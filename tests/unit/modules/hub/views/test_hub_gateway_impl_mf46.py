# -*- coding: utf-8 -*-
"""Testes unitários para hub_gateway_impl.py (MF-46).

Meta: >=95% coverage (ideal 100%).
Estratégia: testes headless com fakes/mocks, imports dinâmicos patchados na origem.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def fake_parent():
    """Fake parent widget (HubScreen)."""
    parent = MagicMock()
    parent.refresh_notes_async = MagicMock()
    parent._hub_controller = MagicMock()
    parent._load_dashboard = MagicMock()
    return parent


@pytest.fixture
def gateway(fake_parent):
    """Instance de HubGatewayImpl."""
    from src.modules.hub.views.hub_gateway_impl import HubGatewayImpl

    return HubGatewayImpl(fake_parent)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: get_org_id
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.core.session.get_current_user")
def test_get_org_id_from_session_cache(mock_get_user, gateway):
    """Test 1.1: Obtém org_id do cache de sessão."""
    # Setup: usuário em cache com org_id
    mock_user = MagicMock()
    mock_user.org_id = "org-cached-123"
    mock_get_user.return_value = mock_user

    # Execute
    result = gateway.get_org_id()

    # Assert
    assert result == "org-cached-123"
    mock_get_user.assert_called_once()


@patch("src.infra.supabase_client.exec_postgrest")
@patch("src.infra.supabase_client.get_supabase")
@patch("src.core.session.get_current_user")
def test_get_org_id_from_supabase_owner_role(mock_get_user, mock_get_supabase, mock_exec_postgrest, gateway):
    """Test 1.2: Fallback Supabase - escolhe owner quando disponível."""
    # Setup: cache vazio
    mock_get_user.return_value = None

    # Setup: cliente Supabase com sessão
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = MagicMock()
    mock_session.user.id = "user-456"
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    # Setup: memberships com owner e não-owner
    mock_response = MagicMock()
    mock_response.data = [
        {"org_id": "org-member-1", "role": "member"},
        {"org_id": "org-owner-2", "role": "owner"},
        {"org_id": "org-member-3", "role": "member"},
    ]
    mock_exec_postgrest.return_value = mock_response

    # Execute
    result = gateway.get_org_id()

    # Assert: escolhe o owner
    assert result == "org-owner-2"
    mock_exec_postgrest.assert_called_once()


@patch("src.infra.supabase_client.exec_postgrest")
@patch("src.infra.supabase_client.get_supabase")
@patch("src.core.session.get_current_user")
def test_get_org_id_from_supabase_no_owner(mock_get_user, mock_get_supabase, mock_exec_postgrest, gateway):
    """Test 1.3: Fallback Supabase - escolhe primeiro se não há owner."""
    # Setup: cache vazio
    mock_get_user.return_value = None

    # Setup: cliente Supabase
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = MagicMock()
    mock_session.user.id = "user-789"
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    # Setup: memberships sem owner
    mock_response = MagicMock()
    mock_response.data = [
        {"org_id": "org-first", "role": "member"},
        {"org_id": "org-second", "role": "admin"},
    ]
    mock_exec_postgrest.return_value = mock_response

    # Execute
    result = gateway.get_org_id()

    # Assert: escolhe o primeiro
    assert result == "org-first"


@patch("src.infra.supabase_client.get_supabase")
@patch("src.core.session.get_current_user")
def test_get_org_id_no_session(mock_get_user, mock_get_supabase, gateway):
    """Test 1.4: Sem sessão retorna None."""
    # Setup: cache vazio, sem cliente
    mock_get_user.return_value = None
    mock_get_supabase.return_value = None

    # Execute
    result = gateway.get_org_id()

    # Assert
    assert result is None


@patch("src.infra.supabase_client.exec_postgrest")
@patch("src.infra.supabase_client.get_supabase")
@patch("src.core.session.get_current_user")
def test_get_org_id_empty_memberships(mock_get_user, mock_get_supabase, mock_exec_postgrest, gateway):
    """Test 1.5: Memberships vazio retorna None."""
    # Setup: cache vazio
    mock_get_user.return_value = None

    # Setup: cliente com sessão
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = MagicMock()
    mock_session.user.id = "user-999"
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    # Setup: response vazio
    mock_response = MagicMock()
    mock_response.data = []
    mock_exec_postgrest.return_value = mock_response

    # Execute
    result = gateway.get_org_id()

    # Assert
    assert result is None


@patch("src.core.session.get_current_user")
def test_get_org_id_exception_handling(mock_get_user, gateway):
    """Test 1.6: Exception retorna None sem explodir."""
    # Setup: get_current_user explode
    mock_get_user.side_effect = RuntimeError("Session error")

    # Execute
    result = gateway.get_org_id()

    # Assert: não explode, retorna None
    assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: get_user_email
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.infra.supabase_client.get_supabase")
def test_get_user_email_no_client(mock_get_supabase, gateway):
    """Test 2.1: Cliente None retorna None."""
    mock_get_supabase.return_value = None

    result = gateway.get_user_email()

    assert result is None


@patch("src.infra.supabase_client.get_supabase")
def test_get_user_email_no_session(mock_get_supabase, gateway):
    """Test 2.2: Sessão None retorna None."""
    mock_client = MagicMock()
    mock_client.auth.get_session.return_value = None
    mock_get_supabase.return_value = mock_client

    result = gateway.get_user_email()

    assert result is None


@patch("src.infra.supabase_client.get_supabase")
def test_get_user_email_no_user(mock_get_supabase, gateway):
    """Test 2.3: Sessão sem user retorna None."""
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = None
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    result = gateway.get_user_email()

    assert result is None


@patch("src.infra.supabase_client.get_supabase")
def test_get_user_email_success(mock_get_supabase, gateway):
    """Test 2.4: Retorna email do usuário."""
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = MagicMock()
    mock_session.user.email = "test@example.com"
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    result = gateway.get_user_email()

    assert result == "test@example.com"


@patch("src.infra.supabase_client.get_supabase")
def test_get_user_email_exception(mock_get_supabase, gateway):
    """Test 2.5: Exception retorna None."""
    mock_get_supabase.side_effect = RuntimeError("Supabase error")

    result = gateway.get_user_email()

    assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: is_authenticated
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.infra.supabase_client.get_supabase")
def test_is_authenticated_no_client(mock_get_supabase, gateway):
    """Test 3.1: Cliente None retorna False."""
    mock_get_supabase.return_value = None

    result = gateway.is_authenticated()

    assert result is False


@patch("src.infra.supabase_client.get_supabase")
def test_is_authenticated_no_user(mock_get_supabase, gateway):
    """Test 3.2: Sessão sem user retorna False."""
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = None
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    result = gateway.is_authenticated()

    assert result is False


@patch("src.infra.supabase_client.get_supabase")
def test_is_authenticated_with_user(mock_get_supabase, gateway):
    """Test 3.3: Sessão com user retorna True."""
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.user = MagicMock()
    mock_session.user.id = "user-auth-123"
    mock_session.user.email = "auth@test.com"
    mock_client.auth.get_session.return_value = mock_session
    mock_get_supabase.return_value = mock_client

    result = gateway.is_authenticated()

    assert result is True


@patch("src.infra.supabase_client.get_supabase")
def test_is_authenticated_exception(mock_get_supabase, gateway):
    """Test 3.4: Exception retorna False."""
    mock_get_supabase.side_effect = RuntimeError("Auth error")

    result = gateway.is_authenticated()

    assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: is_online
# ══════════════════════════════════════════════════════════════════════════════


def test_is_online_when_authenticated(gateway):
    """Test 4.1: is_online retorna True se autenticado."""
    with patch.object(gateway, "is_authenticated", return_value=True):
        result = gateway.is_online()
        assert result is True


def test_is_online_when_not_authenticated(gateway):
    """Test 4.2: is_online retorna False se não autenticado."""
    with patch.object(gateway, "is_authenticated", return_value=False):
        result = gateway.is_online()
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: UI Delegates (show_note_editor, confirm_delete_note, show_error, show_info)
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dialogs.show_note_editor")
def test_show_note_editor_delegates(mock_show_editor, gateway, fake_parent):
    """Test 5.1: show_note_editor delega corretamente."""
    note_data = {"id": 123, "title": "Test Note"}
    mock_show_editor.return_value = {"id": 123, "title": "Updated Note"}

    result = gateway.show_note_editor(note_data)

    mock_show_editor.assert_called_once_with(fake_parent, note_data)
    assert result == {"id": 123, "title": "Updated Note"}


@patch("src.modules.hub.views.hub_dialogs.show_note_editor")
def test_show_note_editor_none_data(mock_show_editor, gateway, fake_parent):
    """Test 5.2: show_note_editor com None (criar nova)."""
    mock_show_editor.return_value = {"title": "New Note"}

    result = gateway.show_note_editor(None)

    mock_show_editor.assert_called_once_with(fake_parent, None)
    assert result == {"title": "New Note"}


@patch("src.modules.hub.views.hub_dialogs.confirm_delete_note")
def test_confirm_delete_note_delegates(mock_confirm, gateway, fake_parent):
    """Test 5.3: confirm_delete_note delega corretamente."""
    note_data = {"id": 456, "title": "To Delete"}
    mock_confirm.return_value = True

    result = gateway.confirm_delete_note(note_data)

    mock_confirm.assert_called_once_with(fake_parent, note_data)
    assert result is True


@patch("src.modules.hub.views.hub_dialogs.confirm_delete_note")
def test_confirm_delete_note_cancelled(mock_confirm, gateway, fake_parent):
    """Test 5.4: confirm_delete_note retorna False se cancelado."""
    note_data = {"id": 789}
    mock_confirm.return_value = False

    result = gateway.confirm_delete_note(note_data)

    mock_confirm.assert_called_once_with(fake_parent, note_data)
    assert result is False


@patch("src.modules.hub.views.hub_dialogs.show_error")
def test_show_error_delegates(mock_show_error, gateway, fake_parent):
    """Test 5.5: show_error delega corretamente."""
    gateway.show_error("Error Title", "Error message")

    mock_show_error.assert_called_once_with(fake_parent, "Error Title", "Error message")


@patch("src.modules.hub.views.hub_dialogs.show_info")
def test_show_info_delegates(mock_show_info, gateway, fake_parent):
    """Test 5.6: show_info delega corretamente."""
    gateway.show_info("Info Title", "Info message")

    mock_show_info.assert_called_once_with(fake_parent, "Info Title", "Info message")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: reload_notes
# ══════════════════════════════════════════════════════════════════════════════


def test_reload_notes_via_refresh_notes_async(gateway, fake_parent):
    """Test 6.1: reload_notes usa refresh_notes_async quando disponível."""
    gateway.reload_notes()

    fake_parent.refresh_notes_async.assert_called_once_with(force=True)


def test_reload_notes_via_controller(gateway, fake_parent):
    """Test 6.2: reload_notes usa controller quando refresh_notes_async não existe."""
    # Remove método preferencial
    delattr(fake_parent, "refresh_notes_async")

    gateway.reload_notes()

    fake_parent._hub_controller.refresh_notes.assert_called_once_with(force=True)


def test_reload_notes_no_method_available(gateway, fake_parent):
    """Test 6.3: reload_notes não explode quando nenhum método disponível."""
    # Remove ambos métodos
    delattr(fake_parent, "refresh_notes_async")
    delattr(fake_parent, "_hub_controller")

    # Não deve explodir
    gateway.reload_notes()


def test_reload_notes_exception_handling(gateway, fake_parent):
    """Test 6.4: reload_notes captura exceção sem explodir."""
    fake_parent.refresh_notes_async.side_effect = RuntimeError("Refresh error")

    # Não deve explodir
    gateway.reload_notes()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: reload_dashboard
# ══════════════════════════════════════════════════════════════════════════════


def test_reload_dashboard_via_controller(gateway, fake_parent):
    """Test 7.1: reload_dashboard usa controller (método preferido)."""
    gateway.reload_dashboard()

    fake_parent._hub_controller.refresh_dashboard.assert_called_once()


def test_reload_dashboard_fallback_load_dashboard(gateway, fake_parent):
    """Test 7.2: reload_dashboard usa _load_dashboard como fallback."""
    # Remove controller
    fake_parent._hub_controller = None

    gateway.reload_dashboard()

    fake_parent._load_dashboard.assert_called_once()


def test_reload_dashboard_no_method_available(gateway, fake_parent):
    """Test 7.3: reload_dashboard não explode quando nenhum método disponível."""
    # Remove ambos métodos
    fake_parent._hub_controller = None
    delattr(fake_parent, "_load_dashboard")

    # Não deve explodir
    gateway.reload_dashboard()


def test_reload_dashboard_exception_handling(gateway, fake_parent):
    """Test 7.4: reload_dashboard captura exceção sem explodir."""
    fake_parent._hub_controller.refresh_dashboard.side_effect = RuntimeError("Dashboard error")

    # Não deve explodir
    gateway.reload_dashboard()
