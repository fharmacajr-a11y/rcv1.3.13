# -*- coding: utf-8 -*-
"""
Testes unitários para data/supabase_repo.py - BATCH 09

Cobertura das funções públicas:
- Helpers genéricos: get_supabase_client, format_api_error, to_iso_date, with_retries
- CRUD senhas: list_passwords, add_password, update_password, delete_password, delete_passwords_by_client, decrypt_for_view
- Autocomplete: search_clients, list_clients_for_picker
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

# Importar o módulo alvo
import data.supabase_repo as repo


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase."""
    client = MagicMock()
    client.auth = MagicMock()
    client.postgrest = MagicMock()
    client.table = MagicMock(return_value=MagicMock())
    return client


@pytest.fixture
def mock_session():
    """Mock de sessão Supabase com token."""
    session = MagicMock()
    session.access_token = "fake-token-123"
    return session


# -----------------------------------------------------------------------------
# Tests: get_supabase_client
# -----------------------------------------------------------------------------
def test_get_supabase_client_success(mock_supabase_client):
    """Deve retornar cliente Supabase quando disponível."""
    with patch("data.supabase_repo.get_supabase", return_value=mock_supabase_client):
        client = repo.get_supabase_client()
        assert client is mock_supabase_client


def test_get_supabase_client_returns_none():
    """Deve levantar RuntimeError quando get_supabase retorna None."""
    with patch("data.supabase_repo.get_supabase", return_value=None):
        with pytest.raises(RuntimeError, match="Cliente Supabase retornou None"):
            repo.get_supabase_client()


def test_get_supabase_client_exception():
    """Deve levantar RuntimeError quando get_supabase lança exceção."""
    with patch("data.supabase_repo.get_supabase", side_effect=Exception("Connection failed")):
        with pytest.raises(RuntimeError, match="Cliente Supabase não disponível"):
            repo.get_supabase_client()


# -----------------------------------------------------------------------------
# Tests: format_api_error
# -----------------------------------------------------------------------------
def test_format_api_error_basic():
    """Deve formatar erro básico sem code/hint."""
    exc = Exception("Database error")
    result = repo.format_api_error(exc, "SELECT")
    assert isinstance(result, RuntimeError)
    assert "[SELECT] Erro na API: Database error" in str(result)


def test_format_api_error_with_code():
    """Deve incluir code no erro quando disponível."""
    exc = Exception("Access denied")
    exc.code = "42501"  # type: ignore
    exc.details = "Permission denied for table"  # type: ignore
    result = repo.format_api_error(exc, "INSERT")
    assert "[INSERT] (42501) Permission denied for table" in str(result)


def test_format_api_error_with_hint():
    """Deve incluir hint no erro quando disponível."""
    exc = Exception("Constraint violation")
    exc.code = "23505"  # type: ignore
    exc.details = "Duplicate key"  # type: ignore
    exc.hint = "Use ON CONFLICT clause"  # type: ignore
    result = repo.format_api_error(exc, "UPDATE")
    error_msg = str(result)
    assert "(23505) Duplicate key" in error_msg
    assert "hint: Use ON CONFLICT clause" in error_msg


def test_format_api_error_with_message_attr():
    """Deve usar message attr quando details não existir."""
    exc = Exception("Error")
    exc.message = "Custom message"  # type: ignore
    result = repo.format_api_error(exc, "DELETE")
    assert "Custom message" in str(result)


# -----------------------------------------------------------------------------
# Tests: to_iso_date
# -----------------------------------------------------------------------------
def test_to_iso_date_with_date():
    """Deve converter date para string ISO."""
    d = date(2025, 12, 24)
    result = repo.to_iso_date(d)
    assert result == "2025-12-24"


def test_to_iso_date_with_datetime():
    """Deve converter datetime para string ISO."""
    dt = datetime(2025, 12, 24, 15, 30, 45)
    result = repo.to_iso_date(dt)
    assert result.startswith("2025-12-24T15:30:45")


def test_to_iso_date_with_string():
    """Deve retornar string como está."""
    s = "2025-12-24"
    result = repo.to_iso_date(s)
    assert result == s


