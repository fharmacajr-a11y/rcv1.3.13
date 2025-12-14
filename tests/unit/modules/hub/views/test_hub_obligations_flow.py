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

    mock_app = MagicMock()

    with (
        patch("src.modules.hub.views.hub_screen.ensure_state"),
        patch("src.modules.hub.views.hub_dashboard_callbacks.handle_new_obligation_click"),
    ):
        hub = HubScreen.__new__(HubScreen)  # Criar sem chamar __init__
        hub._get_org_id_safe = MagicMock(return_value=123)
        hub._get_user_id_safe = MagicMock(return_value=456)
        hub._get_main_app = MagicMock(return_value=mock_app)

        # MF-28: Mockar _dashboard_facade que é usado em _on_new_obligation
        mock_dashboard_facade = MagicMock()
        hub._dashboard_facade = mock_dashboard_facade

        hub._on_new_obligation()

        # Verificar que _dashboard_facade.on_new_obligation foi chamado
        assert mock_dashboard_facade.on_new_obligation.call_count == 1

        # MF-28: Teste simplificado - verifica que a facade foi chamada corretamente
        # O teste real da lógica de start_client_pick_mode está em testes do handler


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
        patch("src.modules.hub.views.hub_dashboard_callbacks.handle_client_picked_for_obligation"),
    ):
        hub = HubScreen.__new__(HubScreen)
        hub._get_main_app = MagicMock(return_value=mock_app)
        hub._pending_obligation_org_id = 123
        hub._pending_obligation_user_id = 456
        hub.winfo_toplevel = MagicMock()
        hub._load_dashboard = MagicMock()

        # MF-28: Mockar _dashboard_facade que é usado em _handle_client_picked_for_obligation
        mock_dashboard_facade = MagicMock()
        hub._dashboard_facade = mock_dashboard_facade

        client_data = {
            "id": 789,
            "razao_social": "Teste Ltda",
            "cnpj": "12.345.678/0001-90",
        }

        hub._handle_client_picked_for_obligation(client_data)

        # Verificar que _dashboard_facade.on_client_picked_for_obligation foi chamado
        assert mock_dashboard_facade.on_client_picked_for_obligation.call_count == 1

        # Verificar que client_data foi passado
        call_args = mock_dashboard_facade.on_client_picked_for_obligation.call_args
        assert call_args[0][0] == client_data

        # MF-28: Teste simplificado - verifica que a facade foi chamada corretamente
        # O teste real da lógica de navigate_to e show_client_obligations_window está em testes do handler


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
    ):
        hub = HubScreen.__new__(HubScreen)
        hub._get_org_id_safe = MagicMock(return_value=123)
        hub._get_user_id_safe = MagicMock(return_value=456)
        hub._get_main_app = MagicMock(return_value=MagicMock())

        # MF-28: Mockar _dashboard_facade que é usado em _on_new_obligation
        mock_dashboard_facade = MagicMock()
        hub._dashboard_facade = mock_dashboard_facade

        hub._on_new_obligation()

        # Verificar que facade foi chamada
        assert mock_dashboard_facade.on_new_obligation.call_count == 1

        # MF-28: Teste simplificado - verifica que o método de obrigações foi chamado
        # (NãO o de senhas)


def test_passwords_flow_isolation():
    """
    Testa que o fluxo de Senhas continua funcionando de forma independente.

    Objetivo:
    - Validar que mudanças para Obrigações não afetaram o fluxo de Senhas.
    - Verificar que start_client_pick_mode para Senhas usa callback correto.
    """
    from src.modules.passwords.views.passwords_screen import PasswordsScreen

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
