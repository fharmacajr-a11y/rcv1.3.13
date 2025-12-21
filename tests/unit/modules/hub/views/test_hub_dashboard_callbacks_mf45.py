# -*- coding: utf-8 -*-
# ruff: noqa: E731
"""Testes unitários para hub_dashboard_callbacks.py (MF-45).

Meta: >=95% coverage (ideal 100%).
Estratégia: testes headless com fakes/mocks, sem Tkinter real.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES & HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def make_getter(value):
    """Helper para criar getters sem lambda (E731)."""

    def _getter():
        return value

    return _getter


@pytest.fixture
def fake_parent():
    """Fake parent widget."""
    parent = MagicMock()
    parent.winfo_toplevel.return_value = parent
    return parent


@pytest.fixture
def fake_state():
    """Fake DashboardViewState."""
    return MagicMock()


@pytest.fixture
def fake_controller():
    """Fake dashboard actions controller."""
    controller = MagicMock()
    controller.handle_clients_card_click = MagicMock()
    controller.handle_pending_card_click = MagicMock()
    controller.handle_tasks_today_card_click = MagicMock()
    return controller


@pytest.fixture
def fake_main_app():
    """Fake main app."""
    return MagicMock()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: handle_new_task_click
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.tasks.views.NovaTarefaDialog")
@patch("data.supabase_repo.list_clients_for_picker")
def test_handle_new_task_click_success_happy_path(
    mock_list_clients,
    mock_dialog_class,
    mock_messagebox,
    fake_parent,
):
    """Test 1.1: Caminho feliz - abre diálogo com sucesso."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_task_click

    # Setup
    mock_list_clients.return_value = [{"id": 1, "name": "Client A"}]
    mock_dialog = MagicMock()
    mock_dialog_class.return_value = mock_dialog
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    on_success = MagicMock()

    # Execute
    handle_new_task_click(fake_parent, get_org_id, get_user_id, on_success)

    # Assert
    mock_list_clients.assert_called_once_with("org-123", limit=500)
    mock_dialog_class.assert_called_once_with(
        parent=fake_parent,
        org_id="org-123",
        user_id="user-456",
        on_success=on_success,
        clients=[{"id": 1, "name": "Client A"}],
    )
    mock_dialog.deiconify.assert_called_once()
    mock_messagebox.showwarning.assert_not_called()
    mock_messagebox.showerror.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_new_task_click_no_org_id(mock_messagebox, fake_parent):
    """Test 1.2: Guard - sem org_id mostra warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_task_click

    get_org_id = make_getter(None)
    get_user_id = make_getter("user-456")
    on_success = MagicMock()

    handle_new_task_click(fake_parent, get_org_id, get_user_id, on_success)

    mock_messagebox.showwarning.assert_called_once_with(
        "Autenticação Necessária",
        "Por favor, faça login para criar tarefas.",
        parent=fake_parent,
    )


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_new_task_click_no_user_id(mock_messagebox, fake_parent):
    """Test 1.3: Guard - sem user_id mostra warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_task_click

    get_org_id = make_getter("org-123")
    get_user_id = make_getter(None)
    on_success = MagicMock()

    handle_new_task_click(fake_parent, get_org_id, get_user_id, on_success)

    mock_messagebox.showwarning.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("data.supabase_repo.list_clients_for_picker")
