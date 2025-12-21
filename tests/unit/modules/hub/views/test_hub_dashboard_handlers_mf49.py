# -*- coding: utf-8 -*-
"""Testes unitários para hub_dashboard_handlers.py (MF-49).

Meta: >=95% coverage (ideal 100%).
Estratégia: testes headless com mocks, validar delegação correta aos callbacks.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def fake_parent() -> Any:
    """Fake parent widget."""
    return MagicMock()


@pytest.fixture
def fake_dashboard_vm() -> Any:
    """Fake DashboardViewModel com state usando SimpleNamespace."""
    vm = SimpleNamespace()
    vm.state = "STATE_MOCK"
    return vm


@pytest.fixture
def fake_dashboard_actions() -> Any:
    """Fake DashboardActionController usando SimpleNamespace."""
    return SimpleNamespace()


@pytest.fixture
def fake_get_org_id() -> Any:
    """Fake get_org_id callable."""
    return MagicMock(return_value="org-123")


@pytest.fixture
def fake_get_user_id() -> Any:
    """Fake get_user_id callable."""
    return MagicMock(return_value="user-456")


@pytest.fixture
def fake_get_main_app() -> Any:
    """Fake get_main_app callable."""
    return MagicMock(return_value=MagicMock())


@pytest.fixture
def fake_on_success() -> Any:
    """Fake on_success_callback."""
    return MagicMock()


@pytest.fixture
def fake_on_client_picked() -> Any:
    """Fake on_client_picked callback."""
    return MagicMock()


@pytest.fixture
def fake_on_refresh() -> Any:
    """Fake on_refresh_callback."""
    return MagicMock()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: handle_new_task_click_v2
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_new_task_click")
def test_handle_new_task_click_v2_delegates_correctly(
    mock_handle_new_task_click,
    fake_parent,
    fake_get_org_id,
    fake_get_user_id,
    fake_on_success,
):
    """Test 1.1: handle_new_task_click_v2 delega para handle_new_task_click."""
    from src.modules.hub.views.hub_dashboard_handlers import (
        handle_new_task_click_v2,
    )

    # Execute
    handle_new_task_click_v2(
        parent=fake_parent,
        get_org_id=fake_get_org_id,
        get_user_id=fake_get_user_id,
        on_success_callback=fake_on_success,
    )

    # Assert
    mock_handle_new_task_click.assert_called_once_with(
        parent=fake_parent,
        get_org_id=fake_get_org_id,
        get_user_id=fake_get_user_id,
        on_success_callback=fake_on_success,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: handle_new_obligation_click_v2
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_new_obligation_click")
def test_handle_new_obligation_click_v2_delegates_correctly(
    mock_handle_new_obligation_click,
    fake_parent,
    fake_get_org_id,
    fake_get_user_id,
    fake_get_main_app,
    fake_on_client_picked,
):
    """Test 2.1: handle_new_obligation_click_v2 delega corretamente."""
    from src.modules.hub.views.hub_dashboard_handlers import (
        handle_new_obligation_click_v2,
    )

    # Execute
    handle_new_obligation_click_v2(
        parent=fake_parent,
        get_org_id=fake_get_org_id,
        get_user_id=fake_get_user_id,
        get_main_app=fake_get_main_app,
        on_client_picked=fake_on_client_picked,
    )

    # Assert
    mock_handle_new_obligation_click.assert_called_once_with(
        parent=fake_parent,
        get_org_id=fake_get_org_id,
        get_user_id=fake_get_user_id,
        get_main_app=fake_get_main_app,
        on_client_picked=fake_on_client_picked,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: handle_view_all_activity_click_v2
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_view_all_activity_click")
def test_handle_view_all_activity_click_v2_delegates_correctly(
    mock_handle_view_all_activity_click,
    fake_parent,
):
    """Test 3.1: handle_view_all_activity_click_v2 delega com parent."""
    from src.modules.hub.views.hub_dashboard_handlers import (
        handle_view_all_activity_click_v2,
    )

    # Execute
    handle_view_all_activity_click_v2(parent=fake_parent)

    # Assert
    mock_handle_view_all_activity_click.assert_called_once_with(parent=fake_parent)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: Card Handlers (clients, pendencias, tarefas)
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_card_click")
def test_handle_card_clients_click_delegates_correctly(
    mock_handle_card_click,
    fake_dashboard_vm,
    fake_dashboard_actions,
    fake_parent,
):
    """Test 4.1: handle_card_clients_click delega com card_type='clients'."""
    from src.modules.hub.views.hub_dashboard_handlers import handle_card_clients_click

    # Execute
    handle_card_clients_click(
        dashboard_vm=fake_dashboard_vm,
        dashboard_actions=fake_dashboard_actions,
        parent=fake_parent,
    )

    # Assert
    mock_handle_card_click.assert_called_once_with(
        card_type="clients",
        state=fake_dashboard_vm.state,
        controller=fake_dashboard_actions,
        parent=fake_parent,
    )


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_card_click")
def test_handle_card_pendencias_click_delegates_correctly(
    mock_handle_card_click,
    fake_dashboard_vm,
    fake_dashboard_actions,
    fake_parent,
):
    """Test 4.2: handle_card_pendencias_click delega com card_type='pending'."""
    from src.modules.hub.views.hub_dashboard_handlers import (
        handle_card_pendencias_click,
    )

    # Execute
    handle_card_pendencias_click(
        dashboard_vm=fake_dashboard_vm,
        dashboard_actions=fake_dashboard_actions,
        parent=fake_parent,
    )

    # Assert
    mock_handle_card_click.assert_called_once_with(
        card_type="pending",
        state=fake_dashboard_vm.state,
        controller=fake_dashboard_actions,
        parent=fake_parent,
    )


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_card_click")
def test_handle_card_tarefas_click_delegates_correctly(
    mock_handle_card_click,
    fake_dashboard_vm,
    fake_dashboard_actions,
    fake_parent,
):
    """Test 4.3: handle_card_tarefas_click delega com card_type='tasks'."""
    from src.modules.hub.views.hub_dashboard_handlers import handle_card_tarefas_click

    # Execute
    handle_card_tarefas_click(
        dashboard_vm=fake_dashboard_vm,
        dashboard_actions=fake_dashboard_actions,
        parent=fake_parent,
    )

    # Assert
    mock_handle_card_click.assert_called_once_with(
        card_type="tasks",
        state=fake_dashboard_vm.state,
        controller=fake_dashboard_actions,
        parent=fake_parent,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: handle_client_picked_for_obligation_v2
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_handlers.handle_client_picked_for_obligation")
def test_handle_client_picked_for_obligation_v2_delegates_correctly(
    mock_handle_client_picked,
    fake_parent,
    fake_get_org_id,
    fake_get_user_id,
    fake_get_main_app,
    fake_on_refresh,
):
    """Test 5.1: handle_client_picked_for_obligation_v2 delega corretamente."""
    from src.modules.hub.views.hub_dashboard_handlers import (
        handle_client_picked_for_obligation_v2,
    )

    client_data = {"id": 123, "name": "Cliente Teste"}

    # Execute
    handle_client_picked_for_obligation_v2(
        client_data=client_data,
        parent=fake_parent,
        get_org_id=fake_get_org_id,
        get_user_id=fake_get_user_id,
        get_main_app=fake_get_main_app,
        on_refresh_callback=fake_on_refresh,
    )

    # Assert
    mock_handle_client_picked.assert_called_once_with(
        client_data=client_data,
        parent=fake_parent,
        get_org_id=fake_get_org_id,
        get_user_id=fake_get_user_id,
        get_main_app=fake_get_main_app,
        on_refresh_callback=fake_on_refresh,
    )
