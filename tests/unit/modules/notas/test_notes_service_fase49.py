"""
TESTE_1 - notes_service

Objetivo: aumentar a cobertura de src/core/services/notes_service.py na fase 49,
cobrindo listagem, append e tratamento de erros de rede/Postgrest (tabela ausente, auth, etc.).
"""

from __future__ import annotations

import types

import pytest

import src.core.services.notes_service as notes_service


class DummyQuery:
    def __init__(self, table: str):
        self.table = table
        self.actions = []

    def select(self, cols):
        self.actions.append(("select", cols))
        return self

    def eq(self, field, value):
        self.actions.append(("eq", field, value))
        return self

    def order(self, field, desc=False):
        self.actions.append(("order", field, desc))
        return self

    def limit(self, value):
        self.actions.append(("limit", value))
        return self

    def gt(self, field, value):
        self.actions.append(("gt", field, value))
        return self

    def insert(self, payload):
        self.actions.append(("insert", payload))
        return self


def test_is_transient_net_error_true_para_timeout():
    class TimeoutError(Exception):
        def __str__(self):
            return "Timed out while connecting"

    assert notes_service._is_transient_net_error(TimeoutError()) is True

    class ErrnoError(Exception):
        errno = notes_service.errno.EAGAIN

        def __str__(self):
            return "EAGAIN"

    assert notes_service._is_transient_net_error(ErrnoError()) is True


def test_is_transient_net_error_false_para_outros():
    assert notes_service._is_transient_net_error(ValueError("boom")) is False


def test_with_retry_exaure_e_lanca_transient(monkeypatch):
    attempts = {"count": 0}
    monkeypatch.setattr(notes_service.time, "sleep", lambda s: None)
    monkeypatch.setattr(notes_service, "_is_transient_net_error", lambda e: True)

    def always_fail():
        attempts["count"] += 1
        raise RuntimeError("timeout")

    with pytest.raises(notes_service.NotesTransientError):
        notes_service._with_retry(always_fail, retries=2, base_sleep=0)

    assert attempts["count"] == 2


def test_with_retry_aborta_em_erro_nao_transiente(monkeypatch):
    monkeypatch.setattr(notes_service, "_is_transient_net_error", lambda e: False)

    def fail():
        raise RuntimeError("fatal")

    with pytest.raises(RuntimeError):
        notes_service._with_retry(fail, retries=3, base_sleep=0)


def test_check_table_missing_error_lanca(monkeypatch):
    with pytest.raises(notes_service.NotesTableMissingError):
        notes_service._check_table_missing_error(Exception("relation rc_notes does not exist"))

    class CodeError(Exception):
        code = "PGRST205"

        def get(self, key, default=None):
            return getattr(self, key, default)

        def __str__(self):
            return "other"

    with pytest.raises(notes_service.NotesTableMissingError):
        notes_service._check_table_missing_error(CodeError())


def test_check_auth_error_lanca():
    with pytest.raises(notes_service.NotesAuthError):
        notes_service._check_auth_error(Exception("permission denied for table"))

    class AuthCodeError(Exception):
        code = "42501"

        def get(self, key, default=None):
            return getattr(self, key, default)

    with pytest.raises(notes_service.NotesAuthError):
        notes_service._check_auth_error(AuthCodeError())


def test_list_notes_caminho_feliz(monkeypatch):
    monkeypatch.setattr(notes_service, "_with_retry", lambda fn, retries=3, base_sleep=0.25: fn())
    queries = []

    class StubSupabase:
        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(notes_service, "get_supabase", lambda: StubSupabase())

    def fake_exec(query):
        queries.append(query)
        return types.SimpleNamespace(
            data=[{"id": 1, "author_email": "user@example.com", "body": "hi", "created_at": "t"}]
        )

    monkeypatch.setattr(notes_service, "exec_postgrest", fake_exec)
    result = notes_service.list_notes("org-1", limit=10)

    assert result[0]["id"] == 1
    assert ("eq", "org_id", "org-1") in queries[0].actions
    assert ("limit", 10) in queries[0].actions


def test_list_notes_transient_error(monkeypatch):
    def raise_transient(fn, retries=3, base_sleep=0.25):
        raise notes_service.NotesTransientError("boom")

    monkeypatch.setattr(notes_service, "_with_retry", raise_transient)

    with pytest.raises(notes_service.NotesTransientError):
        notes_service.list_notes("org-1")


def test_list_notes_tabela_ausente(monkeypatch):
    monkeypatch.setattr(
        notes_service,
        "_with_retry",
        lambda fn, retries=3, base_sleep=0.25: (_ for _ in ()).throw(notes_service.NotesTableMissingError("no table")),
    )  # noqa: E501

    with pytest.raises(notes_service.NotesTableMissingError):
        notes_service.list_notes("org-1")


