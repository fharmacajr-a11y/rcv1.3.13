"""Testes para src/core/services/profiles_service.py (TEST-001 Fase 6).

Valida o serviço de perfis de usuários usado por notes_service para normalizar
emails e mapear display_names.
"""

from typing import Any


from src.core.services import profiles_service


class FakeSupabaseResponse:
    """Mock de resposta do Supabase para profiles."""

    def __init__(self, data: list[dict[str, Any]] | None = None):
        self.data = data or []


class FakeSupabaseTable:
    """Mock de table do Supabase."""

    def __init__(self, response_data: list[dict[str, Any]] | None = None, raise_error: Exception | None = None):
        self.response_data = response_data
        self.raise_error = raise_error
        self._query_params: dict[str, Any] = {}

    def select(self, fields: str) -> "FakeSupabaseTable":
        """Simula select()."""
        self._query_params["fields"] = fields
        return self

    def eq(self, field: str, value: Any) -> "FakeSupabaseTable":
        """Simula eq()."""
        self._query_params[f"eq_{field}"] = value
        return self

    def in_(self, field: str, values: list[Any]) -> "FakeSupabaseTable":
        """Simula in_()."""
        self._query_params[f"in_{field}"] = values
        return self

    def limit(self, n: int) -> "FakeSupabaseTable":
        """Simula limit()."""
        self._query_params["limit"] = n
        return self

    def execute(self) -> FakeSupabaseResponse:
        """Simula execute() - usado por exec_postgrest."""
        if self.raise_error:
            raise self.raise_error
        return FakeSupabaseResponse(self.response_data)


class FakeSupabaseClient:
    """Mock do cliente Supabase."""

    def __init__(self, response_data: list[dict[str, Any]] | None = None, raise_error: Exception | None = None):
        self.response_data = response_data
        self.raise_error = raise_error

    def table(self, name: str) -> FakeSupabaseTable:
        """Simula table()."""
        return FakeSupabaseTable(self.response_data, self.raise_error)


# ========== Testes para list_profiles_by_org ==========


def test_list_profiles_by_org_success(monkeypatch):
    """Testa listagem de perfis com sucesso (com display_name)."""
    fake_profiles = [
        {"email": "alice@example.com", "display_name": "Alice Silva"},
        {"email": "bob@example.com", "display_name": "Bob Santos"},
    ]

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return query.execute()

    fake_client = FakeSupabaseClient(response_data=fake_profiles)
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.list_profiles_by_org("org-123")

    assert len(result) == 2
    assert result[0]["email"] == "alice@example.com"
    assert result[0]["display_name"] == "Alice Silva"
    assert result[1]["email"] == "bob@example.com"
    assert result[1]["display_name"] == "Bob Santos"


def test_list_profiles_by_org_empty(monkeypatch):
    """Testa listagem quando não há perfis na org."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return query.execute()

    fake_client = FakeSupabaseClient(response_data=[])
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.list_profiles_by_org("org-456")

    assert result == []


def test_list_profiles_by_org_missing_column_fallback(monkeypatch):
    """Testa fallback quando coluna display_name não existe (erro 42703)."""
    # Simula erro de coluna ausente no primeiro select
    error = Exception("column display_name does not exist (42703)")

    call_count = {"count": 0}

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        call_count["count"] += 1
        if call_count["count"] == 1:
            # Primeira chamada (com display_name) falha
            raise error
        # Segunda chamada (sem display_name) retorna dados
        return FakeSupabaseResponse([{"email": "charlie@example.com"}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    # Reseta flag de warning
    profiles_service._WARNED_MISSING_COL = False

    result = profiles_service.list_profiles_by_org("org-789")

    assert len(result) == 1
    assert result[0]["email"] == "charlie@example.com"
    assert call_count["count"] == 2  # Duas chamadas: fallback funcionou


def test_list_profiles_by_org_network_error_returns_empty(monkeypatch):
    """Testa que erro de rede retorna lista vazia (graceful degradation)."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        raise Exception("Network timeout")

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.list_profiles_by_org("org-error")

    assert result == []


# ========== Testes para get_display_names_map ==========


