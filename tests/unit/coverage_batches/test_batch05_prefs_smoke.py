# -*- coding: utf-8 -*-
"""
Testes SMOKE para src/utils/prefs.py

Coverage batch 05: preferências de usuário (columns, login, auth session, browser state).
Todos os testes são headless (sem GUI), determinísticos, e usam tmp_path para isolamento.

Convenção: todos os nomes de teste contêm "smoke" para serem incluídos no pytest --smoke.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.utils import prefs as prefs_module


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redireciona _get_base_dir para tmp_path (isolamento total)."""
    base = tmp_path / "prefs_test"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(prefs_module, "_get_base_dir", lambda: str(base))
    return base


class DummyLock:
    """Context manager dummy para simular FileLock."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "DummyLock":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


# =============================================================================
# COLUMNS VISIBILITY
# =============================================================================


class TestColumnsVisibilitySmoke:
    """Testes smoke para save/load_columns_visibility."""

    def test_prefs_smoke_columns_roundtrip(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Roundtrip: salva e carrega columns_visibility corretamente."""
        user_key = "user@example.com"
        mapping = {"col_a": True, "col_b": False, "col_c": True}

        # Sem filelock
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        prefs_module.save_columns_visibility(user_key, mapping)
        loaded = prefs_module.load_columns_visibility(user_key)

        assert loaded == mapping

    def test_prefs_smoke_columns_invalid_json_returns_empty(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arquivo JSON quebrado retorna {} sem exceção."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        # Escrever JSON inválido
        prefs_path = tmp_base / prefs_module.PREFS_FILENAME
        prefs_path.write_text("{broken json", encoding="utf-8")

        result = prefs_module.load_columns_visibility("any_user")
        assert result == {}

    def test_prefs_smoke_columns_with_filelock_branch(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Branch com HAS_FILELOCK=True usando DummyLock."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", True)
        monkeypatch.setattr(prefs_module, "FileLock", DummyLock)

        user_key = "locked_user@test.com"
        mapping = {"locked_col": True}

        prefs_module.save_columns_visibility(user_key, mapping)
        loaded = prefs_module.load_columns_visibility(user_key)

        assert loaded == mapping

    def test_prefs_smoke_columns_multiple_users(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Preserva preferências de múltiplos usuários."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        prefs_module.save_columns_visibility("user1", {"a": True})
        prefs_module.save_columns_visibility("user2", {"b": False})

        assert prefs_module.load_columns_visibility("user1") == {"a": True}
        assert prefs_module.load_columns_visibility("user2") == {"b": False}

    def test_prefs_smoke_columns_nonexistent_returns_empty(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Usuário inexistente retorna {}."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)
        result = prefs_module.load_columns_visibility("nonexistent@test.com")
        assert result == {}


# =============================================================================
# LOGIN PREFS
# =============================================================================


class TestLoginPrefsSmoke:
    """Testes smoke para save/load_login_prefs."""

    def test_prefs_smoke_login_save_remember_true(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """save_login_prefs(remember=True) persiste e load normaliza email."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        email = "  Test@Example.COM  "
        prefs_module.save_login_prefs(email, remember_email=True)

        loaded = prefs_module.load_login_prefs()
        assert loaded["email"] == "Test@Example.COM"  # stripped
        assert loaded["remember_email"] is True

    def test_prefs_smoke_login_save_remember_false_removes_file(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_login_prefs(remember=False) remove arquivo e load retorna {}."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        # Primeiro salva
        prefs_module.save_login_prefs("user@test.com", remember_email=True)
        login_path = tmp_base / prefs_module.LOGIN_PREFS_FILENAME
        assert login_path.exists()

        # Depois remove
        prefs_module.save_login_prefs("user@test.com", remember_email=False)
        assert not login_path.exists()

        loaded = prefs_module.load_login_prefs()
        assert loaded == {}

    def test_prefs_smoke_login_invalid_structure_returns_empty(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arquivo com estrutura inválida (não dict) retorna {}."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        login_path = tmp_base / prefs_module.LOGIN_PREFS_FILENAME
        login_path.write_text('["not", "a", "dict"]', encoding="utf-8")

        result = prefs_module.load_login_prefs()
        assert result == {}

    def test_prefs_smoke_login_with_filelock(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Branch com HAS_FILELOCK=True para login prefs."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", True)
        monkeypatch.setattr(prefs_module, "FileLock", DummyLock)

        prefs_module.save_login_prefs("lock@test.com", remember_email=True)
        loaded = prefs_module.load_login_prefs()

        assert loaded["email"] == "lock@test.com"


# =============================================================================
# AUTH SESSION
# =============================================================================


class TestAuthSessionSmoke:
    """Testes smoke para save/load/clear_auth_session."""

    def test_prefs_smoke_auth_session_keyring_branch_valid(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Branch keyring: mocka funções e valida load de sessão válida."""
        valid_session = {
            "access_token": "abc123",
            "refresh_token": "xyz789",
            "created_at": "2025-12-30T10:00:00Z",
            "keep_logged": True,
        }
        session_json = json.dumps(valid_session)

        # Mock keyring helpers
        monkeypatch.setattr(prefs_module, "_keyring_get_session_json", lambda: session_json)
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)

        result = prefs_module.load_auth_session()

        assert result["access_token"] == "abc123"
        assert result["refresh_token"] == "xyz789"
        assert result["keep_logged"] is True

    def test_prefs_smoke_auth_session_keyring_invalid_json_clears(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keyring com JSON inválido retorna {} e chama _keyring_clear_session."""
        clear_called = []

        monkeypatch.setattr(prefs_module, "_keyring_get_session_json", lambda: "{broken}")
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)
        monkeypatch.setattr(prefs_module, "_keyring_clear_session", lambda: clear_called.append(True))

        result = prefs_module.load_auth_session()

        assert result == {}
        assert len(clear_called) == 1

    def test_prefs_smoke_auth_session_keyring_incomplete_clears(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keyring com sessão incompleta (sem tokens) retorna {} e limpa."""
        incomplete = {"access_token": "abc", "refresh_token": "", "created_at": ""}
        clear_called = []

        monkeypatch.setattr(prefs_module, "_keyring_get_session_json", lambda: json.dumps(incomplete))
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)
        monkeypatch.setattr(prefs_module, "_keyring_clear_session", lambda: clear_called.append(True))

        result = prefs_module.load_auth_session()

        assert result == {}
        assert len(clear_called) == 1

    def test_prefs_smoke_auth_session_keyring_not_dict_clears(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keyring com JSON que não é dict retorna {} e limpa."""
        clear_called = []

        monkeypatch.setattr(prefs_module, "_keyring_get_session_json", lambda: '["list"]')
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)
        monkeypatch.setattr(prefs_module, "_keyring_clear_session", lambda: clear_called.append(True))

        result = prefs_module.load_auth_session()

        assert result == {}
        assert len(clear_called) == 1

    def test_prefs_smoke_auth_session_file_fallback(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fallback arquivo: keyring indisponível, lê do arquivo."""
        monkeypatch.setattr(prefs_module, "_keyring_get_session_json", lambda: None)
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: False)
        monkeypatch.setattr(prefs_module, "_keyring_set_session_json", lambda x: False)
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        # Escrever arquivo de sessão
        session_data = {
            "access_token": "file_token",
            "refresh_token": "file_refresh",
            "created_at": "2025-01-01T00:00:00Z",
            "keep_logged": True,
        }
        auth_path = tmp_base / prefs_module.AUTH_SESSION_FILENAME
        auth_path.write_text(json.dumps(session_data), encoding="utf-8")

        result = prefs_module.load_auth_session()

        assert result["access_token"] == "file_token"
        assert result["refresh_token"] == "file_refresh"

    def test_prefs_smoke_auth_session_save_keyring_success(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_auth_session usa keyring quando disponível."""
        saved_to_keyring = []

        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)
        monkeypatch.setattr(
            prefs_module,
            "_keyring_set_session_json",
            lambda x: (saved_to_keyring.append(x), True)[1],
        )
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        prefs_module.save_auth_session("tok", "ref", keep_logged=True)

        assert len(saved_to_keyring) == 1
        parsed = json.loads(saved_to_keyring[0])
        assert parsed["access_token"] == "tok"
        assert parsed["refresh_token"] == "ref"

    def test_prefs_smoke_auth_session_save_file_fallback(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """save_auth_session usa arquivo quando keyring falha."""
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: False)
        monkeypatch.setattr(prefs_module, "_keyring_set_session_json", lambda x: False)
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        prefs_module.save_auth_session("file_tok", "file_ref", keep_logged=True)

        auth_path = tmp_base / prefs_module.AUTH_SESSION_FILENAME
        assert auth_path.exists()

        data = json.loads(auth_path.read_text(encoding="utf-8"))
        assert data["access_token"] == "file_tok"

    def test_prefs_smoke_auth_session_save_not_keep_logged_clears(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_auth_session(keep_logged=False) limpa tudo."""
        clear_called = []

        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)
        monkeypatch.setattr(prefs_module, "_keyring_set_session_json", lambda x: True)
        monkeypatch.setattr(prefs_module, "_keyring_clear_session", lambda: clear_called.append(True))
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        # Criar arquivo primeiro
        auth_path = tmp_base / prefs_module.AUTH_SESSION_FILENAME
        auth_path.write_text('{"test": true}', encoding="utf-8")

        prefs_module.save_auth_session("x", "y", keep_logged=False)

        assert len(clear_called) == 1
        assert not auth_path.exists()

    def test_prefs_smoke_auth_session_clear(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """clear_auth_session remove keyring e arquivo."""
        clear_called = []

        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: True)
        monkeypatch.setattr(prefs_module, "_keyring_clear_session", lambda: clear_called.append(True))

        # Criar arquivo
        auth_path = tmp_base / prefs_module.AUTH_SESSION_FILENAME
        auth_path.write_text('{"test": true}', encoding="utf-8")

        prefs_module.clear_auth_session()

        assert len(clear_called) == 1
        assert not auth_path.exists()

    def test_prefs_smoke_auth_session_save_with_filelock(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Branch HAS_FILELOCK=True para save_auth_session (fallback arquivo)."""
        monkeypatch.setattr(prefs_module, "_keyring_is_available", lambda: False)
        monkeypatch.setattr(prefs_module, "_keyring_set_session_json", lambda x: False)
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", True)
        monkeypatch.setattr(prefs_module, "FileLock", DummyLock)

        prefs_module.save_auth_session("locked_tok", "locked_ref", keep_logged=True)

        auth_path = tmp_base / prefs_module.AUTH_SESSION_FILENAME
        assert auth_path.exists()


# =============================================================================
# BROWSER STATE HELPERS
# =============================================================================


class TestBrowserStateSmoke:
    """Testes smoke para browser state helpers."""

    def test_prefs_smoke_browser_save_load_last_prefix(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """save_last_prefix/load_last_prefix roundtrip."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        key = "client_123"
        prefix = "docs/2025/"

        prefs_module.save_last_prefix(key, prefix)
        loaded = prefs_module.load_last_prefix(key)

        assert loaded == prefix

    def test_prefs_smoke_browser_load_prefix_nonexistent(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_last_prefix retorna "" para chave inexistente."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        result = prefs_module.load_last_prefix("nonexistent_key")
        assert result == ""

    def test_prefs_smoke_browser_prefix_preserves_other_keys(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_last_prefix preserva outras chaves."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        prefs_module.save_last_prefix("key1", "prefix1")
        prefs_module.save_last_prefix("key2", "prefix2")

        assert prefs_module.load_last_prefix("key1") == "prefix1"
        assert prefs_module.load_last_prefix("key2") == "prefix2"

    def test_prefs_smoke_browser_save_load_status_map(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """save_browser_status_map/load_browser_status_map roundtrip."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        key = "user@example.com"
        mapping = {"file1.pdf": "uploaded", "file2.pdf": "pending"}

        prefs_module.save_browser_status_map(key, mapping)
        loaded = prefs_module.load_browser_status_map(key)

        assert loaded == mapping

    def test_prefs_smoke_browser_load_status_map_nonexistent(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_browser_status_map retorna {} para chave inexistente."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        result = prefs_module.load_browser_status_map("nonexistent")
        assert result == {}

    def test_prefs_smoke_browser_status_map_preserves_other_keys(
        self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_browser_status_map preserva outras chaves."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        prefs_module.save_browser_status_map("user1", {"a": "1"})
        prefs_module.save_browser_status_map("user2", {"b": "2"})

        assert prefs_module.load_browser_status_map("user1") == {"a": "1"}
        assert prefs_module.load_browser_status_map("user2") == {"b": "2"}

    def test_prefs_smoke_browser_status_map_invalid_file(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_browser_status_map com arquivo inválido retorna {}."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        status_path = tmp_base / prefs_module.BROWSER_STATUS_FILENAME
        status_path.write_text("{broken", encoding="utf-8")

        result = prefs_module.load_browser_status_map("any_key")
        assert result == {}

    def test_prefs_smoke_browser_prefix_invalid_file(self, tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_last_prefix com arquivo inválido retorna ""."""
        monkeypatch.setattr(prefs_module, "HAS_FILELOCK", False)

        state_path = tmp_base / prefs_module.BROWSER_STATE_FILENAME
        state_path.write_text("{broken", encoding="utf-8")

        result = prefs_module.load_last_prefix("any_key")
        assert result == ""