def test_handle_new_task_click_clients_load_fails(
    mock_list_clients,
    mock_messagebox,
    fake_parent,
):
    """Test 1.4: Falha ao carregar clientes - continua com lista vazia."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_task_click

    # Setup
    mock_list_clients.side_effect = RuntimeError("DB error")
    with patch("src.modules.tasks.views.NovaTarefaDialog") as mock_dialog_class:
        mock_dialog = MagicMock()
        mock_dialog_class.return_value = mock_dialog

        get_org_id = make_getter("org-123")
        get_user_id = make_getter("user-456")
        on_success = MagicMock()

        # Execute
        handle_new_task_click(fake_parent, get_org_id, get_user_id, on_success)

        # Assert - diálogo aberto com lista vazia
        mock_dialog_class.assert_called_once()
        call_kwargs = mock_dialog_class.call_args[1]
        assert call_kwargs["clients"] == []
        mock_dialog.deiconify.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.tasks.views.NovaTarefaDialog")
def test_handle_new_task_click_dialog_creation_fails(
    mock_dialog_class,
    mock_messagebox,
    fake_parent,
):
    """Test 1.5: Exceção ao criar diálogo - mostra erro."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_task_click

    mock_dialog_class.side_effect = RuntimeError("Dialog error")
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    on_success = MagicMock()

    handle_new_task_click(fake_parent, get_org_id, get_user_id, on_success)

    mock_messagebox.showerror.assert_called_once()
    call_args = mock_messagebox.showerror.call_args[0]
    assert call_args[0] == "Erro"
    assert "Dialog error" in call_args[1]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: handle_new_obligation_click
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.main_window.controller.start_client_pick_mode")
def test_handle_new_obligation_click_success_happy_path(
    mock_start_pick_mode,
    mock_messagebox,
    fake_parent,
    fake_main_app,
):
    """Test 2.1: Caminho feliz - inicia modo seleção."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_obligation_click

    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_client_picked = MagicMock()

    handle_new_obligation_click(
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_client_picked,
    )

    mock_start_pick_mode.assert_called_once()
    call_kwargs = mock_start_pick_mode.call_args[1]
    assert call_kwargs["on_client_picked"] == on_client_picked
    assert "obrigações" in call_kwargs["banner_text"]
    mock_messagebox.showwarning.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_new_obligation_click_no_org_id(mock_messagebox, fake_parent, fake_main_app):
    """Test 2.2: Guard - sem org_id mostra warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_obligation_click

    get_org_id = make_getter(None)
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_client_picked = MagicMock()

    handle_new_obligation_click(
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_client_picked,
    )

    mock_messagebox.showwarning.assert_called_once_with(
        "Autenticação Necessária",
        "Por favor, faça login para criar obrigações.",
        parent=fake_parent,
    )


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_new_obligation_click_no_user_id(mock_messagebox, fake_parent, fake_main_app):
    """Test 2.3: Guard - sem user_id mostra warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_obligation_click

    get_org_id = make_getter("org-123")
    get_user_id = make_getter(None)
    get_main_app = make_getter(fake_main_app)
    on_client_picked = MagicMock()

    handle_new_obligation_click(
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_client_picked,
    )

    mock_messagebox.showwarning.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_new_obligation_click_no_main_app(mock_messagebox, fake_parent):
    """Test 2.4: Guard - sem main_app mostra warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_obligation_click

    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(None)
    on_client_picked = MagicMock()

    handle_new_obligation_click(
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_client_picked,
    )

    mock_messagebox.showwarning.assert_called_once_with(
        "Erro",
        "Aplicação principal não encontrada.",
        parent=fake_parent,
    )


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.main_window.controller.start_client_pick_mode")
def test_handle_new_obligation_click_exception(
    mock_start_pick_mode,
    mock_messagebox,
    fake_parent,
    fake_main_app,
):
    """Test 2.5: Exceção ao iniciar modo - mostra erro."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_new_obligation_click

    mock_start_pick_mode.side_effect = RuntimeError("Pick mode error")
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_client_picked = MagicMock()

    handle_new_obligation_click(
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_client_picked,
    )

    mock_messagebox.showerror.assert_called_once()
    call_args = mock_messagebox.showerror.call_args[0]
    assert call_args[0] == "Erro"
    assert "Pick mode error" in call_args[1]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: handle_view_all_activity_click
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_view_all_activity_click_success(mock_messagebox, fake_parent):
    """Test 3.1: Caminho feliz - mostra mensagem de desenvolvimento."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_view_all_activity_click

    handle_view_all_activity_click(fake_parent)

    mock_messagebox.showinfo.assert_called_once()
    assert "Em Desenvolvimento" in mock_messagebox.showinfo.call_args[0][0]


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_view_all_activity_click_exception(mock_messagebox, fake_parent):
    """Test 3.2: Exceção ao mostrar info - mostra erro."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_view_all_activity_click

    mock_messagebox.showinfo.side_effect = RuntimeError("Messagebox error")

    handle_view_all_activity_click(fake_parent)

    mock_messagebox.showerror.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: handle_client_picked_for_obligation
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
@patch("src.modules.main_window.controller.navigate_to")
def test_handle_client_picked_for_obligation_success_happy_path(
    mock_navigate_to,
    mock_show_obligations,
    mock_messagebox,
    fake_parent,
    fake_main_app,
):
    """Test 4.1: Caminho feliz - abre janela de obrigações."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {
        "id": 42,
        "razao_social": "Empresa XYZ",
    }
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_navigate_to.assert_called_once_with(fake_main_app, "hub")
    mock_show_obligations.assert_called_once_with(
        parent=fake_parent,
        org_id="org-123",
        created_by="user-456",
        client_id=42,
        client_name="Empresa XYZ",
        on_refresh_hub=on_refresh,
    )
    mock_messagebox.showerror.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