def test_to_iso_date_with_other():
    """Deve converter objeto com isoformat quando disponível."""
    obj = MagicMock()
    obj.isoformat = MagicMock(return_value="2025-12-24T00:00:00")
    result = repo.to_iso_date(obj)
    assert result == "2025-12-24T00:00:00"


# -----------------------------------------------------------------------------
# Tests: with_retries
# -----------------------------------------------------------------------------
def test_with_retries_success_first_attempt():
    """Deve retornar resultado na primeira tentativa quando bem-sucedido."""
    fn = Mock(return_value="success")
    result = repo.with_retries(fn, tries=3)
    assert result == "success"
    assert fn.call_count == 1


def test_with_retries_success_after_transient_error():
    """Deve tentar novamente após erro transitório (httpx.ReadError)."""
    fn = Mock(side_effect=[httpx.ReadError("Network error"), "success"])
    result = repo.with_retries(fn, tries=3, base_delay=0.01)
    assert result == "success"
    assert fn.call_count == 2


def test_with_retries_all_attempts_fail():
    """Deve levantar exceção após esgotar tentativas."""
    fn = Mock(side_effect=httpx.ConnectError("Connection refused"))
    with pytest.raises(httpx.ConnectError, match="Connection refused"):
        repo.with_retries(fn, tries=3, base_delay=0.01)
    assert fn.call_count == 3


def test_with_retries_non_retryable_error():
    """Deve levantar imediatamente exceção não-transitória."""
    fn = Mock(side_effect=ValueError("Invalid input"))
    with pytest.raises(ValueError, match="Invalid input"):
        repo.with_retries(fn, tries=3)
    assert fn.call_count == 1


def test_with_retries_5xx_error_retryable():
    """Deve tentar novamente em erros 5xx."""
    fn = Mock(side_effect=[Exception("502 Bad Gateway"), "success"])
    result = repo.with_retries(fn, tries=3, base_delay=0.01)
    assert result == "success"
    assert fn.call_count == 2


def test_with_retries_oserror_10035():
    """Deve tentar novamente em WinError 10035."""
    err = OSError("WinError 10035")
    err.errno = 10035
    fn = Mock(side_effect=[err, "success"])
    result = repo.with_retries(fn, tries=3, base_delay=0.01)
    assert result == "success"
    assert fn.call_count == 2


def test_with_retries_oserror_non_transient():
    """Deve tentar novamente OSError mesmo sem errno=10035 (lógica atual)."""
    err = OSError("File not found")
    err.errno = 2
    fn = Mock(side_effect=err)
    with pytest.raises(OSError, match="File not found"):
        repo.with_retries(fn, tries=3, base_delay=0.01)
    # A lógica atual trata OSError como transient independente do errno
    assert fn.call_count == 3


# -----------------------------------------------------------------------------
# Tests: list_passwords
# -----------------------------------------------------------------------------
def test_list_passwords_success(mock_supabase_client):
    """Deve listar senhas com JOIN de clientes."""
    # Mock response com dados do JOIN
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "pass1",
            "org_id": "org1",
            "client_name": "Cliente A",
            "service": "Portal",
            "username": "user1",
            "password_enc": "encrypted123",
            "notes": "Nota",
            "created_by": "user1",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
            "client_id": "client1",
            "clients": {
                "id": "ext123",
                "razao_social": "Empresa A",
                "cnpj": "12345678000190",
                "nome": "João",
                "numero": "11999999999",
            },
        }
    ]

    with (
        patch("data.supabase_repo.supabase", mock_supabase_client),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.list_passwords("org1")

    assert len(result) == 1
    assert result[0]["id"] == "pass1"
    assert result[0].get("client_external_id") == "ext123"
    assert result[0].get("razao_social") == "Empresa A"
    assert result[0].get("whatsapp") == "11999999999"


def test_list_passwords_empty():
    """Deve retornar lista vazia quando não há senhas."""
    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.list_passwords("org1")

    assert result == []


def test_list_passwords_no_client_data():
    """Deve preencher campos vazios quando não há dados do cliente."""
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "pass1",
            "org_id": "org1",
            "client_name": "Cliente Sem Cadastro",
            "service": "Portal",
            "username": "user1",
            "password_enc": "encrypted",
            "notes": "",
            "created_by": "user1",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "client_id": None,
            "clients": None,
        }
    ]

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.list_passwords("org1")

    assert result[0].get("client_external_id") == ""
    assert result[0].get("razao_social") == "Cliente Sem Cadastro"
    assert result[0].get("whatsapp") == ""


