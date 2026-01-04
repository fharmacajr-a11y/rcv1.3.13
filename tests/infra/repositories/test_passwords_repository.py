# -*- coding: utf-8 -*-
"""
Testes unitários para infra/repositories/passwords_repository.py

Objetivo: aumentar cobertura de 25.8% para ≥85-90% testando todos os branches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from src.db.domain_types import PasswordRow
from src.infra.repositories.passwords_repository import (
    create_password,
    delete_all_passwords_for_client,
    delete_password_by_id,
    find_duplicate_password_by_service,
    get_passwords,
    update_password_by_id,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_passwords() -> list[PasswordRow]:
    """Lista de senhas de exemplo para testes."""
    return [
        {
            "id": "pwd-001",
            "org_id": "org-123",
            "client_name": "Empresa XYZ",
            "service": "Gmail",
            "username": "contato@xyz.com",
            "password_enc": "encrypted_password_1",
            "notes": "Conta compartilhada",
            "created_by": "user-456",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
        },
        {
            "id": "pwd-002",
            "org_id": "org-123",
            "client_name": "Empresa ABC",
            "service": "AWS Console",
            "username": "admin@abc.com",
            "password_enc": "encrypted_password_2",
            "notes": "Acesso root",
            "created_by": "user-456",
            "created_at": "2025-01-02T11:00:00",
            "updated_at": "2025-01-02T11:00:00",
        },
        {
            "id": "pwd-003",
            "org_id": "org-123",
            "client_name": "Empresa XYZ",
            "service": "ANVISA",
            "username": "usuario.anvisa",
            "password_enc": "encrypted_password_3",
            "notes": "Portal ANVISA",
            "created_by": "user-789",
            "created_at": "2025-01-03T12:00:00",
            "updated_at": "2025-01-03T12:00:00",
        },
    ]


# ============================================================================
# Test get_passwords
# ============================================================================


def test_get_passwords_sem_filtros_retorna_todas(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords sem filtros deve retornar todas as senhas."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123")

        assert len(result) == 3
        assert result == sample_passwords
        # PERF-003: Atualizado para incluir parâmetros de paginação
        mock_list.assert_called_once_with("org-123", limit=None, offset=0)


def test_get_passwords_com_search_text_filtra_client_name(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com search_text deve filtrar por client_name (case-insensitive)."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", search_text="xyz")

        assert len(result) == 2  # Empresa XYZ aparece 2 vezes
        assert all("XYZ" in p["client_name"] for p in result)


def test_get_passwords_com_search_text_filtra_service(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com search_text deve filtrar por service (case-insensitive)."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", search_text="gmail")

        assert len(result) == 1
        assert result[0]["service"] == "Gmail"


def test_get_passwords_com_search_text_filtra_username(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com search_text deve filtrar por username (case-insensitive)."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", search_text="admin")

        assert len(result) == 1
        assert "admin" in result[0]["username"]


def test_get_passwords_com_search_text_vazio_retorna_todas(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com search_text vazio deve retornar todas."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", search_text="")

        assert len(result) == 3


def test_get_passwords_com_search_text_nao_encontrado_retorna_vazio(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com search_text que não existe deve retornar lista vazia."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", search_text="inexistente")

        assert len(result) == 0


def test_get_passwords_com_client_filter_filtra_corretamente(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com client_filter deve filtrar exatamente pelo nome do cliente."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", client_filter="Empresa XYZ")

        assert len(result) == 2
        assert all(p["client_name"] == "Empresa XYZ" for p in result)


def test_get_passwords_com_client_filter_todos_nao_filtra(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com client_filter='Todos' não deve filtrar."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", client_filter="Todos")

        assert len(result) == 3


def test_get_passwords_com_client_filter_none_nao_filtra(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com client_filter=None não deve filtrar."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", client_filter=None)

        assert len(result) == 3


def test_get_passwords_com_ambos_filtros_aplica_ambos(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com search_text e client_filter deve aplicar ambos os filtros."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", search_text="anvisa", client_filter="Empresa XYZ")

        assert len(result) == 1
        assert result[0]["service"] == "ANVISA"
        assert result[0]["client_name"] == "Empresa XYZ"


def test_get_passwords_lista_vazia_retorna_vazio() -> None:
    """get_passwords deve retornar lista vazia quando não há senhas."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = []

        result = get_passwords("org-123")

        assert result == []


# ============================================================================
# Test get_passwords com paginação (PERF-003)
# ============================================================================


