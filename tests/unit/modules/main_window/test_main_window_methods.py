"""Testes unitários dos métodos públicos de App (main_window.py) - ZUI-TEST-001.

Estratégia: Testar apenas os métodos públicos sem criar a janela Tk.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.main_window.views.main_window import App


@pytest.fixture
def app_mock():
    """Cria um mock parcial de App com métodos públicos delegados."""
    app = MagicMock(spec=App)

    # Atributos necessários
    app.nav = MagicMock()
    app._actions = MagicMock()
    app._session = MagicMock()  # SessionCache agora é _session
    app._content_container = MagicMock()  # Container para telas
    app.footer = MagicMock()
    app._status_monitor = MagicMock()
    app._main_frame_ref = None
    app.after = MagicMock()
    app.auth = MagicMock()
    app.topbar = MagicMock()

    # Métodos públicos reais (vamos testar suas assinaturas)
    from src.modules.main_window.views.main_window import App as RealApp

    app.show_hub_screen = RealApp.show_hub_screen.__get__(app, type(app))
    app.show_main_screen = RealApp.show_main_screen.__get__(app, type(app))
    app.show_passwords_screen = RealApp.show_passwords_screen.__get__(app, type(app))
    app.show_cashflow_screen = RealApp.show_cashflow_screen.__get__(app, type(app))
    app.show_placeholder_screen = RealApp.show_placeholder_screen.__get__(app, type(app))
    app.novo_cliente = RealApp.novo_cliente.__get__(app, type(app))
    app.editar_cliente = RealApp.editar_cliente.__get__(app, type(app))
    app.ver_subpastas = RealApp.ver_subpastas.__get__(app, type(app))
    app.abrir_lixeira = RealApp.abrir_lixeira.__get__(app, type(app))
    app._excluir_cliente = RealApp._excluir_cliente.__get__(app, type(app))
    app.enviar_para_supabase = RealApp.enviar_para_supabase.__get__(app, type(app))
    app._get_user_cached = RealApp._get_user_cached.__get__(app, type(app))
    app._get_role_cached = RealApp._get_role_cached.__get__(app, type(app))
    app._get_org_id_cached = RealApp._get_org_id_cached.__get__(app, type(app))

    return app


# ==================== Testes: Navegação ====================


@patch("src.modules.main_window.views.main_window.navigate_to")
def test_app_show_hub_screen_chama_nav(mock_navigate, app_mock):
    """Testa que show_hub_screen delega para navigate_to."""
    app_mock.show_hub_screen()
    mock_navigate.assert_called_once_with(app_mock, "hub")


@patch("src.modules.main_window.views.main_window.navigate_to")
def test_app_show_main_screen_chama_nav(mock_navigate, app_mock):
    """Testa que show_main_screen delega para navigate_to."""
    app_mock.show_main_screen()
    mock_navigate.assert_called_once_with(app_mock, "main")


@patch("src.modules.main_window.views.main_window.navigate_to")
def test_app_show_passwords_screen_chama_nav(mock_navigate, app_mock):
    """Testa que show_passwords_screen delega para navigate_to."""
    app_mock.show_passwords_screen()
    mock_navigate.assert_called_once_with(app_mock, "passwords")


@patch("src.modules.main_window.views.main_window.navigate_to")
def test_app_show_cashflow_screen_chama_nav(mock_navigate, app_mock):
    """Testa que show_cashflow_screen delega para navigate_to."""
    app_mock.show_cashflow_screen()
    mock_navigate.assert_called_once_with(app_mock, "cashflow")


@patch("src.modules.main_window.views.main_window.navigate_to")
def test_app_show_placeholder_screen_chama_nav(mock_navigate, app_mock):
    """Testa que show_placeholder_screen delega para navigate_to."""
    app_mock.show_placeholder_screen("Test")
    mock_navigate.assert_called_once_with(app_mock, "placeholder", title="Test")


# ==================== Testes: Ações Delegadas ====================


def test_app_novo_cliente_delega_para_actions(app_mock):
    """Testa que novo_cliente delega para AppActions."""
    app_mock.novo_cliente()
    app_mock._actions.novo_cliente.assert_called_once()


def test_app_editar_cliente_delega_para_actions(app_mock):
    """Testa que editar_cliente delega para AppActions."""
    app_mock.editar_cliente()
    app_mock._actions.editar_cliente.assert_called_once()


def test_app_ver_subpastas_delega_para_actions(app_mock):
    """Testa que ver_subpastas delega para AppActions."""
    app_mock.ver_subpastas()
    app_mock._actions.ver_subpastas.assert_called_once()


def test_app_abrir_lixeira_delega_para_actions(app_mock):
    """Testa que abrir_lixeira delega para AppActions."""
    app_mock.abrir_lixeira()
    app_mock._actions.abrir_lixeira.assert_called_once()


def test_app_excluir_cliente_delega_para_actions(app_mock):
    """Testa que _excluir_cliente delega para AppActions."""
    app_mock._excluir_cliente()
    app_mock._actions._excluir_cliente.assert_called_once()


def test_app_enviar_para_supabase_delega_para_actions(app_mock):
    """Testa que enviar_para_supabase delega para AppActions."""
    app_mock.enviar_para_supabase()
    app_mock._actions.enviar_para_supabase.assert_called_once()


# ==================== Testes: SessionCache ====================


def test_app_get_user_cached_usa_session_cache(app_mock):
    """Testa que _get_user_cached usa SessionCache."""
    app_mock._session.get_user.return_value = {"id": "user123", "email": "test@test.com"}
    app_mock.auth.set_user_data = MagicMock()

    result = app_mock._get_user_cached()

    app_mock._session.get_user.assert_called_once()
    assert result == {"id": "user123", "email": "test@test.com"}


def test_app_get_role_cached_usa_session_cache(app_mock):
    """Testa que _get_role_cached usa SessionCache."""
    app_mock._session.get_role.return_value = "admin"

    result = app_mock._get_role_cached("user123")

    app_mock._session.get_role.assert_called_once_with("user123")
    assert result == "admin"


def test_app_get_org_id_cached_usa_session_cache(app_mock):
    """Testa que _get_org_id_cached usa SessionCache."""
    app_mock._session.get_org_id.return_value = "org123"

    result = app_mock._get_org_id_cached("user123")

    app_mock._session.get_org_id.assert_called_once_with("user123")
    assert result == "org123"