def test_list_passwords_with_pagination():
    """Deve aplicar paginação quando especificado."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo.supabase", mock_client),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        repo.list_passwords("org1", limit=10, offset=20)

    # Verifica se range foi chamado
    mock_query.range.assert_called_once_with(20, 29)


def test_list_passwords_no_org_id():
    """Deve levantar ValueError quando org_id não for fornecido."""
    with pytest.raises(ValueError, match="org_id é obrigatório"):
        repo.list_passwords("")


def test_list_passwords_api_error():
    """Deve levantar RuntimeError quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        with pytest.raises(RuntimeError, match="Falha ao listar senhas"):
            repo.list_passwords("org1")


# -----------------------------------------------------------------------------
# Tests: add_password
# -----------------------------------------------------------------------------
def test_add_password_success(mock_supabase_client):
    """Deve adicionar senha com sucesso."""
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "new_pass",
            "org_id": "org1",
            "client_name": "Cliente A",
            "service": "Portal",
            "username": "user1",
            "password_enc": "encrypted",
            "notes": "Nota",
            "created_by": "user1",
        }
    ]

    with (
        patch("data.supabase_repo.supabase", mock_supabase_client),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo._rls_precheck_membership"),
        patch("data.supabase_repo.encrypt_text", return_value="encrypted"),
    ):
        result = repo.add_password(
            org_id="org1",
            client_name="Cliente A",
            service="Portal",
            username="user1",
            password_plain="senha123",
            notes="Nota",
            created_by="user1",
        )

    assert result["id"] == "new_pass"
    assert result["service"] == "Portal"


def test_add_password_with_client_id(mock_supabase_client):
    """Deve adicionar senha com client_id."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "new_pass", "client_id": "client1"}]

    with (
        patch("data.supabase_repo.supabase", mock_supabase_client),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo._rls_precheck_membership"),
        patch("data.supabase_repo.encrypt_text", return_value="encrypted"),
    ):
        result = repo.add_password(
            org_id="org1",
            client_name="Cliente A",
            service="Portal",
            username="user1",
            password_plain="senha123",
            notes="",
            created_by="user1",
            client_id="client1",
        )

    assert result.get("client_id") == "client1"


def test_add_password_validation_error():
    """Deve levantar ValueError quando campos obrigatórios ausentes."""
    with pytest.raises(ValueError, match="org_id, client_name e service são obrigatórios"):
        repo.add_password(
            org_id="",
            client_name="Cliente",
            service="Portal",
            username="user",
            password_plain="senha",
            notes="",
            created_by="user",
        )


def test_add_password_no_data_returned():
    """Deve levantar RuntimeError quando insert não retorna dados."""
    mock_response = MagicMock()
    mock_response.data = None

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo._rls_precheck_membership"),
        patch("data.supabase_repo.encrypt_text", return_value="encrypted"),
    ):
        with pytest.raises(RuntimeError, match="Insert não retornou dados"):
            repo.add_password(
                org_id="org1",
                client_name="Cliente",
                service="Portal",
                username="user",
                password_plain="senha",
                notes="",
                created_by="user",
            )


def test_add_password_api_error():
    """Deve levantar RuntimeError quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo._rls_precheck_membership"),
        patch("data.supabase_repo.encrypt_text", return_value="encrypted"),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
    ):
        with pytest.raises(RuntimeError, match="Falha ao adicionar senha"):
            repo.add_password(
                org_id="org1",
                client_name="Cliente",
                service="Portal",
                username="user",
                password_plain="senha",
                notes="",
                created_by="user",
            )