def test_get_passwords_com_limit_e_offset(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords deve passar limit e offset para list_passwords."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords[:2]  # Simula que retornou apenas 2

        result = get_passwords("org-123", limit=2, offset=0)

        assert len(result) == 2
        mock_list.assert_called_once_with("org-123", limit=2, offset=0)


def test_get_passwords_com_limit_none_retorna_todas(sample_passwords: list[PasswordRow]) -> None:
    """get_passwords com limit=None deve retornar todas as senhas."""
    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = sample_passwords

        result = get_passwords("org-123", limit=None, offset=0)

        assert len(result) == 3
        mock_list.assert_called_once_with("org-123", limit=None, offset=0)


# ============================================================================
# Test create_password
# ============================================================================


def test_create_password_chama_add_password_com_parametros_corretos() -> None:
    """create_password deve delegar para add_password com todos os parâmetros."""
    with patch("src.db.supabase_repo.add_password") as mock_add:
        fake_password: PasswordRow = {
            "id": "pwd-new",
            "org_id": "org-123",
            "client_name": "Empresa XYZ",
            "service": "Gmail",
            "username": "contato@xyz.com",
            "password_enc": "encrypted_new",
            "notes": "Nova senha",
            "created_by": "user-456",
            "created_at": "2025-12-08T10:00:00",
            "updated_at": "2025-12-08T10:00:00",
        }
        mock_add.return_value = fake_password

        result = create_password(
            org_id="org-123",
            client_name="Empresa XYZ",
            service="Gmail",
            username="contato@xyz.com",
            password_plain="senhaSegura123",
            notes="Nova senha",
            created_by="user-456",
            client_id="256",
        )

        assert result == fake_password
        mock_add.assert_called_once_with(
            "org-123",
            "Empresa XYZ",
            "Gmail",
            "contato@xyz.com",
            "senhaSegura123",
            "Nova senha",
            "user-456",
            "256",
        )


def test_create_password_sem_client_id_funciona() -> None:
    """create_password deve funcionar sem client_id (valor padrão None)."""
    with patch("src.db.supabase_repo.add_password") as mock_add:
        fake_password: PasswordRow = {
            "id": "pwd-new",
            "org_id": "org-123",
            "client_name": "Empresa XYZ",
            "service": "Gmail",
            "username": "contato@xyz.com",
            "password_enc": "encrypted_new",
            "notes": "Nova senha",
            "created_by": "user-456",
            "created_at": "2025-12-08T10:00:00",
            "updated_at": "2025-12-08T10:00:00",
        }
        mock_add.return_value = fake_password

        result = create_password(
            org_id="org-123",
            client_name="Empresa XYZ",
            service="Gmail",
            username="contato@xyz.com",
            password_plain="senhaSegura123",
            notes="Nova senha",
            created_by="user-456",
        )

        assert result == fake_password
        # Verifica que client_id foi passado como None
        assert mock_add.call_args[0][7] is None


# ============================================================================
# Test update_password_by_id
# ============================================================================


def test_update_password_by_id_chama_update_password_com_todos_parametros() -> None:
    """update_password_by_id deve delegar para update_password."""
    with patch("src.db.supabase_repo.update_password") as mock_update:
        fake_updated: PasswordRow = {
            "id": "pwd-001",
            "org_id": "org-123",
            "client_name": "Empresa XYZ Atualizada",
            "service": "Gmail",
            "username": "novo@xyz.com",
            "password_enc": "encrypted_updated",
            "notes": "Senha atualizada",
            "created_by": "user-456",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-12-08T11:00:00",
        }
        mock_update.return_value = fake_updated

        result = update_password_by_id(
            password_id="pwd-001",
            client_name="Empresa XYZ Atualizada",
            service="Gmail",
            username="novo@xyz.com",
            password_plain="novaSenha456",
            notes="Senha atualizada",
            client_id="256",
        )

        assert result == fake_updated
        mock_update.assert_called_once_with(
            "pwd-001",
            "Empresa XYZ Atualizada",
            "Gmail",
            "novo@xyz.com",
            "novaSenha456",
            "Senha atualizada",
            "256",
        )


def test_update_password_by_id_com_campos_none_mantem_valores() -> None:
    """update_password_by_id com campos None deve passar None (manter valores atuais)."""
    with patch("src.db.supabase_repo.update_password") as mock_update:
        fake_updated: PasswordRow = {
            "id": "pwd-001",
            "org_id": "org-123",
            "client_name": "Empresa XYZ",
            "service": "Gmail",
            "username": "contato@xyz.com",
            "password_enc": "encrypted_updated",
            "notes": "Apenas senha atualizada",
            "created_by": "user-456",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-12-08T11:00:00",
        }
        mock_update.return_value = fake_updated

        result = update_password_by_id(
            password_id="pwd-001",
            password_plain="novaSenha456",
        )

        assert result == fake_updated
        mock_update.assert_called_once_with(
            "pwd-001",
            None,  # client_name
            None,  # service
            None,  # username
            "novaSenha456",  # password_plain
            None,  # notes
            None,  # client_id
        )


# ============================================================================
# Test delete_password_by_id
# ============================================================================


def test_delete_password_by_id_chama_delete_password() -> None:
    """delete_password_by_id deve delegar para delete_password."""
    with patch("src.db.supabase_repo.delete_password") as mock_delete:
        mock_delete.return_value = None

        result = delete_password_by_id("pwd-789")

        assert result is None
        mock_delete.assert_called_once_with("pwd-789")


# ============================================================================
# Test delete_all_passwords_for_client
# ============================================================================


def test_delete_all_passwords_for_client_retorna_count() -> None:
    """delete_all_passwords_for_client deve retornar número de senhas excluídas."""
    with patch("src.db.supabase_repo.delete_passwords_by_client") as mock_delete_all:
        mock_delete_all.return_value = 5

        result = delete_all_passwords_for_client("org-123", "256")

        assert result == 5
        mock_delete_all.assert_called_once_with("org-123", "256")


def test_delete_all_passwords_for_client_sem_senhas_retorna_zero() -> None:
    """delete_all_passwords_for_client sem senhas deve retornar 0."""
    with patch("src.db.supabase_repo.delete_passwords_by_client") as mock_delete_all:
        mock_delete_all.return_value = 0

        result = delete_all_passwords_for_client("org-123", "999")

        assert result == 0
        mock_delete_all.assert_called_once_with("org-123", "999")


# ============================================================================
# Test find_duplicate_password_by_service
# ============================================================================


def test_find_duplicate_password_by_service_encontra_duplicatas(sample_passwords: list[PasswordRow]) -> None:
    """find_duplicate_password_by_service deve encontrar senhas com mesmo cliente+serviço."""
    # Adicionar client_id aos samples
    passwords_with_client_id = sample_passwords.copy()
    passwords_with_client_id[0]["client_id"] = "256"  # type: ignore[typeddict-item]
    passwords_with_client_id[1]["client_id"] = "257"  # type: ignore[typeddict-item]
    passwords_with_client_id[2]["client_id"] = "256"  # type: ignore[typeddict-item]

    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = passwords_with_client_id

        result = find_duplicate_password_by_service(
            org_id="org-123",
            client_id="256",
            service="Gmail",
        )

        assert len(result) == 1
        assert result[0]["service"] == "Gmail"
        assert result[0]["client_id"] == "256"  # type: ignore[typeddict-item]


def test_find_duplicate_password_by_service_nao_encontra_retorna_vazio(sample_passwords: list[PasswordRow]) -> None:
    """find_duplicate_password_by_service sem duplicatas deve retornar lista vazia."""
    passwords_with_client_id = sample_passwords.copy()
    passwords_with_client_id[0]["client_id"] = "256"  # type: ignore[typeddict-item]
    passwords_with_client_id[1]["client_id"] = "257"  # type: ignore[typeddict-item]
    passwords_with_client_id[2]["client_id"] = "256"  # type: ignore[typeddict-item]

    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = passwords_with_client_id

        result = find_duplicate_password_by_service(
            org_id="org-123",
            client_id="999",
            service="Gmail",
        )

        assert len(result) == 0


def test_find_duplicate_password_by_service_multiplas_duplicatas(sample_passwords: list[PasswordRow]) -> None:
    """find_duplicate_password_by_service deve retornar todas as duplicatas."""
    # Criar cenário com múltiplas senhas para mesmo cliente+serviço
    passwords_with_client_id = sample_passwords.copy()
    passwords_with_client_id[0]["client_id"] = "256"  # type: ignore[typeddict-item]
    passwords_with_client_id[0]["service"] = "ANVISA"
    passwords_with_client_id[1]["client_id"] = "256"  # type: ignore[typeddict-item]
    passwords_with_client_id[1]["service"] = "ANVISA"
    passwords_with_client_id[2]["client_id"] = "256"  # type: ignore[typeddict-item]
    passwords_with_client_id[2]["service"] = "ANVISA"

    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = passwords_with_client_id

        result = find_duplicate_password_by_service(
            org_id="org-123",
            client_id="256",
            service="ANVISA",
        )

        assert len(result) == 3
        assert all(p["service"] == "ANVISA" for p in result)
        assert all(p.get("client_id") == "256" for p in result)


def test_find_duplicate_password_by_service_sem_client_id_nao_encontra() -> None:
    """find_duplicate_password_by_service não deve encontrar senhas sem client_id."""
    passwords_without_client_id: list[PasswordRow] = [
        {
            "id": "pwd-001",
            "org_id": "org-123",
            "client_name": "Empresa XYZ",
            "service": "Gmail",
            "username": "contato@xyz.com",
            "password_enc": "encrypted_password_1",
            "notes": "Sem client_id",
            "created_by": "user-456",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
        }
    ]

    with patch("src.db.supabase_repo.list_passwords") as mock_list:
        mock_list.return_value = passwords_without_client_id

        result = find_duplicate_password_by_service(
            org_id="org-123",
            client_id="256",
            service="Gmail",
        )

        assert len(result) == 0