def test_list_notes_retorna_vazio_em_erro_generico(monkeypatch):
    def raise_generic(fn, retries=3, base_sleep=0.25):
        raise RuntimeError("fatal error not table")

    monkeypatch.setattr(notes_service, "_with_retry", raise_generic)
    monkeypatch.setattr(notes_service, "_check_table_missing_error", lambda e: None)

    result = notes_service.list_notes("org-1")

    assert result == []


def test_add_note_caminho_feliz(monkeypatch):
    monkeypatch.setattr(notes_service, "_with_retry", lambda fn, retries=3, base_sleep=0.25: fn())

    class StubSupabase:
        def table(self, name):
            return DummyQuery(name)

    monkeypatch.setattr(notes_service, "get_supabase", lambda: StubSupabase())
    monkeypatch.setattr(
        notes_service, "exec_postgrest", lambda query: types.SimpleNamespace(data=[{"id": 5, "body": "ok"}])
    )

    result = notes_service.add_note("org-1", "user@example.com", "texto")

    assert result["id"] == 5


def test_add_note_body_vazio(monkeypatch):
    with pytest.raises(ValueError):
        notes_service.add_note("org-1", "a@b.com", "")


def test_add_note_auth_error(monkeypatch):
    monkeypatch.setattr(
        notes_service,
        "_with_retry",
        lambda fn, retries=3, base_sleep=0.25: (_ for _ in ()).throw(Exception("42501 RLS")),
    )
    with pytest.raises(notes_service.NotesAuthError):
        notes_service.add_note("org-1", "user@example.com", "txt")


def test_add_note_tabela_ausente(monkeypatch):
    class MissingTableError(Exception):
        code = "PGRST205"

    monkeypatch.setattr(
        notes_service,
        "_with_retry",
        lambda fn, retries=3, base_sleep=0.25: (_ for _ in ()).throw(MissingTableError("no table")),
    )
    with pytest.raises(notes_service.NotesTableMissingError):
        notes_service.add_note("org-1", "user@example.com", "txt")


def test_add_note_transient(monkeypatch):
    monkeypatch.setattr(
        notes_service,
        "_with_retry",
        lambda fn, retries=3, base_sleep=0.25: (_ for _ in ()).throw(notes_service.NotesTransientError("temp")),
    )
    with pytest.raises(notes_service.NotesTransientError):
        notes_service.add_note("org-1", "user@example.com", "txt")


def test_add_note_limita_tamanho(monkeypatch):
    monkeypatch.setattr(notes_service, "_with_retry", lambda fn, retries=3, base_sleep=0.25: fn())
    monkeypatch.setattr(
        notes_service, "get_supabase", lambda: types.SimpleNamespace(table=lambda name: DummyQuery(name))
    )
    payloads = {}

    def fake_exec(query):
        payload = next(action[1] for action in query.actions if action[0] == "insert")
        payloads["body_len"] = len(payload["body"])
        return types.SimpleNamespace(data=[payload])

    monkeypatch.setattr(notes_service, "exec_postgrest", fake_exec)
    long_body = "x" * 2000
    notes_service.add_note("org-1", "user@example.com", long_body)

    assert payloads["body_len"] == 1000


def test_list_notes_since_sem_since():
    assert notes_service.list_notes_since("org", None) == []


def test_list_notes_since_caminho_feliz(monkeypatch):
    monkeypatch.setattr(notes_service, "_with_retry", lambda fn, retries=2, base_sleep=0.1: fn())
    monkeypatch.setattr(
        notes_service, "get_supabase", lambda: types.SimpleNamespace(table=lambda name: DummyQuery(name))
    )
    monkeypatch.setattr(
        notes_service,
        "exec_postgrest",
        lambda query: types.SimpleNamespace(data=[{"id": 2, "author_email": "u", "created_at": "t"}]),
    )

    result = notes_service.list_notes_since("org-1", "ts")

    assert result[0]["id"] == 2