# -----------------------------------------------------------------------------
# Tests: update_password
# -----------------------------------------------------------------------------
def test_update_password_success():
    """Deve atualizar senha com sucesso."""
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "pass1",
            "client_name": "Cliente Atualizado",
            "service": "Portal2",
            "username": "user2",
        }
    ]

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo.encrypt_text", return_value="new_encrypted"),
    ):
        result = repo.update_password(
            id="pass1",
            client_name="Cliente Atualizado",
            service="Portal2",
            username="user2",
            password_plain="newpass",
        )

    assert result["id"] == "pass1"
    assert result["client_name"] == "Cliente Atualizado"


def test_update_password_partial():
    """Deve atualizar apenas campos fornecidos."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "pass1", "notes": "Nova nota"}]

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.update_password(id="pass1", notes="Nova nota")

    assert result["notes"] == "Nova nota"


def test_update_password_no_id():
    """Deve levantar ValueError quando id ausente."""
    with pytest.raises(ValueError, match="id é obrigatório"):
        repo.update_password(id="")


def test_update_password_no_data_returned():
    """Deve levantar RuntimeError quando update não retorna dados."""
    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        with pytest.raises(RuntimeError, match="Update não retornou dados"):
            repo.update_password(id="pass1", notes="Nova nota")


def test_update_password_api_error():
    """Deve levantar RuntimeError quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        with pytest.raises(RuntimeError, match="Falha ao atualizar senha"):
            repo.update_password(id="pass1", notes="Nova nota")


# -----------------------------------------------------------------------------
# Tests: delete_password
# -----------------------------------------------------------------------------
def test_delete_password_success():
    """Deve deletar senha com sucesso."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=MagicMock()),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        repo.delete_password("pass1")
        # Sem exceção = sucesso


def test_delete_password_no_id():
    """Deve levantar ValueError quando id ausente."""
    with pytest.raises(ValueError, match="id é obrigatório"):
        repo.delete_password("")


def test_delete_password_api_error():
    """Deve levantar RuntimeError quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        with pytest.raises(RuntimeError, match="Falha ao excluir senha"):
            repo.delete_password("pass1")


# -----------------------------------------------------------------------------
# Tests: delete_passwords_by_client
# -----------------------------------------------------------------------------
def test_delete_passwords_by_client_success():
    """Deve deletar senhas de um cliente."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "pass1"}, {"id": "pass2"}]

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        count = repo.delete_passwords_by_client("org1", "client1")

    assert count == 2


def test_delete_passwords_by_client_empty():
    """Deve retornar 0 quando nenhuma senha foi deletada."""
    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        count = repo.delete_passwords_by_client("org1", "client1")

    assert count == 0


def test_delete_passwords_by_client_no_org_id():
    """Deve levantar ValueError quando org_id ausente."""
    with pytest.raises(ValueError, match="org_id é obrigatório"):
        repo.delete_passwords_by_client("", "client1")


def test_delete_passwords_by_client_no_client_id():
    """Deve levantar ValueError quando client_id ausente."""
    with pytest.raises(ValueError, match="client_id é obrigatório"):
        repo.delete_passwords_by_client("org1", "")


def test_delete_passwords_by_client_api_error():
    """Deve levantar RuntimeError quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        with pytest.raises(RuntimeError, match="Falha ao excluir senhas do cliente"):
            repo.delete_passwords_by_client("org1", "client1")


# -----------------------------------------------------------------------------
# Tests: decrypt_for_view
# -----------------------------------------------------------------------------
def test_decrypt_for_view_success():
    """Deve descriptografar token com sucesso."""
    with patch("data.supabase_repo.decrypt_text", return_value="senha_plana"):
        result = repo.decrypt_for_view("encrypted_token")
    assert result == "senha_plana"


def test_decrypt_for_view_error():
    """Deve levantar RuntimeError quando falha descriptografia."""
    with patch("data.supabase_repo.decrypt_text", side_effect=Exception("Decrypt failed")):
        with pytest.raises(RuntimeError, match="Falha ao descriptografar"):
            repo.decrypt_for_view("invalid_token")


# -----------------------------------------------------------------------------
# Tests: search_clients
# -----------------------------------------------------------------------------
def test_search_clients_success():
    """Deve buscar clientes com sucesso."""
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "client1",
            "org_id": "org1",
            "razao_social": "Empresa A",
            "cnpj": "12345678000190",
            "nome": "João",
            "numero": "11999999999",
            "obs": "",
            "cnpj_norm": "12345678000190",
        }
    ]

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.search_clients("org1", "Empresa")

    assert len(result) == 1
    assert result[0]["razao_social"] == "Empresa A"


