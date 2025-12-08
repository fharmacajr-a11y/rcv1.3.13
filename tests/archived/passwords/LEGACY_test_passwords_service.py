"""LEGACY TEST - Service Antigo de Senhas

Este arquivo cobre o service antigo de senhas.
Não faz parte da bateria de regressão atual; mantido apenas por referência.

Cobertura de:
- Listagem de senhas com filtros
- Criação de senhas
- Atualização de senhas
- Exclusão de senhas
"""

import pytest

pytestmark = [
    pytest.mark.legacy_ui,
    pytest.mark.skip(reason="Service antigo, mantido apenas como referência histórica"),
]

pytest.skip(
    "Legacy tests de Senhas (pré-refactor). Mantidos apenas como referência. "
    "Senhas agora é coberto por testes em tests/modules/passwords e "
    "tests/integration/passwords.",
    allow_module_level=True,
)

# ruff: noqa: E402

from unittest.mock import patch

from infra.repositories import passwords_repository


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_passwords():
    """Senhas de exemplo para testes."""
    return [
        {
            "id": "pwd-1",
            "org_id": "org-123",
            "client_name": "Cliente A",
            "service": "Email",
            "username": "admin@clientea.com",
            "password_encrypted": "encrypted-data-1",
            "notes": "Senha principal",
            "created_by": "user-1",
        },
        {
            "id": "pwd-2",
            "org_id": "org-123",
            "client_name": "Cliente A",
            "service": "FTP",
            "username": "ftp_user",
            "password_encrypted": "encrypted-data-2",
            "notes": "",
            "created_by": "user-1",
        },
        {
            "id": "pwd-3",
            "org_id": "org-123",
            "client_name": "Cliente B",
            "service": "Database",
            "username": "db_admin",
            "password_encrypted": "encrypted-data-3",
            "notes": "Prod DB",
            "created_by": "user-2",
        },
    ]


# ============================================================================
# TESTES - get_passwords()
# ============================================================================


def test_get_passwords_no_filters(sample_passwords):
    """Testa listagem sem filtros."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(org_id="org-123")

    assert len(result) == 3
    assert result[0]["id"] == "pwd-1"


def test_get_passwords_with_search_text_in_client_name(sample_passwords):
    """Testa busca por texto no nome do cliente."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="Cliente A",
        )

    assert len(result) == 2
    assert all("Cliente A" in p["client_name"] for p in result)


def test_get_passwords_with_search_text_in_service(sample_passwords):
    """Testa busca por texto no serviço."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="email",
        )

    assert len(result) == 1
    assert result[0]["service"].lower() == "email"


def test_get_passwords_with_search_text_in_username(sample_passwords):
    """Testa busca por texto no username."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="ftp_user",
        )

    assert len(result) == 1
    assert result[0]["username"] == "ftp_user"


def test_get_passwords_with_search_text_case_insensitive(sample_passwords):
    """Testa busca case-insensitive."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="DATABASE",  # uppercase
        )

    assert len(result) == 1
    assert result[0]["service"] == "Database"


def test_get_passwords_with_client_filter(sample_passwords):
    """Testa filtro por cliente específico."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            client_filter="Cliente A",
        )

    assert len(result) == 2
    assert all(p["client_name"] == "Cliente A" for p in result)


def test_get_passwords_with_client_filter_todos(sample_passwords):
    """Testa filtro 'Todos' (não filtra)."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            client_filter="Todos",
        )

    assert len(result) == 3


def test_get_passwords_with_search_and_client_filter(sample_passwords):
    """Testa busca + filtro de cliente combinados."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="user",
            client_filter="Cliente A",
        )

    # Apenas pwd-2 (Cliente A + "user" no username)
    assert len(result) == 1
    assert result[0]["id"] == "pwd-2"


def test_get_passwords_empty_result(sample_passwords):
    """Testa quando não há senhas que atendam os critérios."""
    with patch("data.supabase_repo.list_passwords", return_value=sample_passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="inexistente",
        )

    assert result == []


def test_get_passwords_empty_org(sample_passwords):
    """Testa quando organização não tem senhas."""
    with patch("data.supabase_repo.list_passwords", return_value=[]):
        result = passwords_repository.get_passwords(org_id="org-999")

    assert result == []


# ============================================================================
# TESTES - create_password()
# ============================================================================


def test_create_password_basic():
    """Testa criação de senha."""
    new_password = {
        "id": "pwd-new",
        "org_id": "org-123",
        "client_name": "Cliente C",
        "service": "SSH",
        "username": "root",
        "password_encrypted": "encrypted-secret",
        "notes": "Servidor prod",
        "created_by": "user-3",
    }

    with patch("data.supabase_repo.add_password", return_value=new_password):
        result = passwords_repository.create_password(
            org_id="org-123",
            client_name="Cliente C",
            service="SSH",
            username="root",
            password_plain="secret123",
            notes="Servidor prod",
            created_by="user-3",
        )

    assert result["id"] == "pwd-new"
    assert result["client_name"] == "Cliente C"
    assert result["service"] == "SSH"


