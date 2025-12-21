# -*- coding: utf-8 -*-
# ruff: noqa: E731
"""Testes unitários para HubDashboardFacade (MF-47).

Meta: >=95% coverage (ideal 100%).
Estratégia: testes headless com mocks, cobertura completa de delegações e branches.
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def simple_parent():
    """Parent simples sem atributos _pending_obligation_*."""
    return SimpleNamespace()


@pytest.fixture
def parent_with_attrs():
    """Parent com atributos _pending_obligation_* já existentes."""
    parent = SimpleNamespace()
    parent._pending_obligation_org_id = "old-org"
    parent._pending_obligation_user_id = "old-user"
    return parent


@pytest.fixture
def mock_dashboard_vm():
    """Mock do DashboardViewModel."""
    return MagicMock()


@pytest.fixture
def mock_dashboard_actions():
    """Mock do DashboardActionController."""
    return MagicMock()


@pytest.fixture
def mock_renderer():
    """Mock do HubDashboardRenderer."""
    return MagicMock()


@pytest.fixture
def mock_state_manager():
    """Mock do HubStateManager."""
    return MagicMock()


@pytest.fixture
def mock_on_refresh():
    """Mock do callback on_refresh."""
    return MagicMock()


def make_facade(
    parent: Any,
    get_org_id_value: str | None = "org-123",
    get_user_id_value: str | None = "user-456",
    debug_logger: Any = None,
    mock_dashboard_vm: Any = None,
    mock_dashboard_actions: Any = None,
    mock_renderer: Any = None,
    mock_state_manager: Any = None,
    mock_on_refresh: Any = None,
) -> Any:
    """Helper para criar facade com defaults (aceita None para testar edge cases)."""
    from src.modules.hub.views.hub_dashboard_facade import HubDashboardFacade

    return HubDashboardFacade(
        parent=parent,
        dashboard_vm=mock_dashboard_vm or MagicMock(),
        dashboard_actions=mock_dashboard_actions or MagicMock(),
        renderer=mock_renderer or MagicMock(),
        state_manager=mock_state_manager or MagicMock(),
        get_org_id=lambda: get_org_id_value,
        get_user_id=lambda: get_user_id_value,
        get_main_app=lambda: MagicMock(),
        on_refresh_callback=mock_on_refresh or MagicMock(),
        debug_logger=debug_logger,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Delegação para handlers (happy path)
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_task_click_v2")
def test_on_new_task_delegates_correctly(mock_handler, simple_parent):
    """Test 1.1: on_new_task delega para handle_new_task_click_v2."""
    mock_refresh = MagicMock()
    get_org_id_func = lambda: "org-abc"
    get_user_id_func = lambda: "user-xyz"

    from src.modules.hub.views.hub_dashboard_facade import HubDashboardFacade

    facade = HubDashboardFacade(
        parent=simple_parent,
        dashboard_vm=MagicMock(),
        dashboard_actions=MagicMock(),
        renderer=MagicMock(),
        state_manager=MagicMock(),
        get_org_id=get_org_id_func,
        get_user_id=get_user_id_func,
        get_main_app=lambda: MagicMock(),
        on_refresh_callback=mock_refresh,
        debug_logger=None,
    )

    facade.on_new_task()

    mock_handler.assert_called_once_with(
        parent=simple_parent,
        get_org_id=get_org_id_func,
        get_user_id=get_user_id_func,
        on_success_callback=mock_refresh,
    )


@patch("src.modules.hub.views.hub_dashboard_facade.handle_view_all_activity_click_v2")
def test_on_view_all_activity_delegates_correctly(mock_handler, simple_parent):
    """Test 1.2: on_view_all_activity delega para handle_view_all_activity_click_v2."""
    facade = make_facade(simple_parent)

    facade.on_view_all_activity()

    mock_handler.assert_called_once_with(parent=simple_parent)


@patch("src.modules.hub.views.hub_dashboard_facade.handle_card_clients_click")
def test_on_card_clients_click_delegates_correctly(mock_handler, simple_parent):
    """Test 1.3: on_card_clients_click delega corretamente."""
    mock_vm = MagicMock()
    mock_actions = MagicMock()

    facade = make_facade(simple_parent, mock_dashboard_vm=mock_vm, mock_dashboard_actions=mock_actions)

    facade.on_card_clients_click()

    mock_handler.assert_called_once_with(dashboard_vm=mock_vm, dashboard_actions=mock_actions, parent=simple_parent)


@patch("src.modules.hub.views.hub_dashboard_facade.handle_card_pendencias_click")
def test_on_card_pendencias_click_delegates_correctly(mock_handler, simple_parent):
    """Test 1.4: on_card_pendencias_click delega corretamente."""
    mock_vm = MagicMock()
    mock_actions = MagicMock()

    facade = make_facade(simple_parent, mock_dashboard_vm=mock_vm, mock_dashboard_actions=mock_actions)

    facade.on_card_pendencias_click()

    mock_handler.assert_called_once_with(dashboard_vm=mock_vm, dashboard_actions=mock_actions, parent=simple_parent)


@patch("src.modules.hub.views.hub_dashboard_facade.handle_card_tarefas_click")
def test_on_card_tarefas_click_delegates_correctly(mock_handler, simple_parent):
    """Test 1.5: on_card_tarefas_click delega corretamente."""
    mock_vm = MagicMock()
    mock_actions = MagicMock()

    facade = make_facade(simple_parent, mock_dashboard_vm=mock_vm, mock_dashboard_actions=mock_actions)

    facade.on_card_tarefas_click()

    mock_handler.assert_called_once_with(dashboard_vm=mock_vm, dashboard_actions=mock_actions, parent=simple_parent)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: on_new_obligation - armazenamento de IDs no parent
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
def test_on_new_obligation_stores_ids_when_truthy(mock_handler, simple_parent):
    """Test 2.1: on_new_obligation armazena org_id e user_id quando truthy."""
    facade = make_facade(simple_parent, get_org_id_value="org-store", get_user_id_value="user-store")

    facade.on_new_obligation()

    # Assert: IDs armazenados no parent
    assert simple_parent._pending_obligation_org_id == "org-store"
    assert simple_parent._pending_obligation_user_id == "user-store"

    # Assert: handler chamado com callback correto
    mock_handler.assert_called_once()
    call_kwargs = mock_handler.call_args[1]
    assert call_kwargs["parent"] == simple_parent
    assert call_kwargs["on_client_picked"] == facade.on_client_picked_for_obligation


@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
def test_on_new_obligation_no_store_when_org_id_none(mock_handler, simple_parent):
    """Test 2.2: on_new_obligation não armazena quando org_id=None."""
    facade = make_facade(simple_parent, get_org_id_value=None, get_user_id_value="user-ok")

    facade.on_new_obligation()

    # Assert: IDs NÃO armazenados (atributos não existem)
    assert not hasattr(simple_parent, "_pending_obligation_org_id")
    assert not hasattr(simple_parent, "_pending_obligation_user_id")

    # Assert: handler ainda é chamado
    mock_handler.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
def test_on_new_obligation_no_store_when_user_id_none(mock_handler, simple_parent):
    """Test 2.3: on_new_obligation não armazena quando user_id=None."""
    facade = make_facade(simple_parent, get_org_id_value="org-ok", get_user_id_value=None)

    facade.on_new_obligation()

    # Assert: IDs NÃO armazenados
    assert not hasattr(simple_parent, "_pending_obligation_org_id")
    assert not hasattr(simple_parent, "_pending_obligation_user_id")

    # Assert: handler ainda é chamado
    mock_handler.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
def test_on_new_obligation_no_store_when_empty_string(mock_handler, simple_parent):
    """Test 2.4: on_new_obligation não armazena quando string vazia."""
    facade = make_facade(simple_parent, get_org_id_value="", get_user_id_value="user-ok")

    facade.on_new_obligation()

    # Assert: IDs NÃO armazenados
    assert not hasattr(simple_parent, "_pending_obligation_org_id")
    assert not hasattr(simple_parent, "_pending_obligation_user_id")

    mock_handler.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: on_client_picked_for_obligation
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_facade.handle_client_picked_for_obligation_v2")
def test_on_client_picked_delegates_with_stored_ids(mock_handler, parent_with_attrs):
    """Test 3.1: on_client_picked usa IDs armazenados no parent quando existem."""
    mock_refresh = MagicMock()
    mock_main_app = MagicMock()

    from src.modules.hub.views.hub_dashboard_facade import HubDashboardFacade

    facade = HubDashboardFacade(
        parent=parent_with_attrs,
        dashboard_vm=MagicMock(),
        dashboard_actions=MagicMock(),
        renderer=MagicMock(),
        state_manager=MagicMock(),
        get_org_id=lambda: "facade-org",
        get_user_id=lambda: "facade-user",
        get_main_app=lambda: mock_main_app,
        on_refresh_callback=mock_refresh,
        debug_logger=None,
    )

    client_data = {"id": 999, "name": "Test Client"}
    facade.on_client_picked_for_obligation(client_data)

    mock_handler.assert_called_once()
    call_kwargs = mock_handler.call_args[1]

    assert call_kwargs["client_data"] == client_data
    assert call_kwargs["parent"] == parent_with_attrs
    assert call_kwargs["on_refresh_callback"] == mock_refresh

    # Validar que get_org_id/get_user_id retornam valores do parent
    get_org_id_func = call_kwargs["get_org_id"]
    get_user_id_func = call_kwargs["get_user_id"]
    assert callable(get_org_id_func)
    assert callable(get_user_id_func)
    assert get_org_id_func() == "old-org"
    assert get_user_id_func() == "old-user"


@patch("src.modules.hub.views.hub_dashboard_facade.handle_client_picked_for_obligation_v2")
def test_on_client_picked_delegates_with_no_stored_ids(mock_handler, simple_parent):
    """Test 3.2: on_client_picked retorna None quando IDs não estão no parent."""
    mock_refresh = MagicMock()

    from src.modules.hub.views.hub_dashboard_facade import HubDashboardFacade

    facade = HubDashboardFacade(
        parent=simple_parent,
        dashboard_vm=MagicMock(),
        dashboard_actions=MagicMock(),
        renderer=MagicMock(),
        state_manager=MagicMock(),
        get_org_id=lambda: "facade-org",
        get_user_id=lambda: "facade-user",
        get_main_app=lambda: MagicMock(),
        on_refresh_callback=mock_refresh,
        debug_logger=None,
    )

    client_data = {"id": 888}
    facade.on_client_picked_for_obligation(client_data)

    mock_handler.assert_called_once()
    call_kwargs = mock_handler.call_args[1]

    # Validar que get_org_id/get_user_id retornam None
    get_org_id_func = call_kwargs["get_org_id"]
    get_user_id_func = call_kwargs["get_user_id"]
    assert get_org_id_func() is None
    assert get_user_id_func() is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Debug logger
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "method_name,expected_log_substring",
    [
        ("on_new_task", "on_new_task"),
        ("on_new_obligation", "on_new_obligation"),
        ("on_view_all_activity", "on_view_all_activity"),
        ("on_card_clients_click", "on_card_clients_click"),
        ("on_card_pendencias_click", "on_card_pendencias_click"),
        ("on_card_tarefas_click", "on_card_tarefas_click"),
    ],
)
@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_task_click_v2")
@patch("src.modules.hub.views.hub_dashboard_facade.handle_new_obligation_click_v2")
@patch("src.modules.hub.views.hub_dashboard_facade.handle_view_all_activity_click_v2")
@patch("src.modules.hub.views.hub_dashboard_facade.handle_card_clients_click")
@patch("src.modules.hub.views.hub_dashboard_facade.handle_card_pendencias_click")
@patch("src.modules.hub.views.hub_dashboard_facade.handle_card_tarefas_click")
def test_debug_logger_called_for_methods(
    mock_h6,
    mock_h5,
    mock_h4,
    mock_h3,
    mock_h2,
    mock_h1,
    method_name,
    expected_log_substring,
    simple_parent,
):
    """Test 4.x: Debug logger é chamado com mensagem correta para cada método."""
    mock_logger = MagicMock()
    facade = make_facade(simple_parent, debug_logger=mock_logger)

    method = getattr(facade, method_name)
    method()

    mock_logger.assert_called_once()
    log_message = mock_logger.call_args[0][0]
    assert expected_log_substring in log_message


@patch("src.modules.hub.views.hub_dashboard_facade.handle_client_picked_for_obligation_v2")
def test_debug_logger_called_for_on_client_picked(mock_handler, simple_parent):
    """Test 4.7: Debug logger é chamado para on_client_picked_for_obligation."""
    mock_logger = MagicMock()
    facade = make_facade(simple_parent, debug_logger=mock_logger)

    facade.on_client_picked_for_obligation({"id": 1})

    mock_logger.assert_called_once()
    log_message = mock_logger.call_args[0][0]
    assert "on_client_picked_for_obligation" in log_message


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Fallback logger import (branch coverage)
# ══════════════════════════════════════════════════════════════════════════════


def test_fallback_logger_when_src_core_logger_fails():
    """Test 5.1: Fallback logger é usado quando import de src.core.logger falha."""
    import builtins

    # Salvar import original
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "src.core.logger":
            raise ImportError("Forced failure for test")
        return original_import(name, *args, **kwargs)

    # Patch e reload
    with patch("builtins.__import__", side_effect=mock_import):
        # Remove do sys.modules para forçar re-import
        if "src.modules.hub.views.hub_dashboard_facade" in sys.modules:
            del sys.modules["src.modules.hub.views.hub_dashboard_facade"]

        import src.modules.hub.views.hub_dashboard_facade as module

        importlib.reload(module)

        # Assert: get_logger existe e funciona
        assert hasattr(module, "get_logger")
        logger = module.get_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    # Reload normal para não poluir outros testes
    if "src.modules.hub.views.hub_dashboard_facade" in sys.modules:
        del sys.modules["src.modules.hub.views.hub_dashboard_facade"]
    import src.modules.hub.views.hub_dashboard_facade

    importlib.reload(src.modules.hub.views.hub_dashboard_facade)