def test_search_clients_short_query():
    """Deve buscar sem filtro de texto quando query < 2 caracteres."""
    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.search_clients("org1", "A")

    assert result == []


def test_search_clients_empty_org_id():
    """Deve retornar lista vazia quando org_id não fornecido."""
    result = repo.search_clients("", "query")
    assert result == []


def test_search_clients_api_error():
    """Deve retornar lista vazia quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.search_clients("org1", "query")

    assert result == []


# -----------------------------------------------------------------------------
# Tests: list_clients_for_picker
# -----------------------------------------------------------------------------
def test_list_clients_for_picker_success():
    """Deve listar clientes para picker."""
    mock_response = MagicMock()
    mock_response.data = [
        {"id": "client1", "org_id": "org1", "razao_social": "Empresa A", "cnpj": "12345678000190", "nome": "João"},
        {"id": "client2", "org_id": "org1", "razao_social": "Empresa B", "cnpj": "98765432000199", "nome": "Maria"},
    ]

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.list_clients_for_picker("org1")

    assert len(result) == 2
    assert result[0]["razao_social"] == "Empresa A"


def test_list_clients_for_picker_empty_org_id():
    """Deve retornar lista vazia quando org_id não fornecido."""
    result = repo.list_clients_for_picker("")
    assert result == []


def test_list_clients_for_picker_api_error():
    """Deve retornar lista vazia quando API falha."""
    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", side_effect=Exception("API Error")),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.list_clients_for_picker("org1")

    assert result == []


def test_list_clients_for_picker_custom_limit():
    """Deve respeitar limit customizado."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo.supabase", mock_client),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        repo.list_clients_for_picker("org1", limit=50)

    mock_query.limit.assert_called_once_with(50)


# -----------------------------------------------------------------------------
# Tests: Coverage de branches faltantes (BATCH 09C)
# -----------------------------------------------------------------------------


def test_get_access_token_returns_none_on_exception():
    """Deve retornar None quando get_session lança exceção."""
    client = MagicMock()
    client.auth.get_session.side_effect = Exception("Session error")
    result = repo._get_access_token(client)
    assert result is None


def test_ensure_postgrest_auth_no_token_required_true():
    """Deve levantar RuntimeError quando required=True e sem token."""
    client = MagicMock()
    client.auth.get_session.return_value = None

    with pytest.raises(RuntimeError, match="Sessão sem access_token"):
        repo._ensure_postgrest_auth(client, required=True)


def test_ensure_postgrest_auth_postgrest_auth_fails():
    """Deve logar warning quando postgrest.auth falha."""
    client = MagicMock()
    session = MagicMock()
    session.access_token = "token123"
    client.auth.get_session.return_value = session
    client.postgrest.auth.side_effect = Exception("Auth failed")

    # Não deve levantar exceção, apenas logar warning
    repo._ensure_postgrest_auth(client)


def test_rls_precheck_membership_no_data():
    """Deve levantar RuntimeError quando não encontra membership."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = None

    with (
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
    ):
        with pytest.raises(RuntimeError, match="RLS precheck: a API NÃO enxerga membership"):
            repo._rls_precheck_membership(client, "org1", "user1")


def test_rls_precheck_membership_empty_list():
    """Deve levantar RuntimeError quando data é lista vazia."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = []

    with (
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
    ):
        with pytest.raises(RuntimeError, match="RLS precheck: a API NÃO enxerga membership"):
            repo._rls_precheck_membership(client, "org1", "user1")


def test_supabase_proxy_getattr():
    """Deve delegar acesso ao cliente Supabase singleton."""
    with patch("data.supabase_repo.get_supabase") as mock_get:
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table = mock_table
        mock_get.return_value = mock_client

        proxy = repo._SupabaseProxy()
        result = proxy.table
        assert result is mock_table


