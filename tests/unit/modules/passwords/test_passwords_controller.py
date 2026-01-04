"""Testes unitários para PasswordsController.

FASE 6 - Cobertura de casos de borda e erros.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.db.domain_types import PasswordRow
from tests.unit.modules.passwords.conftest import make_password_row

from src.modules.passwords.controller import PasswordsController


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def controller() -> PasswordsController:
    """Controller limpo para testes."""
    return PasswordsController()


@pytest.fixture
def sample_passwords() -> list[PasswordRow]:
    """Senhas de exemplo para testes."""
    return [
        make_password_row(
            id="pwd-1",
            client_id="client-1",
            client_name="Alpha Corp",
            service="SIFAP",
            username="alpha@sifap.gov",
            password_enc="encrypted_password_1",
            notes="Nota 1",
        ),
        make_password_row(
            id="pwd-2",
            client_id="client-1",
            client_name="Alpha Corp",
            service="GOV.BR",
            username="alpha@gov.br",
            password_enc="encrypted_password_2",
            notes="Nota 2",
        ),
        make_password_row(
            id="pwd-3",
            client_id="client-2",
            client_name="Beta Ltda",
            service="ANVISA",
            username="beta@anvisa.gov",
            password_enc="encrypted_password_3",
            notes="",
        ),
    ]


# ========================================
# Testes de decrypt_password
# ========================================


class TestDecryptPassword:
    """Testes para controller.decrypt_password()."""

    def test_decrypt_password_success(self, controller: PasswordsController) -> None:
        """Decrypt com token válido deve retornar texto plano."""
        with patch("src.modules.passwords.controller.decrypt_text") as mock_decrypt:
            mock_decrypt.return_value = "senha_secreta_123"

            result = controller.decrypt_password("encrypted_token_abc")

            mock_decrypt.assert_called_once_with("encrypted_token_abc")
            assert result == "senha_secreta_123"

    def test_decrypt_password_empty_token(self, controller: PasswordsController) -> None:
        """Decrypt de token vazio deve retornar vazio."""
        with patch("src.modules.passwords.controller.decrypt_text") as mock_decrypt:
            mock_decrypt.return_value = ""

            result = controller.decrypt_password("")

            mock_decrypt.assert_called_once_with("")
            assert result == ""

    def test_decrypt_password_crypto_error_propagates(self, controller: PasswordsController) -> None:
        """Erro de crypto deve propagar como RuntimeError."""
        with patch("src.modules.passwords.controller.decrypt_text") as mock_decrypt:
            mock_decrypt.side_effect = RuntimeError("Falha na descriptografia")

            with pytest.raises(RuntimeError, match="Falha na descriptografia"):
                controller.decrypt_password("invalid_token")


# ========================================
# Testes de get_passwords_for_client
# ========================================


class TestGetPasswordsForClient:
    """Testes para controller.get_passwords_for_client()."""

    def test_get_passwords_for_client_returns_filtered(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve retornar apenas senhas do cliente especificado."""
        controller._all_passwords = sample_passwords

        result = controller.get_passwords_for_client("client-1")

        assert len(result) == 2
        assert all(p["client_id"] == "client-1" for p in result)

    def test_get_passwords_for_client_empty_when_no_match(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve retornar lista vazia se cliente não tem senhas."""
        controller._all_passwords = sample_passwords

        result = controller.get_passwords_for_client("client-inexistente")

        assert result == []

    def test_get_passwords_for_client_empty_cache(self, controller: PasswordsController) -> None:
        """Deve retornar lista vazia se cache está vazio."""
        controller._all_passwords = []

        result = controller.get_passwords_for_client("client-1")

        assert result == []

    def test_get_passwords_for_client_handles_none_client_id(
        self,
        controller: PasswordsController,
    ) -> None:
        """Deve lidar com senhas que têm client_id None."""
        passwords_with_none: list[PasswordRow] = [
            make_password_row(id="pwd-1", client_id=None, service="Test"),
            make_password_row(id="pwd-2", client_id="client-1", service="Test2"),
        ]
        controller._all_passwords = passwords_with_none

        result = controller.get_passwords_for_client("client-1")

        assert len(result) == 1
        assert result[0]["id"] == "pwd-2"


# ========================================
# Testes de load_all_passwords
# ========================================


class TestLoadAllPasswords:
    """Testes para controller.load_all_passwords()."""

    def test_load_all_passwords_success(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve carregar senhas do service e atualizar cache."""
        with patch("src.modules.passwords.controller.passwords_service.get_passwords") as mock_get:
            mock_get.return_value = sample_passwords

            result = controller.load_all_passwords("org-123")

            mock_get.assert_called_once_with("org-123", None, "Todos")
            assert result == sample_passwords
            assert controller._all_passwords == sample_passwords

    def test_load_all_passwords_empty_result(self, controller: PasswordsController) -> None:
        """Deve lidar com resultado vazio do repositório."""
        with patch("src.modules.passwords.controller.passwords_service.get_passwords") as mock_get:
            mock_get.return_value = []

            result = controller.load_all_passwords("org-vazio")

            assert result == []
            assert controller._all_passwords == []

    def test_load_all_passwords_repository_error(self, controller: PasswordsController) -> None:
        """Erro do repositório deve propagar."""
        with patch("src.modules.passwords.controller.passwords_service.get_passwords") as mock_get:
            mock_get.side_effect = Exception("Supabase offline")

            with pytest.raises(Exception, match="Supabase offline"):
                controller.load_all_passwords("org-123")


# ========================================
# Testes de filter_passwords
# ========================================


class TestFilterPasswords:
    """Testes para controller.filter_passwords()."""

    def test_filter_passwords_by_text(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve filtrar por texto de busca."""
        controller._all_passwords = sample_passwords

        result = controller.filter_passwords("alpha", None)

        # Filtra por client_name, service ou username
        assert len(result) == 2  # Alpha Corp tem 2 senhas

    def test_filter_passwords_by_service(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve filtrar por serviço específico."""
        controller._all_passwords = sample_passwords

        result = controller.filter_passwords(None, "SIFAP")

        assert len(result) == 1
        assert result[0]["service"] == "SIFAP"

    def test_filter_passwords_combined(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve aplicar filtros combinados."""
        controller._all_passwords = sample_passwords

        result = controller.filter_passwords("alpha", "GOV.BR")

        assert len(result) == 1
        assert result[0]["service"] == "GOV.BR"

    def test_filter_passwords_no_match(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve retornar vazio se nenhum filtro corresponder."""
        controller._all_passwords = sample_passwords

        result = controller.filter_passwords("xyz", "ServicoInexistente")

        assert result == []


# ========================================
# Testes de operações CRUD
# ========================================


class TestCrudOperations:
    """Testes para operações CRUD do controller."""

    def test_create_password_delegates_to_service(self, controller: PasswordsController) -> None:
        """create_password deve delegar para o service."""
        with patch("src.modules.passwords.controller.passwords_service.create_password") as mock_create:
            controller.create_password(
                org_id="org-1",
                client_id="client-1",
                client_name="Alpha",
                service="SIFAP",
                username="user",
                password="pass",
                notes="notes",
                user_id="user-1",
            )

            mock_create.assert_called_once_with(
                "org-1", "Alpha", "SIFAP", "user", "pass", "notes", "user-1", "client-1"
            )

    def test_update_password_delegates_to_service(self, controller: PasswordsController) -> None:
        """update_password deve delegar para o service."""
        with patch("src.modules.passwords.controller.passwords_service.update_password_by_id") as mock_update:
            controller.update_password(
                password_id="pwd-1",
                client_id="client-1",
                client_name="Alpha",
                service="SIFAP",
                username="user",
                password_plain="newpass",
                notes="new notes",
            )

            mock_update.assert_called_once_with(
                "pwd-1",
                client_id="client-1",
                client_name="Alpha",
                service="SIFAP",
                username="user",
                password_plain="newpass",
                notes="new notes",
            )

    def test_delete_password_delegates_to_service(self, controller: PasswordsController) -> None:
        """delete_password deve delegar para o service."""
        with patch("src.modules.passwords.controller.passwords_service.delete_password_by_id") as mock_delete:
            controller.delete_password("pwd-1")

            mock_delete.assert_called_once_with("pwd-1")

    def test_delete_all_passwords_for_client_returns_count(self, controller: PasswordsController) -> None:
        """delete_all_passwords_for_client deve retornar quantidade deletada."""
        with patch("src.modules.passwords.controller.passwords_service.delete_all_passwords_for_client") as mock_delete:
            mock_delete.return_value = 5

            result = controller.delete_all_passwords_for_client("org-1", "client-1")

            assert result == 5
            mock_delete.assert_called_once_with("org-1", "client-1")


# ========================================
# Testes de find_duplicate_passwords_by_service
# ========================================


class TestFindDuplicates:
    """Testes para controller.find_duplicate_passwords_by_service()."""

    def test_find_duplicates_returns_matches(self, controller: PasswordsController) -> None:
        """Deve retornar senhas existentes para mesma combinação."""
        expected_duplicates: list[PasswordRow] = [make_password_row(id="pwd-1", service="SIFAP")]

        with patch(
            "src.modules.passwords.controller.passwords_service.find_duplicate_password_by_service"
        ) as mock_find:
            mock_find.return_value = expected_duplicates

            result = controller.find_duplicate_passwords_by_service("org-1", "client-1", "SIFAP")

            assert result == expected_duplicates
            mock_find.assert_called_once_with(org_id="org-1", client_id="client-1", service="SIFAP")

    def test_find_duplicates_returns_empty_when_no_match(self, controller: PasswordsController) -> None:
        """Deve retornar lista vazia se não há duplicatas."""
        with patch(
            "src.modules.passwords.controller.passwords_service.find_duplicate_password_by_service"
        ) as mock_find:
            mock_find.return_value = []

            result = controller.find_duplicate_passwords_by_service("org-1", "client-1", "NovoServico")

            assert result == []


# ========================================
# Testes de group_passwords_by_client
# ========================================


class TestGroupPasswordsByClient:
    """Testes para controller.group_passwords_by_client()."""

    def test_group_passwords_uses_cache(
        self,
        controller: PasswordsController,
        sample_passwords: list[PasswordRow],
    ) -> None:
        """Deve usar o cache interno para agrupar."""
        controller._all_passwords = sample_passwords

        result = controller.group_passwords_by_client()

        # 2 clientes: client-1 e client-2
        assert len(result) == 2

    def test_group_passwords_empty_cache(self, controller: PasswordsController) -> None:
        """Deve retornar lista vazia se cache está vazio."""
        controller._all_passwords = []

        result = controller.group_passwords_by_client()

        assert result == []