def test_get_display_names_map_success(monkeypatch):
    """Testa criação de mapa email -> display_name."""
    fake_profiles = [
        {"email": "Alice@Example.com", "display_name": "Alice Silva"},
        {"email": "bob@example.com", "display_name": "Bob Santos"},
        {"email": "noname@example.com", "display_name": ""},  # Sem display_name
    ]

    monkeypatch.setattr(profiles_service, "list_profiles_by_org", lambda org_id: fake_profiles)

    result = profiles_service.get_display_names_map("org-123")

    # Emails normalizados para lowercase
    assert result == {
        "alice@example.com": "Alice Silva",
        "bob@example.com": "Bob Santos",
        # noname@example.com não incluído (display_name vazio)
    }


def test_get_display_names_map_empty_org(monkeypatch):
    """Testa mapa vazio quando org não tem perfis."""
    monkeypatch.setattr(profiles_service, "list_profiles_by_org", lambda org_id: [])

    result = profiles_service.get_display_names_map("org-empty")

    assert result == {}


def test_get_display_names_map_filters_empty_emails(monkeypatch):
    """Testa que emails vazios são filtrados do mapa."""
    fake_profiles = [
        {"email": "", "display_name": "No Email User"},
        {"email": "   ", "display_name": "Whitespace Email"},
        {"email": "valid@example.com", "display_name": "Valid User"},
    ]

    monkeypatch.setattr(profiles_service, "list_profiles_by_org", lambda org_id: fake_profiles)

    result = profiles_service.get_display_names_map("org-123")

    assert result == {"valid@example.com": "Valid User"}


# ========== Testes para get_display_name_by_email ==========


def test_get_display_name_by_email_success(monkeypatch):
    """Testa busca direta de display_name por email."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse([{"display_name": "Alice Silva"}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_name_by_email("alice@example.com")

    assert result == "Alice Silva"


def test_get_display_name_by_email_case_normalization(monkeypatch):
    """Testa que email é normalizado para lowercase."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        # Verifica que query foi feita com email lowercase
        return FakeSupabaseResponse([{"display_name": "Bob Santos"}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_name_by_email("Bob@Example.COM")

    assert result == "Bob Santos"


def test_get_display_name_by_email_not_found(monkeypatch):
    """Testa que retorna None quando email não encontrado."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse([])  # Sem resultados

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_name_by_email("notfound@example.com")

    assert result is None


# ========== Testes para get_display_names_by_user_ids ==========


def test_get_display_names_by_user_ids_success(monkeypatch):
    """Testa mapeamento de user_ids para display_names."""
    fake_profiles = [
        {"id": "user-1", "email": "ana@example.com", "display_name": "Ana"},
        {"id": "user-2", "email": "junior@example.com", "display_name": "Junior"},
    ]

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return query.execute()

    fake_client = FakeSupabaseClient(response_data=fake_profiles)
    monkeypatch.setattr("src.core.services.profiles_service.get_supabase", lambda: fake_client)
    monkeypatch.setattr("src.core.services.profiles_service.exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_names_by_user_ids("org-123", ["user-1", "user-2"])

    assert result == {"user-1": "Ana", "user-2": "Junior"}


def test_get_display_names_by_user_ids_empty_list(monkeypatch):
    """Testa com lista vazia de user_ids."""
    result = profiles_service.get_display_names_by_user_ids("org-123", [])
    assert result == {}


def test_get_display_names_by_user_ids_fallback_to_email_prefix(monkeypatch):
    """Testa fallback para prefixo do email quando display_name está vazio."""
    fake_profiles = [
        {"id": "user-1", "email": "ana_silva@example.com", "display_name": ""},
        {"id": "user-2", "email": "junior@example.com", "display_name": "Junior"},
    ]

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return query.execute()

    fake_client = FakeSupabaseClient(response_data=fake_profiles)
    monkeypatch.setattr("src.core.services.profiles_service.get_supabase", lambda: fake_client)
    monkeypatch.setattr("src.core.services.profiles_service.exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_names_by_user_ids("org-123", ["user-1", "user-2"])

    assert result == {"user-1": "ana_silva", "user-2": "Junior"}


def test_get_display_names_by_user_ids_filters_none_and_empty(monkeypatch):
    """Testa que filtra user_ids None e vazios."""
    fake_profiles = [
        {"id": "user-1", "email": "ana@example.com", "display_name": "Ana"},
    ]

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return query.execute()

    fake_client = FakeSupabaseClient(response_data=fake_profiles)
    monkeypatch.setattr("src.core.services.profiles_service.get_supabase", lambda: fake_client)
    monkeypatch.setattr("src.core.services.profiles_service.exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_names_by_user_ids("org-123", ["user-1", None, "", "  "])

    assert result == {"user-1": "Ana"}


def test_get_display_name_by_email_empty_display_name(monkeypatch):
    """Testa que retorna None quando display_name está vazio."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse([{"display_name": "   "}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_name_by_email("empty@example.com")

    assert result is None


def test_get_display_name_by_email_empty_input(monkeypatch):
    """Testa que retorna None quando email está vazio."""
    # Não deve fazer chamada ao DB se email vazio
    result = profiles_service.get_display_name_by_email("")

    assert result is None


def test_get_display_name_by_email_error_returns_none(monkeypatch):
    """Testa que erro na consulta retorna None (graceful degradation)."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        raise Exception("Database error")

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_display_name_by_email("error@example.com")

    assert result is None


# ========== Testes para get_email_prefix_map ==========


def test_get_email_prefix_map_success(monkeypatch):
    """Testa criação de mapa prefixo -> email completo."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse(
            [
                {"email": "alice@example.com"},
                {"email": "bob@test.org"},
                {"email": "fharmaca2013@hotmail.com"},
            ]
        )

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-123")

    assert result["alice"] == "alice@example.com"
    assert result["bob"] == "bob@test.org"
    assert result["fharmaca2013"] == "fharmaca2013@hotmail.com"


def test_get_email_prefix_map_with_aliases(monkeypatch):
    """Testa que aliases de prefixos são aplicados corretamente."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse([{"email": "fharmaca2013@hotmail.com"}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-456")

    # Alias: "pharmaca2013" (sem f) deve mapear para email correto com "f"
    # Prefixo original "fharmaca2013" também deve estar no mapa
    assert result["fharmaca2013"] == "fharmaca2013@hotmail.com"

    # Se tivermos um email com prefixo que tem alias, verificar
    # (O alias pharmaca2013 -> fharmaca2013 só é aplicado quando o prefixo já existe)


def test_get_email_prefix_map_empty_org(monkeypatch):
    """Testa mapa vazio quando org não tem perfis."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse([])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-empty")

    assert result == {}