def test_list_notes_since_com_erro_retornar_vazio(monkeypatch):
    monkeypatch.setattr(
        notes_service, "_with_retry", lambda fn, retries=2, base_sleep=0.1: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    result = notes_service.list_notes_since("org-1", "ts")
    assert result == []


# ==================== Novos Testes - MICROFASE NOTES_SERVICE ====================


def test_is_transient_net_error_detecta_temporarily_unavailable():
    """Testa detecção de 'temporarily unavailable' string."""
    err = Exception("Service temporarily unavailable")
    assert notes_service._is_transient_net_error(err) is True


def test_is_transient_net_error_detecta_temporary_failure():
    """Testa detecção de 'temporary failure' string."""
    err = Exception("temporary failure in name resolution")
    assert notes_service._is_transient_net_error(err) is True


def test_handle_table_missing_error_logged_com_dict():
    """Testa _handle_table_missing_error_logged com exceção dict-like (código PGRST205)."""

    class DictCodeError(Exception):
        def get(self, key, default=None):
            if key == "code":
                return "PGRST205"
            return default

        def __str__(self):
            return "PGRST205: relation rc_notes does not exist"

    exc = DictCodeError()

    # Deve lançar NotesTableMissingError
    with pytest.raises(notes_service.NotesTableMissingError):
        notes_service._handle_table_missing_error_logged(exc)


def test_handle_auth_error_logged_com_42501_dict(monkeypatch):
    """Testa _handle_auth_error_logged com exceção dict-like (código 42501 RLS)."""

    class DictAuthError(Exception):
        def get(self, key, default=None):
            if key == "code":
                return "42501"
            return default

        def __str__(self):
            return "42501: permission denied for table"

    exc = DictAuthError()

    # Deve lançar NotesAuthError
    with pytest.raises(notes_service.NotesAuthError):
        notes_service._handle_auth_error_logged(exc, "org-123", "user")


def test_normalize_author_email_for_org_com_prefixo_sem_arroba(monkeypatch):
    """Testa _normalize_author_email_for_org com prefixo sem @, buscando no mapa de aliases."""

    # Mock do get_email_prefix_map retornando mapa de aliases
    def fake_get_map(org_id):
        return {"user1": "user1@example.com", "admin": "admin@example.com"}

    monkeypatch.setattr("src.core.services.profiles_service.get_email_prefix_map", fake_get_map)
    monkeypatch.setattr("src.core.services.profiles_service.EMAIL_PREFIX_ALIASES", {})

    # Testa conversão de prefixo para email completo
    result = notes_service._normalize_author_email_for_org("user1", "org-123")
    assert result == "user1@example.com"


def test_normalize_author_email_for_org_com_prefixo_nao_mapeado(monkeypatch):
    """Testa _normalize_author_email_for_org com prefixo sem @ que não está no mapa."""

    def fake_get_map(org_id):
        return {"user1": "user1@example.com"}

    monkeypatch.setattr("src.core.services.profiles_service.get_email_prefix_map", fake_get_map)
    monkeypatch.setattr("src.core.services.profiles_service.EMAIL_PREFIX_ALIASES", {})

    # Prefixo não mapeado deve retornar o próprio prefixo
    result = notes_service._normalize_author_email_for_org("unknownuser", "org-123")
    assert result == "unknownuser"


def test_normalize_author_email_for_org_com_alias_em_prefix_aliases(monkeypatch):
    """Testa _normalize_author_email_for_org com EMAIL_PREFIX_ALIASES mapeando o prefixo."""

    def fake_get_map(org_id):
        return {"aliased": "aliased@example.com"}

    monkeypatch.setattr("src.core.services.profiles_service.get_email_prefix_map", fake_get_map)
    monkeypatch.setattr("src.core.services.profiles_service.EMAIL_PREFIX_ALIASES", {"user": "aliased"})

    # "user" deve ser mapeado para "aliased" via EMAIL_PREFIX_ALIASES
    result = notes_service._normalize_author_email_for_org("user", "org-123")
    assert result == "aliased@example.com"


def test_normalize_author_email_for_org_falha_get_map_retorna_prefixo(monkeypatch):
    """Testa _normalize_author_email_for_org quando get_email_prefix_map lança exceção."""

    def fake_get_map(org_id):
        raise RuntimeError("Supabase connection error")

    monkeypatch.setattr("src.core.services.profiles_service.get_email_prefix_map", fake_get_map)
    monkeypatch.setattr("src.core.services.profiles_service.EMAIL_PREFIX_ALIASES", {})

    # Deve retornar o prefixo original sem quebrar
    result = notes_service._normalize_author_email_for_org("user1", "org-123")
    assert result == "user1"


def test_add_note_reraise_notes_table_missing_error(monkeypatch):
    """Testa que add_note re-lança NotesTableMissingError sem wrapping."""

    def fake_retry(fn, retries=3, base_sleep=0.25):
        raise notes_service.NotesTableMissingError("Tabela ausente")

    monkeypatch.setattr(notes_service, "_with_retry", fake_retry)

    # Deve re-lançar NotesTableMissingError diretamente
    with pytest.raises(notes_service.NotesTableMissingError, match="Tabela ausente"):
        notes_service.add_note("org-123", "user@example.com", "Test note")


def test_add_note_reraise_notes_auth_error(monkeypatch):
    """Testa que add_note re-lança NotesAuthError sem wrapping."""

    def fake_retry(fn, retries=3, base_sleep=0.25):
        raise notes_service.NotesAuthError("Permissão negada")

    monkeypatch.setattr(notes_service, "_with_retry", fake_retry)

    # Deve re-lançar NotesAuthError diretamente
    with pytest.raises(notes_service.NotesAuthError, match="Permissão negada"):
        notes_service.add_note("org-123", "user@example.com", "Test note")


def test_add_note_outro_erro_chama_handlers(monkeypatch):
    """Testa que add_note chama _handle_table_missing_error_logged e _handle_auth_error_logged em erros genéricos."""

    handler_calls = {"table": 0, "auth": 0}

    def fake_retry(fn, retries=3, base_sleep=0.25):
        raise RuntimeError("Erro genérico")

    def fake_table_handler(exc):
        handler_calls["table"] += 1

    def fake_auth_handler(exc, org_id, email_prefix):
        handler_calls["auth"] += 1

    monkeypatch.setattr(notes_service, "_with_retry", fake_retry)
    monkeypatch.setattr(notes_service, "_handle_table_missing_error_logged", fake_table_handler)
    monkeypatch.setattr(notes_service, "_handle_auth_error_logged", fake_auth_handler)

    # Deve lançar RuntimeError após chamar os handlers
    with pytest.raises(RuntimeError, match="Erro genérico"):
        notes_service.add_note("org-123", "user@example.com", "Test note")

    assert handler_calls["table"] == 1
    assert handler_calls["auth"] == 1


def test_check_table_missing_error_com_dict_like_exception():
    """Testa _check_table_missing_error com exceção dict-like (hasattr + .get())."""

    class DictLikeError(Exception):
        """Exceção que se comporta como dict com método get()."""

        def get(self, key, default=None):
            if key == "code":
                return "PGRST205"
            return default

        def __str__(self):
            return "Table missing"

    err = DictLikeError()

    # Deve lançar NotesTableMissingError
    with pytest.raises(notes_service.NotesTableMissingError, match="Tabela 'rc_notes' ausente"):
        notes_service._check_table_missing_error(err)


def test_check_auth_error_com_dict_like_exception():
    """Testa _check_auth_error com exceção dict-like (hasattr + .get())."""

    class DictLikeError(Exception):
        """Exceção que se comporta como dict com método get()."""

        def get(self, key, default=None):
            if key == "code":
                return "42501"
            return default

        def __str__(self):
            return "Permission denied"

    err = DictLikeError()

    # Deve lançar NotesAuthError (regex flexível para encoding)
    with pytest.raises(notes_service.NotesAuthError, match=r"Sem.*RLS"):
        notes_service._check_auth_error(err)


def test_normalize_author_emails_com_excecao_get_email_map(monkeypatch):
    """Testa _normalize_author_emails quando get_email_prefix_map lança exceção."""

    def fake_get_map(org_id):
        raise RuntimeError("Database connection failed")

    monkeypatch.setattr("src.core.services.profiles_service.get_email_prefix_map", fake_get_map)
    monkeypatch.setattr("src.core.services.profiles_service.EMAIL_PREFIX_ALIASES", {})

    rows = [
        {"author_email": "user1", "body": "Test note 1"},
        {"author_email": "user2", "body": "Test note 2"},
    ]

    # Deve retornar os prefixos originais sem quebrar
    result = notes_service._normalize_author_emails(rows, "org-123")

    assert result[0]["author_email"] == "user1"
    assert result[1]["author_email"] == "user2"


def test_is_transient_net_error_wouldblock_string():
    """Testa detecção de 'wouldblock' no erro como string."""
    err = Exception("Operation wouldblock")
    assert notes_service._is_transient_net_error(err) is True


def test_is_transient_net_error_10035_string():
    """Testa detecção de '10035' no erro como string."""
    err = Exception("WinError 10035 occurred")
    assert notes_service._is_transient_net_error(err) is True


def test_is_transient_net_error_errno_eagain():
    """Testa detecção de EAGAIN via errno."""
    err = OSError()
    err.errno = notes_service.errno.EAGAIN  # type: ignore
    assert notes_service._is_transient_net_error(err) is True


def test_handle_auth_error_logged_com_dict_like_42501(monkeypatch):
    """Testa _handle_auth_error_logged com exceção dict-like código 42501."""

    class DictAuthError(Exception):
        """Exceção dict-like com código 42501 RLS."""

        def get(self, key, default=None):
            if key == "code":
                return "42501"
            return default

        def __str__(self):
            return "Generic error message"

    err = DictAuthError()

    # Deve lançar NotesAuthError ao chamar _handle_auth_error_logged
    with pytest.raises(notes_service.NotesAuthError, match=r"Sem.*RLS"):
        notes_service._handle_auth_error_logged(err, "org-123", "user")
