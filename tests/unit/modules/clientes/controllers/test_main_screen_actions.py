# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false, reportUnknownVariableType=false, reportMissingParameterType=false

"""Testes para MainScreenActions controller.

Valida a extração da lógica de botões principais para um controller dedicado
e o retorno estruturado via ActionResult.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.modules.clientes.controllers.main_screen_actions import ActionResult, MainScreenActions
from src.modules.clientes.viewmodel import ClientesViewModel


@pytest.fixture
def mock_view():
    """Cria mock da View com interface necessária."""
    view = Mock()
    view.carregar = Mock()
    view._update_main_buttons_state = Mock()
    return view


@pytest.fixture
def mock_vm():
    """Cria mock do ViewModel."""
    vm = Mock(spec=ClientesViewModel)
    return vm


@pytest.fixture
def mock_batch_coordinator():
    """Cria mock do BatchOperationsCoordinator."""
    return Mock()


@pytest.fixture
def mock_selection_manager():
    """Cria mock do SelectionManager."""
    return Mock()


@pytest.fixture
def actions_controller(mock_vm, mock_batch_coordinator, mock_selection_manager, mock_view):
    """Cria instância do MainScreenActions para testes."""
    return MainScreenActions(
        vm=mock_vm,
        batch=mock_batch_coordinator,
        selection=mock_selection_manager,
        view=mock_view,
    )


def test_handle_new_calls_callback(actions_controller):
    """handle_new deve chamar o callback on_new_callback se registrado e retornar ok."""
    callback = Mock()
    actions_controller.on_new_callback = callback

    result = actions_controller.handle_new()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_new_without_callback(actions_controller):
    """handle_new deve retornar no_callback se callback não estiver registrado."""
    actions_controller.on_new_callback = None

    result = actions_controller.handle_new()

    assert isinstance(result, ActionResult)
    assert result.kind == "no_callback"
    assert "não configurado" in result.message.lower() if result.message else False


def test_handle_edit_calls_callback(actions_controller):
    """handle_edit deve chamar o callback on_edit_callback se registrado e retornar ok."""
    callback = Mock()
    actions_controller.on_edit_callback = callback

    result = actions_controller.handle_edit()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_edit_without_callback(actions_controller):
    """handle_edit deve retornar no_callback se callback não estiver registrado."""
    actions_controller.on_edit_callback = None

    result = actions_controller.handle_edit()

    assert isinstance(result, ActionResult)
    assert result.kind == "no_callback"


def test_handle_open_trash_calls_callback(actions_controller):
    """handle_open_trash deve chamar o callback on_open_lixeira_callback se registrado."""
    callback = Mock()
    actions_controller.on_open_lixeira_callback = callback

    result = actions_controller.handle_open_trash()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_open_subfolders_calls_callback(actions_controller):
    """handle_open_subfolders deve chamar o callback on_open_subpastas_callback se registrado."""
    callback = Mock()
    actions_controller.on_open_subpastas_callback = callback

    result = actions_controller.handle_open_subfolders()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_send_supabase_calls_callback(actions_controller):
    """handle_send_supabase deve chamar o callback on_upload_callback se registrado."""
    callback = Mock()
    actions_controller.on_upload_callback = callback

    result = actions_controller.handle_send_supabase()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_send_folder_calls_callback(actions_controller):
    """handle_send_folder deve chamar o callback on_upload_folder_callback se registrado."""
    callback = Mock()
    actions_controller.on_upload_folder_callback = callback

    result = actions_controller.handle_send_folder()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_obrigacoes_calls_callback(actions_controller):
    """handle_obrigacoes deve chamar o callback on_obrigacoes_callback se registrado."""
    callback = Mock()
    actions_controller.on_obrigacoes_callback = callback

    result = actions_controller.handle_obrigacoes()

    callback.assert_called_once()
    assert isinstance(result, ActionResult)
    assert result.kind == "ok"


def test_handle_new_propagates_exceptions(actions_controller):
    """handle_new deve retornar ActionResult com kind=error se callback lançar exceção."""
    callback = Mock(side_effect=ValueError("Test error"))
    actions_controller.on_new_callback = callback

    result = actions_controller.handle_new()

    assert isinstance(result, ActionResult)
    assert result.kind == "error"
    assert "Test error" in result.message if result.message else False


def test_handle_edit_propagates_exceptions(actions_controller):
    """handle_edit deve retornar ActionResult com kind=error se callback lançar exceção."""
    callback = Mock(side_effect=RuntimeError("Edit error"))
    actions_controller.on_edit_callback = callback

    result = actions_controller.handle_edit()

    assert isinstance(result, ActionResult)
    assert result.kind == "error"
    assert "Edit error" in result.message if result.message else False


def test_actions_controller_has_required_attributes(actions_controller):
    """Controller deve ter todos os atributos necessários."""
    assert hasattr(actions_controller, "vm")
    assert hasattr(actions_controller, "batch")
    assert hasattr(actions_controller, "selection")
    assert hasattr(actions_controller, "view")
    assert hasattr(actions_controller, "on_new_callback")
    assert hasattr(actions_controller, "on_edit_callback")
    assert hasattr(actions_controller, "on_open_subpastas_callback")
    assert hasattr(actions_controller, "on_upload_callback")
    assert hasattr(actions_controller, "on_upload_folder_callback")
    assert hasattr(actions_controller, "on_open_lixeira_callback")
    assert hasattr(actions_controller, "on_obrigacoes_callback")


# MS-26: Testes específicos de ActionResult


def test_action_result_immutable():
    """ActionResult deve ser imutável (frozen dataclass)."""
    result = ActionResult(kind="ok")

    with pytest.raises(Exception):  # FrozenInstanceError
        result.kind = "error"  # type: ignore


def test_action_result_ok():
    """ActionResult com kind='ok' deve ter estrutura correta."""
    result = ActionResult(kind="ok")

    assert result.kind == "ok"
    assert result.message is None
    assert result.payload is None


def test_action_result_with_message():
    """ActionResult deve aceitar mensagem customizada."""
    result = ActionResult(kind="error", message="Teste de erro")

    assert result.kind == "error"
    assert result.message == "Teste de erro"


def test_action_result_with_payload():
    """ActionResult deve aceitar payload com dados adicionais."""
    payload = {"cliente_id": 123, "action": "edit"}
    result = ActionResult(kind="ok", payload=payload)

    assert result.kind == "ok"
    assert result.payload == payload
    assert result.payload["cliente_id"] == 123  # type: ignore


def test_handle_open_trash_without_callback():
    """handle_open_trash deve retornar no_callback se não configurado."""
    from unittest.mock import Mock

    controller = MainScreenActions(
        vm=Mock(),
        batch=Mock(),
        selection=Mock(),
        view=Mock(),
        on_open_lixeira_callback=None,
    )

    result = controller.handle_open_trash()

    assert isinstance(result, ActionResult)
    assert result.kind == "no_callback"


def test_handle_send_supabase_error():
    """handle_send_supabase deve retornar error se callback falhar."""
    from unittest.mock import Mock

    controller = MainScreenActions(
        vm=Mock(),
        batch=Mock(),
        selection=Mock(),
        view=Mock(),
        on_upload_callback=Mock(side_effect=Exception("Network error")),
    )

    result = controller.handle_send_supabase()

    assert isinstance(result, ActionResult)
    assert result.kind == "error"
    assert "Network error" in result.message if result.message else False