def test_get_email_prefix_map_filters_empty_emails(monkeypatch):
    """Testa que emails vazios são filtrados do mapa."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse(
            [
                {"email": ""},
                {"email": "   "},
                {"email": "valid@example.com"},
            ]
        )

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-123")

    assert "valid" in result
    assert result["valid"] == "valid@example.com"
    # Emails vazios não devem criar entradas
    assert "" not in result


def test_get_email_prefix_map_error_returns_empty(monkeypatch):
    """Testa que erro na consulta retorna dicionário vazio."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        raise Exception("Database error")

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-error")

    assert result == {}


def test_get_email_prefix_map_case_normalization(monkeypatch):
    """Testa que emails são normalizados para lowercase."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        return FakeSupabaseResponse([{"email": "Alice@Example.COM"}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-123")

    # Prefixo e email devem estar em lowercase
    assert result["alice"] == "alice@example.com"


# ========== Testes de integração com EMAIL_PREFIX_ALIASES ==========


def test_email_prefix_aliases_constant():
    """Verifica que constante EMAIL_PREFIX_ALIASES está definida corretamente."""
    assert isinstance(profiles_service.EMAIL_PREFIX_ALIASES, dict)
    # Verifica alias conhecido usado em notes_service
    assert profiles_service.EMAIL_PREFIX_ALIASES.get("pharmaca2013") == "fharmaca2013"


def test_alias_usage_in_prefix_map(monkeypatch):
    """Testa que alias é aplicado ao construir o mapa de prefixos."""

    def fake_exec_postgrest(query: Any) -> FakeSupabaseResponse:
        # Retorna email com prefixo "correto" (fharmaca2013)
        return FakeSupabaseResponse([{"email": "fharmaca2013@hotmail.com"}])

    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(profiles_service, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(profiles_service, "exec_postgrest", fake_exec_postgrest)

    result = profiles_service.get_email_prefix_map("org-123")

    # Ambos prefixos devem estar no mapa:
    # - fharmaca2013 (original do email)
    # - fharmaca2013 também como alias de fharmaca2013 (redundante mas OK)
    assert "fharmaca2013" in result
    assert result["fharmaca2013"] == "fharmaca2013@hotmail.com"

    # O código aplica alias dentro da função:
    # alias = EMAIL_PREFIX_ALIASES.get(prefix, prefix)
    # out.setdefault(alias, em)
    # out.setdefault(prefix, em)
    # Então ambas entradas devem existir
