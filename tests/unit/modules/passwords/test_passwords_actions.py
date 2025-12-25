"""Testes unitários para src/modules/passwords/passwords_actions.py."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from src.modules.passwords.passwords_actions import (
    PasswordDialogActions,
    PasswordFormData,
    PasswordsActions,
)


class TestPasswordDialogActionsValidateForm:
    """Testes para PasswordDialogActions.validate_form()."""

    def test_retorna_erro_quando_client_id_vazio(self):
        """Deve exigir client_id."""
        data = PasswordFormData(
            client_id="",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="secret",
            notes="",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        assert any("cliente usando o botão" in e.lower() for e in errors)

    def test_retorna_erro_quando_client_name_vazio(self):
        """Deve exigir client_name não vazio."""
        data = PasswordFormData(
            client_id="123",
            client_name="   ",
            service="email",
            username="user@example.com",
            password="secret",
            notes="",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        assert any("cliente está vazio" in e.lower() for e in errors)

    def test_retorna_erro_quando_service_vazio(self):
        """Deve exigir service não vazio."""
        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="  ",
            username="user@example.com",
            password="secret",
            notes="",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        assert any("serviço" in e.lower() for e in errors)

    def test_retorna_erro_quando_username_vazio(self):
        """Deve exigir username não vazio."""
        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="",
            password="secret",
            notes="",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        assert any("usuário" in e.lower() or "login" in e.lower() for e in errors)

    def test_retorna_erro_quando_password_vazia_em_criacao(self):
        """Deve exigir password em modo criação (is_editing=False)."""
        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="",
            notes="",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        assert any("senha" in e.lower() for e in errors)

    def test_nao_exige_password_quando_is_editing_true(self):
        """Quando is_editing=True, password vazia NÃO deve gerar erro."""
        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="",
            notes="",
            is_editing=True,
        )
        errors = PasswordDialogActions.validate_form(data)
        # Não deve haver erro relacionado à senha
        assert not any("senha" in e.lower() for e in errors)

    def test_retorna_lista_vazia_quando_todos_campos_validos(self):
        """Deve retornar lista vazia quando tudo está OK."""
        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="secret",
            notes="nota qualquer",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        assert len(errors) == 0

    def test_retorna_multiplos_erros_quando_varios_campos_vazios(self):
        """Deve retornar múltiplos erros quando há vários problemas."""
        data = PasswordFormData(
            client_id="",
            client_name="",
            service="",
            username="",
            password="",
            notes="",
            is_editing=False,
        )
        errors = PasswordDialogActions.validate_form(data)
        # Deve haver pelo menos 4 erros (client_id, client_name, service, username, password)
        assert len(errors) >= 4


class TestPasswordDialogActionsUpdatePassword:
    """Testes para PasswordDialogActions.update_password()."""

    def test_levanta_valueerror_quando_password_id_falta(self):
        """Deve levantar ValueError se password_id for None ou vazio."""
        mock_controller = Mock()
        actions = PasswordDialogActions(controller=mock_controller)

        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="newsecret",
            notes="",
            is_editing=True,
            password_id=None,
        )

        with pytest.raises(ValueError, match="ID da senha não informado"):
            actions.update_password(data)

    def test_chama_controller_update_password_com_password_id_valido(self):
        """Deve chamar controller.update_password quando password_id é válido."""
        mock_controller = Mock()
        actions = PasswordDialogActions(controller=mock_controller)

        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="newsecret",
            notes="updated notes",
            is_editing=True,
            password_id="pwd-abc-123",
        )

        actions.update_password(data)

        mock_controller.update_password.assert_called_once_with(
            "pwd-abc-123",
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password_plain="newsecret",
            notes="updated notes",
        )


class TestPasswordsActionsBuildSummaries:
    """Testes para PasswordsActions.build_summaries()."""

    def test_filtered_summaries_com_search_text(self):
        """filtered_summaries deve respeitar search_text."""
        mock_controller = Mock()
        actions = PasswordsActions(controller=mock_controller)

        all_passwords = [
            {
                "client_id": "1",
                "client_name": "Alpha Corp",
                "service": "email",
                "username": "user@alpha.com",
                "razao_social": "Alpha Corp",
            },
            {
                "client_id": "2",
                "client_name": "Beta Inc",
                "service": "ftp",
                "username": "admin@beta.com",
                "razao_social": "Beta Inc",
            },
        ]

        result = actions.build_summaries(all_passwords, search_text="alpha", service_filter=None)

        # filtered_summaries deve conter apenas Alpha Corp
        assert len(result.filtered_summaries) == 1
        assert result.filtered_summaries[0].razao_social == "Alpha Corp"

        # all_summaries deve conter ambos
        assert len(result.all_summaries) == 2

    def test_filtered_summaries_com_service_filter(self):
        """filtered_summaries deve respeitar service_filter."""
        mock_controller = Mock()
        actions = PasswordsActions(controller=mock_controller)

        all_passwords = [
            {
                "client_id": "1",
                "client_name": "Client A",
                "service": "email",
                "username": "u1",
                "razao_social": "Client A",
            },
            {
                "client_id": "1",
                "client_name": "Client A",
                "service": "ftp",
                "username": "u2",
                "razao_social": "Client A",
            },
            {
                "client_id": "2",
                "client_name": "Client B",
                "service": "email",
                "username": "u3",
                "razao_social": "Client B",
            },
        ]

        result = actions.build_summaries(all_passwords, search_text=None, service_filter="email")

        # filtered_summaries deve conter clientes que têm email (após filtro)
        assert len(result.filtered_summaries) == 2
        assert all("email" in s.services for s in result.filtered_summaries)

    def test_summaries_by_id_contem_todos_clientes(self):
        """summaries_by_id deve conter todos os clientes de all_summaries."""
        mock_controller = Mock()
        actions = PasswordsActions(controller=mock_controller)

        all_passwords = [
            {"client_id": "10", "client_name": "A", "service": "s1", "username": "u1", "razao_social": "A"},
            {"client_id": "20", "client_name": "B", "service": "s2", "username": "u2", "razao_social": "B"},
        ]

        result = actions.build_summaries(all_passwords, search_text=None, service_filter=None)

        assert "10" in result.summaries_by_id
        assert "20" in result.summaries_by_id
        assert result.summaries_by_id["10"].razao_social == "A"
        assert result.summaries_by_id["20"].razao_social == "B"

    def test_combina_search_text_e_service_filter(self):
        """Deve combinar ambos os filtros."""
        mock_controller = Mock()
        actions = PasswordsActions(controller=mock_controller)

        all_passwords = [
            {
                "client_id": "1",
                "client_name": "Alpha Corp",
                "service": "email",
                "username": "u1",
                "razao_social": "Alpha Corp",
            },
            {
                "client_id": "2",
                "client_name": "Alpha LLC",
                "service": "ftp",
                "username": "u2",
                "razao_social": "Alpha LLC",
            },
        ]

        result = actions.build_summaries(all_passwords, search_text="alpha", service_filter="email")

        # Apenas Alpha Corp (email) deve passar
        assert len(result.filtered_summaries) == 1
        assert result.filtered_summaries[0].razao_social == "Alpha Corp"


class TestPasswordDialogActionsIntegration:
    """Testes de integração leve com controller mockado."""

    def test_find_duplicates_delega_ao_controller(self):
        """find_duplicates deve chamar controller.find_duplicate_passwords_by_service."""
        mock_controller = Mock()
        mock_controller.find_duplicate_passwords_by_service.return_value = [
            {"id": "pwd1", "service": "email", "username": "user@example.com"}
        ]

        actions = PasswordDialogActions(controller=mock_controller)
        result = actions.find_duplicates("org123", "client456", "email")

        mock_controller.find_duplicate_passwords_by_service.assert_called_once_with("org123", "client456", "email")
        assert len(result) == 1

    def test_create_password_delega_ao_controller(self):
        """create_password deve chamar controller.create_password."""
        mock_controller = Mock()
        actions = PasswordDialogActions(controller=mock_controller)

        data = PasswordFormData(
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="secret",
            notes="test note",
            is_editing=False,
        )

        actions.create_password("org123", "user789", data)

        mock_controller.create_password.assert_called_once_with(
            "org123",
            client_id="123",
            client_name="Cliente A",
            service="email",
            username="user@example.com",
            password="secret",
            notes="test note",
            user_id="user789",
        )