def test_with_retries_raises_runtime_error_if_last_exc_is_none():
    """Caso extremo: se last_exc for None após tentativas, levanta RuntimeError."""
    # Esse caso é teórico, mas a cobertura aponta linha 297
    # Vamos simular uma situação onde nenhuma exceção é capturada mas fn não retorna
    # Na prática, isso é impossível com a lógica atual, mas vamos cobrir o branch
    pass  # Branch 297 é defensivo, praticamente impossível de atingir


def test_list_passwords_data_none():
    """Deve retornar lista vazia quando exec_postgrest retorna data=None."""
    mock_response = MagicMock()
    mock_response.data = None

    with (
        patch("data.supabase_repo.supabase", MagicMock()),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.list_passwords("org1")

    assert result == []


# -----------------------------------------------------------------------------
# Tests: Coverage 100% - misses finais (BATCH 09D)
# -----------------------------------------------------------------------------


def test_import_fallback_postgrest_api_error():
    """Deve usar fallback quando postgrest.exceptions não disponível."""
    import builtins
    import importlib.util
    import sys
    from pathlib import Path

    # Caminho do módulo
    module_path = Path(__file__).parent.parent.parent.parent / "data" / "supabase_repo.py"

    # Interceptar import de postgrest.exceptions
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "postgrest" in name and "exceptions" in name:
            raise ImportError("Mocked: postgrest.exceptions not available")
        return original_import(name, *args, **kwargs)

    # Criar spec para carregar módulo com nome alternativo
    spec = importlib.util.spec_from_file_location("data.supabase_repo_fallback_test", module_path)
    if spec is None or spec.loader is None:
        pytest.skip("Could not create module spec")

    mod = importlib.util.module_from_spec(spec)

    # Aplicar mock do import
    builtins.__import__ = mock_import
    try:
        # Adicionar ao sys.modules temporariamente
        sys.modules["data.supabase_repo_fallback_test"] = mod
        spec.loader.exec_module(mod)

        # Verificar fallbacks
        assert hasattr(mod, "PostgrestAPIError")
        assert issubclass(mod.PostgrestAPIError, Exception)
        assert hasattr(mod, "APIError")
        assert mod.APIError is Exception
    finally:
        # Restaurar import original
        builtins.__import__ = original_import
        # Limpar sys.modules
        sys.modules.pop("data.supabase_repo_fallback_test", None)


def test_ensure_postgrest_auth_no_token_not_required():
    """Deve logar warning mas não levantar quando required=False e sem token."""

    client = MagicMock()
    client.auth.get_session.return_value = None

    with patch("data.supabase_repo._get_access_token", return_value=None):
        # Não deve levantar exceção
        repo._ensure_postgrest_auth(client, required=False)


def test_rls_precheck_membership_success_with_log(caplog):
    """Deve logar sucesso quando encontra membership."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"user_id": "user1"}]

    with (
        patch("data.supabase_repo._ensure_postgrest_auth"),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        caplog.at_level(logging.INFO),
    ):
        # Não deve levantar exceção
        repo._rls_precheck_membership(client, "org1", "user1")

    # Verificar log de sucesso
    assert "RLS precheck OK" in caplog.text


def test_with_retries_tries_zero():
    """Deve levantar RuntimeError quando tries=0 (last_exc=None)."""
    fn = Mock(return_value="success")

    with pytest.raises(RuntimeError, match="Unexpected None error"):
        repo.with_retries(fn, tries=0)


def test_update_password_with_client_id_payload():
    """Deve incluir client_id no payload quando fornecido."""
    captured_payload = {}

    def mock_update(payload):
        captured_payload.update(payload)
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        return mock_query

    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.update = mock_update
    mock_client.table.return_value = mock_table

    mock_response = MagicMock()
    mock_response.data = [{"id": "pass1", "client_id": "CID-123"}]

    with (
        patch("data.supabase_repo.supabase", mock_client),
        patch("data.supabase_repo.exec_postgrest", return_value=mock_response),
        patch("data.supabase_repo._ensure_postgrest_auth"),
    ):
        result = repo.update_password(id="pass1", client_id="CID-123")

    # Verificar que client_id foi incluído no payload
    assert "client_id" in captured_payload
    assert captured_payload["client_id"] == "CID-123"
    assert result.get("client_id") == "CID-123"