def test_create_password_empty_notes():
    """Testa criação sem notas."""
    new_password = {
        "id": "pwd-new",
        "org_id": "org-123",
        "client_name": "Cliente D",
        "service": "API",
        "username": "api_key",
        "password_encrypted": "encrypted-key",
        "notes": "",
        "created_by": "user-1",
    }

    with patch("data.supabase_repo.add_password", return_value=new_password):
        result = passwords_repository.create_password(
            org_id="org-123",
            client_name="Cliente D",
            service="API",
            username="api_key",
            password_plain="abc123",
            notes="",
            created_by="user-1",
        )

    assert result["notes"] == ""


# ============================================================================
# TESTES - update_password_by_id()
# ============================================================================


def test_update_password_all_fields():
    """Testa atualização de todos os campos."""
    updated = {
        "id": "pwd-1",
        "client_name": "Cliente A Updated",
        "service": "Email Updated",
        "username": "newemail@clientea.com",
        "password_encrypted": "new-encrypted",
        "notes": "Notas atualizadas",
    }

    with patch("data.supabase_repo.update_password", return_value=updated):
        result = passwords_repository.update_password_by_id(
            password_id="pwd-1",
            client_name="Cliente A Updated",
            service="Email Updated",
            username="newemail@clientea.com",
            password_plain="newpassword123",
            notes="Notas atualizadas",
        )

    assert result["client_name"] == "Cliente A Updated"
    assert result["service"] == "Email Updated"


def test_update_password_partial_fields():
    """Testa atualização parcial (apenas alguns campos)."""
    updated = {
        "id": "pwd-2",
        "username": "new_ftp_user",
    }

    with patch("data.supabase_repo.update_password", return_value=updated):
        result = passwords_repository.update_password_by_id(
            password_id="pwd-2",
            username="new_ftp_user",
        )

    assert result["username"] == "new_ftp_user"


def test_update_password_only_notes():
    """Testa atualização apenas das notas."""
    updated = {
        "id": "pwd-3",
        "notes": "Notas completamente novas",
    }

    with patch("data.supabase_repo.update_password", return_value=updated):
        result = passwords_repository.update_password_by_id(
            password_id="pwd-3",
            notes="Notas completamente novas",
        )

    assert result["notes"] == "Notas completamente novas"


# ============================================================================
# TESTES - delete_password_by_id()
# ============================================================================


def test_delete_password_basic():
    """Testa exclusão de senha."""
    with patch("data.supabase_repo.delete_password") as mock_delete:
        passwords_repository.delete_password_by_id("pwd-999")
        mock_delete.assert_called_once_with("pwd-999")


def test_delete_password_multiple_calls():
    """Testa múltiplas exclusões."""
    with patch("data.supabase_repo.delete_password") as mock_delete:
        passwords_repository.delete_password_by_id("pwd-1")
        passwords_repository.delete_password_by_id("pwd-2")

        assert mock_delete.call_count == 2


# ============================================================================
# TESTES - EDGE CASES
# ============================================================================


def test_get_passwords_search_matches_multiple_fields():
    """Testa busca que pode dar match em vários campos."""
    passwords = [
        {
            "id": "pwd-1",
            "client_name": "Admin Corp",
            "service": "Linux Server",
            "username": "admin@example.com",
        },
    ]

    with patch("data.supabase_repo.list_passwords", return_value=passwords):
        # Busca por "admin" deve encontrar (está em client_name E username)
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="admin",
        )

    assert len(result) == 1
    assert result[0]["id"] == "pwd-1"


def test_get_passwords_search_no_partial_match():
    """Testa que busca NÃO encontra se não for substring."""
    passwords = [
        {"id": "pwd-1", "client_name": "ABC", "service": "XYZ", "username": "user"},
    ]

    with patch("data.supabase_repo.list_passwords", return_value=passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="DEF",  # Não existe em nenhum campo
        )

    assert result == []


def test_get_passwords_special_characters_in_search():
    """Testa busca com caracteres especiais."""
    passwords = [
        {
            "id": "pwd-1",
            "client_name": "Cliente & Cia",
            "service": "Email",
            "username": "admin@example.com",
        },
    ]

    with patch("data.supabase_repo.list_passwords", return_value=passwords):
        result = passwords_repository.get_passwords(
            org_id="org-123",
            search_text="& Cia",
        )

    assert len(result) == 1