@patch("src.modules.main_window.controller.navigate_to")
def test_handle_client_picked_for_obligation_client_id_as_string(
    mock_navigate_to,
    mock_show_obligations,
    mock_messagebox,
    fake_parent,
    fake_main_app,
):
    """Test 4.2: client_id como string - converte para int."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {
        "id": "99",
        "nome": "Cliente ABC",
    }
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_show_obligations.assert_called_once()
    call_kwargs = mock_show_obligations.call_args[1]
    assert call_kwargs["client_id"] == 99
    assert call_kwargs["client_name"] == "Cliente ABC"


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
@patch("src.modules.main_window.controller.navigate_to")
def test_handle_client_picked_for_obligation_fallback_client_name(
    mock_navigate_to,
    mock_show_obligations,
    mock_messagebox,
    fake_parent,
    fake_main_app,
):
    """Test 4.3: Sem razao_social nem nome - usa fallback."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {"id": 77}
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_show_obligations.assert_called_once()
    call_kwargs = mock_show_obligations.call_args[1]
    assert call_kwargs["client_name"] == "Cliente 77"


@patch("src.modules.hub.views.hub_dashboard_callbacks.logger")
def test_handle_client_picked_for_obligation_no_org_id(mock_logger, fake_parent, fake_main_app):
    """Test 4.4: Guard - sem org_id loga warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {"id": 42}
    get_org_id = make_getter(None)
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_logger.warning.assert_called_once()
    assert "org_id ou user_id não disponível" in str(mock_logger.warning.call_args)


@patch("src.modules.hub.views.hub_dashboard_callbacks.logger")
def test_handle_client_picked_for_obligation_no_user_id(mock_logger, fake_parent, fake_main_app):
    """Test 4.5: Guard - sem user_id loga warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {"id": 42}
    get_org_id = make_getter("org-123")
    get_user_id = make_getter(None)
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_logger.warning.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_callbacks.logger")
def test_handle_client_picked_for_obligation_no_client_id(mock_logger, fake_parent, fake_main_app):
    """Test 4.6: Guard - sem client_id loga warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {}
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_logger.warning.assert_called_once()
    assert "Client data sem ID" in str(mock_logger.warning.call_args)


@patch("src.modules.hub.views.hub_dashboard_callbacks.logger")
def test_handle_client_picked_for_obligation_invalid_client_id(
    mock_logger,
    fake_parent,
    fake_main_app,
):
    """Test 4.7: client_id inválido (não conversível) - loga erro."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {"id": "invalid"}
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_logger.error.assert_called_once()
    assert "Não foi possível converter client_id" in str(mock_logger.error.call_args)


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
@patch("src.modules.main_window.controller.navigate_to")
def test_handle_client_picked_for_obligation_no_main_app(
    mock_navigate_to,
    mock_show_obligations,
    mock_messagebox,
    fake_parent,
):
    """Test 4.8: Sem main_app - ainda abre obrigações (navigate_to não chamado)."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    client_data = {"id": 42, "razao_social": "Empresa"}
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(None)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_navigate_to.assert_not_called()
    mock_show_obligations.assert_called_once()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
@patch("src.modules.clientes.views.client_obligations_window.show_client_obligations_window")
def test_handle_client_picked_for_obligation_exception(
    mock_show_obligations,
    mock_messagebox,
    fake_parent,
    fake_main_app,
):
    """Test 4.9: Exceção ao abrir obrigações - mostra erro."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_client_picked_for_obligation

    mock_show_obligations.side_effect = RuntimeError("Window error")
    client_data = {"id": 42}
    get_org_id = make_getter("org-123")
    get_user_id = make_getter("user-456")
    get_main_app = make_getter(fake_main_app)
    on_refresh = MagicMock()

    handle_client_picked_for_obligation(
        client_data,
        fake_parent,
        get_org_id,
        get_user_id,
        get_main_app,
        on_refresh,
    )

    mock_messagebox.showerror.assert_called_once()
    call_args = mock_messagebox.showerror.call_args[0]
    assert call_args[0] == "Erro"
    assert "Window error" in call_args[1]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: handle_card_click
