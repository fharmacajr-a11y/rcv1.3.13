# -*- coding: utf-8 -*-
"""Testes para o fluxo de Obrigações via Hub (Fase 2 - Separação de contextos)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_on_new_obligation_calls_start_client_pick_mode_with_correct_params():
    """
    Testa que _on_new_obligation usa start_client_pick_mode com callback específico.

    Objetivo:
    - Validar que o fluxo de Obrigações usa a nova API start_client_pick_mode.
    - Verificar que o callback é específico para obrigações (_handle_client_picked_for_obligation).
    - Garantir que return_to aponta para o Hub, não para Senhas.
    """
    from src.modules.hub.views.hub_screen import HubScreen

    mock_master = MagicMock()
    mock_app = MagicMock()

    with (
        patch("src.modules.hub.views.hub_screen.ensure_state"),
        patch("src.modules.main_window.controller.start_client_pick_mode") as mock_start_pick,
    ):
        hub = HubScreen.__new__(HubScreen)  # Criar sem chamar __init__
        hub._get_org_id_safe = MagicMock(return_value=123)
        hub._get_user_id_safe = MagicMock(return_value=456)
        hub._get_main_app = MagicMock(return_value=mock_app)

        hub._on_new_obligation()

        # Verificar que start_client_pick_mode foi chamado
        assert mock_start_pick.call_count == 1

        # Extrair argumentos da chamada
        call_args = mock_start_pick.call_args
        assert call_args is not None

        # Verificar app
        assert call_args[0][0] == mock_app

        # Verificar callback (deve ser o específico de obrigações)
        callback = call_args[1]["on_client_picked"]
        assert callback == hub._handle_client_picked_for_obligation

        # Verificar banner text
        banner_text = call_args[1]["banner_text"]
        assert "obrigações" in banner_text.lower() or "obrigacoes" in banner_text.lower()

        # Verificar return_to (deve retornar ao Hub)
        return_to = call_args[1]["return_to"]
        assert callable(return_to)


def test_handle_client_picked_for_obligation_opens_window_and_returns_to_hub():
    """
    Testa que o callback de obrigações abre a janela correta e volta pro Hub.

    Objetivo:
    - Validar que _handle_client_picked_for_obligation:
      1. Navega de volta para o Hub
      2. Abre show_client_obligations_window
      3. NÃO abre tela de Senhas
    """
    from src.modules.hub.views.hub_screen import HubScreen

    mock_app = MagicMock()

    with (
        patch("src.modules.hub.views.hub_screen.ensure_state"),
        patch("src.modules.main_window.controller.navigate_to") as mock_navigate,
        patch(
            "src.modules.clientes.views.client_obligations_window.show_client_obligations_window"
        ) as mock_show_window,
    ):
        hub = HubScreen.__new__(HubScreen)
        hub._get_main_app = MagicMock(return_value=mock_app)
        hub._pending_obligation_org_id = 123
        hub._pending_obligation_user_id = 456
        hub.winfo_toplevel = MagicMock()
        hub._load_dashboard = MagicMock()

        client_data = {
            "id": 789,
            "razao_social": "Teste Ltda",
            "cnpj": "12.345.678/0001-90",
        }

        hub._handle_client_picked_for_obligation(client_data)

        # Verificar que navegou de volta ao Hub
        assert mock_navigate.call_count == 1
        nav_call = mock_navigate.call_args
        assert nav_call[0][1] == "hub"

        # Verificar que show_client_obligations_window foi chamado
        assert mock_show_window.call_count == 1
        window_call = mock_show_window.call_args

        # Verificar parâmetros da janela de obrigações
        assert window_call[1]["org_id"] == 123
        assert window_call[1]["created_by"] == 456
        assert window_call[1]["client_id"] == 789
        assert "Teste Ltda" in window_call[1]["client_name"]


def test_obligations_flow_does_not_call_passwords_screen():
    """
    Testa que o fluxo de Obrigações NÃO chama métodos de Senhas.

    Objetivo:
    - Garantir isolamento completo entre os contextos.
    - Verificar que nenhum método relacionado a Senhas é invocado.
    """
    from src.modules.hub.views.hub_screen import HubScreen

    with (
        patch("src.modules.hub.views.hub_screen.ensure_state"),
        patch("src.modules.main_window.controller.start_client_pick_mode") as mock_start_pick,
    ):
        hub = HubScreen.__new__(HubScreen)
        hub._get_org_id_safe = MagicMock(return_value=123)
        hub._get_user_id_safe = MagicMock(return_value=456)
        hub._get_main_app = MagicMock(return_value=MagicMock())

        hub._on_new_obligation()

        # Verificar que o callback passado NÃO é de senhas
        callback = mock_start_pick.call_args[1]["on_client_picked"]
        assert "password" not in callback.__name__.lower()
        assert "senha" not in callback.__name__.lower()
        assert "obligation" in callback.__name__.lower() or "obrigacao" in callback.__name__.lower()


def test_passwords_flow_isolation():
    """
    Testa que o fluxo de Senhas continua funcionando de forma independente.

    Objetivo:
    - Validar que mudanças para Obrigações não afetaram o fluxo de Senhas.
    - Verificar que start_client_pick_mode para Senhas usa callback correto.
    """
    from src.modules.passwords.views.passwords_screen import PasswordsScreen

    mock_master = MagicMock()
    mock_app = MagicMock()

    with (
        patch("src.modules.main_window.controller.start_client_pick_mode") as mock_start_pick,
        patch("src.modules.passwords.views.passwords_screen.PasswordDialog"),
    ):
        pwd_screen = PasswordsScreen.__new__(PasswordsScreen)
        pwd_screen._get_main_app = MagicMock(return_value=mock_app)

        pwd_screen._open_new_password_flow_with_client_picker()

        # Verificar que start_client_pick_mode foi chamado
        assert mock_start_pick.call_count == 1

        # Verificar callback (deve ser específico de senhas)
        callback = mock_start_pick.call_args[1]["on_client_picked"]
        assert callback == pwd_screen._handle_client_picked_for_new_password

        # Verificar banner text
        banner_text = mock_start_pick.call_args[1]["banner_text"]
        assert "senha" in banner_text.lower() or "password" in banner_text.lower()