# ══════════════════════════════════════════════════════════════════════════════


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_card_click_clients_card(
    mock_messagebox,
    fake_parent,
    fake_state,
    fake_controller,
):
    """Test 5.1: Card clients - chama controller correto."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_card_click

    handle_card_click("clients", fake_state, fake_controller, fake_parent)

    fake_controller.handle_clients_card_click.assert_called_once_with(fake_state)
    fake_controller.handle_pending_card_click.assert_not_called()
    fake_controller.handle_tasks_today_card_click.assert_not_called()
    mock_messagebox.showerror.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_card_click_pending_card(
    mock_messagebox,
    fake_parent,
    fake_state,
    fake_controller,
):
    """Test 5.2: Card pending - chama controller correto."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_card_click

    handle_card_click("pending", fake_state, fake_controller, fake_parent)

    fake_controller.handle_pending_card_click.assert_called_once_with(fake_state)
    fake_controller.handle_clients_card_click.assert_not_called()
    fake_controller.handle_tasks_today_card_click.assert_not_called()
    mock_messagebox.showerror.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_card_click_tasks_card(
    mock_messagebox,
    fake_parent,
    fake_state,
    fake_controller,
):
    """Test 5.3: Card tasks - chama controller correto."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_card_click

    handle_card_click("tasks", fake_state, fake_controller, fake_parent)

    fake_controller.handle_tasks_today_card_click.assert_called_once_with(fake_state)
    fake_controller.handle_clients_card_click.assert_not_called()
    fake_controller.handle_pending_card_click.assert_not_called()
    mock_messagebox.showerror.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.logger")
@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_card_click_unknown_card_type(
    mock_messagebox,
    mock_logger,
    fake_parent,
    fake_state,
    fake_controller,
):
    """Test 5.4: Card type desconhecido - loga warning."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_card_click

    handle_card_click("unknown", fake_state, fake_controller, fake_parent)

    mock_logger.warning.assert_called_once()
    assert "Tipo de card desconhecido" in str(mock_logger.warning.call_args)
    fake_controller.handle_clients_card_click.assert_not_called()
    fake_controller.handle_pending_card_click.assert_not_called()
    fake_controller.handle_tasks_today_card_click.assert_not_called()


@patch("src.modules.hub.views.hub_dashboard_callbacks.messagebox")
def test_handle_card_click_controller_raises_exception(
    mock_messagebox,
    fake_parent,
    fake_state,
    fake_controller,
):
    """Test 5.5: Controller lança exceção - mostra erro."""
    from src.modules.hub.views.hub_dashboard_callbacks import handle_card_click

    fake_controller.handle_clients_card_click.side_effect = RuntimeError("Controller error")

    handle_card_click("clients", fake_state, fake_controller, fake_parent)

    mock_messagebox.showerror.assert_called_once()
    # A mensagem é "Erro" como título, com detalhes no segundo argumento
    call_args = mock_messagebox.showerror.call_args[0]
    assert call_args[0] == "Erro"
    assert "Controller error" in call_args[1]
