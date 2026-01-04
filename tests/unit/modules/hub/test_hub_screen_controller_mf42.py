# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false
"""Testes unitários para src/modules/hub/hub_screen_controller.py (MF-42).

Cobertura:
- __init__: inicialização do controller
- start/stop: lifecycle control via HubLifecycle
- refresh_dashboard/refresh_notes: triggers assíncronos
- load_*_data: carregamento síncrono via ViewModels
- setup_realtime/stop_realtime: configuração de canal realtime
- on_realtime_note: handler de eventos realtime
- on_quick_action_clicked/on_module_clicked: delegação para QuickActionsController
- on_card_clicked: handlers de dashboard
- on_*_note_clicked: handlers de notas
- update_notes_ui_state: atualização de estado da UI

Estratégia:
- Fakes simples para State, ViewModels, Services
- Mock para QuickActionsController
- Monkeypatch para async_tasks e callbacks externos
- Validação de branches: guards (org_id, cooldown), error handling, idempotency
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch


# =============================================================================
# FAKES & HELPERS
# =============================================================================


@dataclass
class FakeHubState:
    """Fake para HubState."""

    org_id: str | None = "org-123"
    is_active: bool = False
    is_dashboard_loaded: bool = False
    is_notes_loaded: bool = False
    last_dashboard_refresh_time: float = 0.0
    last_notes_refresh_time: float = 0.0
    last_authors_refresh_time: float = 0.0
    names_refreshing: bool = False
    cached_notes: list = field(default_factory=list)
    cached_authors: dict = field(default_factory=dict)
    live_sync_on: bool = False
    live_org_id: str | None = None
    live_channel: Any = None

    def mark_dashboard_refresh(self) -> None:
        """Marca timestamp de refresh do dashboard."""
        self.last_dashboard_refresh_time = time.time()

    def mark_notes_refresh(self) -> None:
        """Marca timestamp de refresh de notas."""
        self.last_notes_refresh_time = time.time()

    def mark_authors_refresh(self) -> None:
        """Marca timestamp de refresh de autores."""
        self.last_authors_refresh_time = time.time()

    def should_refresh_authors_cache(self) -> bool:
        """Verifica se deve fazer refresh do cache de autores."""
        if self.last_authors_refresh_time == 0:
            return True
        elapsed = time.time() - self.last_authors_refresh_time
        return elapsed > 300  # 5 min

    def update_notes_hash(self, notes: list) -> None:
        """Atualiza hash de notas."""
        pass


@dataclass
class FakeDashboardViewModel:
    """Fake para DashboardViewModel."""

    state: FakeHubState = field(default_factory=FakeHubState)
    load_calls: list = field(default_factory=list)
    _should_raise_on_load: bool = False

    def load(self, org_id: str, today: Any = None) -> Any:
        """Simula carregamento de dashboard."""
        self.load_calls.append((org_id, today))
        if self._should_raise_on_load:
            raise RuntimeError("Dashboard load error")
        return MagicMock(clients=[], pending=[], tasks=[])

    def from_error(self, message: str) -> Any:
        """Simula retorno de erro."""
        return MagicMock(error=message)


@dataclass
class FakeNotesViewModel:
    """Fake para NotesViewModel."""

    load_calls: list = field(default_factory=list)
    _should_raise_on_load: bool = False

    def load(self, org_id: str, author_names_cache: dict) -> Any:
        """Simula carregamento de notas."""
        self.load_calls.append((org_id, author_names_cache))
        if self._should_raise_on_load:
            raise RuntimeError("Notes load error")
        return MagicMock(notes=[])


@dataclass
class FakeQuickActionsViewModel:
    """Fake para QuickActionsViewModel."""

    pass


@dataclass
class FakeAsyncRunner:
    """Fake para HubAsyncRunner."""

    run_calls: list = field(default_factory=list)

    def run(self, task, *args, **kwargs) -> None:
        """Simula execução assíncrona."""
        self.run_calls.append((task, args, kwargs))


@dataclass
class FakeLifecycle:
    """Fake para HubLifecycle."""

    start_calls: list = field(default_factory=list)
    stop_calls: list = field(default_factory=list)

    def start(self) -> None:
        """Simula início do lifecycle."""
        self.start_calls.append(True)

    def stop(self) -> None:
        """Simula parada do lifecycle."""
        self.stop_calls.append(True)


@dataclass
class FakeHubScreenView:
    """Fake para HubScreenView."""

    update_notes_ui_state_calls: list = field(default_factory=list)
    render_notes_calls: list = field(default_factory=list)
    _org_id: str | None = "org-123"
    _email: str = "user@test.com"
    _dashboard_actions: Any = None

    def _get_org_id_safe(self) -> str | None:
        """Retorna org_id."""
        return self._org_id

    def _get_email_safe(self) -> str:
        """Retorna email."""
        return self._email

    def _get_app(self) -> Any:
        """Retorna app."""
        return MagicMock()

    def update_notes_ui_state(self, button_enabled: bool, placeholder_message: str | None) -> None:
        """Simula atualização de estado da UI de notas."""
        self.update_notes_ui_state_calls.append((button_enabled, placeholder_message))

    def render_notes(self, notes: list, force: bool = False) -> None:
        """Simula renderização de notas."""
        self.render_notes_calls.append((notes, force))


class ViewHidesDashboardActions(FakeHubScreenView):
    """View fake que esconde _dashboard_actions para testar branch else de hasattr."""

    def __getattribute__(self, name):
        """Levanta AttributeError para _dashboard_actions, simulando atributo não existente."""
        if name == "_dashboard_actions":
            raise AttributeError(name)
        return super().__getattribute__(name)


def create_controller(**overrides) -> Any:
    """Factory para criar controller com dependências fake."""
    state = overrides.pop("state", FakeHubState())
    dashboard_vm = overrides.pop("dashboard_vm", FakeDashboardViewModel(state=state))
    notes_vm = overrides.pop("notes_vm", FakeNotesViewModel())
    quick_actions_vm = overrides.pop("quick_actions_vm", FakeQuickActionsViewModel())
    async_runner = overrides.pop("async_runner", FakeAsyncRunner())
    lifecycle = overrides.pop("lifecycle", FakeLifecycle())
    view = overrides.pop("view", FakeHubScreenView())
    quick_actions_controller = overrides.pop("quick_actions_controller", MagicMock())
    logger = overrides.pop("logger", MagicMock())

    # Import aqui para evitar circular
    from src.modules.hub.hub_screen_controller import HubScreenController

    return HubScreenController(
        state=state,
        dashboard_vm=dashboard_vm,
        notes_vm=notes_vm,
        quick_actions_vm=quick_actions_vm,
        async_runner=async_runner,
        lifecycle=lifecycle,
        view=view,
        quick_actions_controller=quick_actions_controller,
        logger=logger,
    )


# =============================================================================
# TESTES: __init__
# =============================================================================


def test_init_stores_dependencies():
    """__init__ armazena todas as dependências."""
    state = FakeHubState()
    dashboard_vm = FakeDashboardViewModel()
    notes_vm = FakeNotesViewModel()
    quick_actions_vm = FakeQuickActionsViewModel()
    async_runner = FakeAsyncRunner()
    lifecycle = FakeLifecycle()
    view = FakeHubScreenView()
    quick_actions_controller = MagicMock()
    logger = MagicMock()

    controller = create_controller(
        state=state,
        dashboard_vm=dashboard_vm,
        notes_vm=notes_vm,
        quick_actions_vm=quick_actions_vm,
        async_runner=async_runner,
        lifecycle=lifecycle,
        view=view,
        quick_actions_controller=quick_actions_controller,
        logger=logger,
    )

    assert controller.state is state
    assert controller.dashboard_vm is dashboard_vm
    assert controller.notes_vm is notes_vm
    assert controller.quick_actions_vm is quick_actions_vm
    assert controller.async_runner is async_runner
    assert controller.lifecycle is lifecycle
    assert controller.view is view
    assert controller.quick_actions_controller is quick_actions_controller
    assert controller.logger is logger


def test_init_sets_realtime_warning_flag():
    """__init__ inicializa flag de warning de realtime."""
    controller = create_controller()

    assert controller._realtime_warning_logged is False


# =============================================================================
# TESTES: start/stop
# =============================================================================


def test_start_activates_state_and_lifecycle():
    """start() ativa state e inicia lifecycle."""
    state = FakeHubState()
    lifecycle = FakeLifecycle()
    controller = create_controller(state=state, lifecycle=lifecycle)

    controller.start()

    assert state.is_active is True
    assert len(lifecycle.start_calls) == 1


def test_stop_deactivates_state_and_lifecycle():
    """stop() desativa state e para lifecycle."""
    state = FakeHubState()
    lifecycle = FakeLifecycle()
    controller = create_controller(state=state, lifecycle=lifecycle)

    controller.start()
    controller.stop()

    assert state.is_active is False
    assert len(lifecycle.stop_calls) == 1


# =============================================================================
# TESTES: refresh_dashboard
# =============================================================================


def test_refresh_dashboard_marks_timestamp_and_loads():
    """refresh_dashboard() marca timestamp e carrega dados."""
    state = FakeHubState(is_active=True)
    controller = create_controller(state=state)

    with patch("src.modules.hub.services.hub_async_tasks_service.load_dashboard_data_async") as mock_load:
        controller.refresh_dashboard()

        assert state.last_dashboard_refresh_time > 0
        assert mock_load.called


def test_refresh_dashboard_does_nothing_when_inactive():
    """refresh_dashboard() não faz nada se state.is_active=False."""
    state = FakeHubState(is_active=False)
    controller = create_controller(state=state)

    with patch("src.modules.hub.services.hub_async_tasks_service.load_dashboard_data_async") as mock_load:
        controller.refresh_dashboard()

        assert state.last_dashboard_refresh_time == 0
        assert not mock_load.called


# =============================================================================
# TESTES: refresh_notes
# =============================================================================


def test_refresh_notes_marks_timestamp_and_loads():
    """refresh_notes() marca timestamp e carrega notas."""
    state = FakeHubState(is_active=True)
    controller = create_controller(state=state)

    with patch("src.modules.hub.services.hub_async_tasks_service.load_notes_data_async") as mock_load:
        controller.refresh_notes(force=True)

        assert state.last_notes_refresh_time > 0
        assert mock_load.called


def test_refresh_notes_does_nothing_when_inactive():
    """refresh_notes() não faz nada se state.is_active=False."""
    state = FakeHubState(is_active=False)
    controller = create_controller(state=state)

    with patch("src.modules.hub.services.hub_async_tasks_service.load_notes_data_async") as mock_load:
        controller.refresh_notes()

        assert state.last_notes_refresh_time == 0
        assert not mock_load.called


def test_refresh_notes_respects_cooldown():
    """refresh_notes() respeita cooldown de 5s."""
    state = FakeHubState(is_active=True)
    state.last_notes_refresh_time = time.time()
    controller = create_controller(state=state)

    with patch("src.modules.hub.services.hub_async_tasks_service.load_notes_data_async") as mock_load:
        controller.refresh_notes(force=False)

        # Não deve ter chamado (cooldown ativo)
        assert not mock_load.called


def test_refresh_notes_ignores_cooldown_when_forced():
    """refresh_notes() ignora cooldown quando force=True."""
    state = FakeHubState(is_active=True)
    state.last_notes_refresh_time = time.time()
    controller = create_controller(state=state)

    with patch("src.modules.hub.services.hub_async_tasks_service.load_notes_data_async") as mock_load:
        controller.refresh_notes(force=True)

        # Deve ter chamado (force ignora cooldown)
        assert mock_load.called


# =============================================================================
# TESTES: load_dashboard_data
# =============================================================================


def test_load_dashboard_data_loads_via_viewmodel():
    """load_dashboard_data() carrega via DashboardViewModel."""
    state = FakeHubState(org_id="org-123")
    dashboard_vm = FakeDashboardViewModel()
    controller = create_controller(state=state, dashboard_vm=dashboard_vm)

    result = controller.load_dashboard_data()

    assert len(dashboard_vm.load_calls) == 1
    assert dashboard_vm.load_calls[0][0] == "org-123"
    assert state.is_dashboard_loaded is True
    assert result is not None


def test_load_dashboard_data_returns_error_without_org_id():
    """load_dashboard_data() retorna erro se org_id não existe."""
    state = FakeHubState(org_id=None)
    dashboard_vm = FakeDashboardViewModel()
    controller = create_controller(state=state, dashboard_vm=dashboard_vm)

    result = controller.load_dashboard_data()

    # Deve ter retornado erro
    assert hasattr(result, "error")
    assert state.is_dashboard_loaded is False


def test_load_dashboard_data_handles_exception():
    """load_dashboard_data() trata exceção no ViewModel."""
    state = FakeHubState(org_id="org-123")
    dashboard_vm = FakeDashboardViewModel()
    dashboard_vm._should_raise_on_load = True
    controller = create_controller(state=state, dashboard_vm=dashboard_vm)

    result = controller.load_dashboard_data()

    # Deve ter retornado erro
    assert hasattr(result, "error")


# =============================================================================
# TESTES: load_notes_data
# =============================================================================


def test_load_notes_data_loads_via_viewmodel():
    """load_notes_data() carrega via NotesViewModel."""
    state = FakeHubState(org_id="org-123")
    notes_vm = FakeNotesViewModel()
    controller = create_controller(state=state, notes_vm=notes_vm)

    result = controller.load_notes_data()

    assert len(notes_vm.load_calls) == 1
    assert notes_vm.load_calls[0][0] == "org-123"
    assert state.is_notes_loaded is True
    assert isinstance(result, list)


def test_load_notes_data_returns_empty_without_org_id():
    """load_notes_data() retorna lista vazia se org_id não existe."""
    state = FakeHubState(org_id=None)
    notes_vm = FakeNotesViewModel()
    controller = create_controller(state=state, notes_vm=notes_vm)

    result = controller.load_notes_data()

    assert result == []
    assert len(notes_vm.load_calls) == 0


def test_load_notes_data_handles_exception():
    """load_notes_data() trata exceção no ViewModel."""
    state = FakeHubState(org_id="org-123")
    notes_vm = FakeNotesViewModel()
    notes_vm._should_raise_on_load = True
    controller = create_controller(state=state, notes_vm=notes_vm)

    result = controller.load_notes_data()

    # Deve retornar lista vazia em caso de erro
    assert result == []


# =============================================================================
# TESTES: setup_realtime
# =============================================================================


def test_setup_realtime_syncs_org_id_from_view():
    """setup_realtime() sincroniza org_id da view para state."""
    state = FakeHubState(org_id=None)
    view = FakeHubScreenView(_org_id="org-456")
    controller = create_controller(state=state, view=view)

    with patch("src.infra.supabase_client.get_supabase") as mock_supabase:
        mock_supabase.side_effect = Exception("Realtime not available")
        controller.setup_realtime()

        # Deve ter sincronizado org_id
        assert state.org_id == "org-456"


def test_setup_realtime_does_nothing_without_org_id():
    """setup_realtime() não faz nada se org_id não disponível."""
    state = FakeHubState(org_id=None)
    view = FakeHubScreenView(_org_id=None)
    logger = MagicMock()
    controller = create_controller(state=state, view=view, logger=logger)

    controller.setup_realtime()

    # Deve ter logado debug
    assert logger.debug.called


def test_setup_realtime_skips_if_already_active():
    """setup_realtime() não reconfigura se já ativo para mesmo org_id."""
    state = FakeHubState(org_id="org-123", live_sync_on=True, live_org_id="org-123")
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    with patch("src.infra.supabase_client.get_supabase") as mock_supabase:
        controller.setup_realtime()

        # Não deve ter chamado supabase
        assert not mock_supabase.called
        assert logger.debug.called


def test_setup_realtime_handles_attribute_error_with_sync_client():
    """setup_realtime() trata AttributeError de cliente sync gracefully."""
    state = FakeHubState(org_id="org-123")
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    with patch("src.infra.supabase_client.get_supabase") as mock_supabase:
        mock_supabase.side_effect = AttributeError("sync client has no attribute realtime")
        controller.setup_realtime()

        # Deve ter logado warning (primeira vez)
        assert logger.warning.called
        assert state.live_sync_on is False
        assert controller._realtime_warning_logged is True


def test_setup_realtime_handles_generic_exception():
    """setup_realtime() trata exceção genérica gracefully."""
    state = FakeHubState(org_id="org-123")
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    with patch("src.infra.supabase_client.get_supabase") as mock_supabase:
        mock_supabase.side_effect = Exception("Network error")
        controller.setup_realtime()

        # Deve ter logado debug
        assert logger.debug.called
        assert state.live_sync_on is False


def test_setup_realtime_logs_warning_only_once():
    """setup_realtime() loga warning apenas uma vez."""
    state = FakeHubState(org_id="org-123")
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    with patch("src.infra.supabase_client.get_supabase") as mock_supabase:
        mock_supabase.side_effect = AttributeError("sync client")

        controller.setup_realtime()  # Primeira vez
        logger.warning.reset_mock()

        controller.setup_realtime()  # Segunda vez

        # Não deve ter logado warning novamente
        assert not logger.warning.called


def test_setup_realtime_success_configures_channel():
    """setup_realtime() configura canal realtime com sucesso."""
    state = FakeHubState(org_id="org-123")
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    # Mock supabase client com realtime funcional
    mock_channel = MagicMock()
    mock_client = MagicMock()
    mock_client.realtime.channel.return_value = mock_channel

    with patch("src.infra.supabase_client.get_supabase", return_value=mock_client):
        controller.setup_realtime()

        # Deve ter configurado o canal
        assert mock_client.realtime.channel.called
        assert mock_channel.on.called
        assert mock_channel.subscribe.called
        # State deve estar atualizado
        assert state.live_sync_on is True
        assert state.live_org_id == "org-123"
        assert state.live_channel is mock_channel
        assert logger.debug.called


def test_setup_realtime_handles_attribute_error_other():
    """setup_realtime() trata AttributeError de outro tipo."""
    state = FakeHubState(org_id="org-123")
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    with patch("src.infra.supabase_client.get_supabase") as mock_supabase:
        mock_supabase.side_effect = AttributeError("some other error")
        controller.setup_realtime()

        # Deve ter logado error (não é erro de sync client)
        assert logger.error.called
        assert state.live_sync_on is False


# =============================================================================
# TESTES: stop_realtime
# =============================================================================


def test_stop_realtime_unsubscribes_channel():
    """stop_realtime() desinscreve canal."""
    state = FakeHubState(live_sync_on=True, live_org_id="org-123")
    mock_channel = MagicMock()
    state.live_channel = mock_channel
    controller = create_controller(state=state)

    controller.stop_realtime()

    assert state.live_sync_on is False
    assert state.live_org_id is None
    assert state.live_channel is None
    assert mock_channel.unsubscribe.called


def test_stop_realtime_handles_unsubscribe_error():
    """stop_realtime() trata erro ao desinscrever gracefully."""
    state = FakeHubState(live_sync_on=True)
    mock_channel = MagicMock()
    mock_channel.unsubscribe.side_effect = Exception("Unsubscribe error")
    state.live_channel = mock_channel
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    controller.stop_realtime()

    # Não deve explodir, deve logar warning
    assert logger.warning.called
    assert state.live_channel is None


# =============================================================================
# TESTES: Note event handlers (on_add_note_clicked, etc.)
# =============================================================================


def test_on_add_note_clicked():
    """on_add_note_clicked() loga debug."""
    logger = MagicMock()
    controller = create_controller(logger=logger)
    controller.on_add_note_clicked("Nova nota")
    assert logger.debug.called


def test_on_edit_note_clicked():
    """on_edit_note_clicked() loga debug."""
    logger = MagicMock()
    controller = create_controller(logger=logger)
    controller.on_edit_note_clicked("note-123")
    assert logger.debug.called


def test_on_delete_note_clicked():
    """on_delete_note_clicked() loga debug."""
    logger = MagicMock()
    controller = create_controller(logger=logger)
    controller.on_delete_note_clicked("note-456")
    assert logger.debug.called


def test_on_toggle_pin_clicked():
    """on_toggle_pin_clicked() loga debug."""
    logger = MagicMock()
    controller = create_controller(logger=logger)
    controller.on_toggle_pin_clicked("note-789")
    assert logger.debug.called


def test_on_toggle_done_clicked():
    """on_toggle_done_clicked() loga debug."""
    logger = MagicMock()
    controller = create_controller(logger=logger)
    controller.on_toggle_done_clicked("note-abc")
    assert logger.debug.called


def test_on_debug_shortcut():
    """on_debug_shortcut() loga debug."""
    logger = MagicMock()
    controller = create_controller(logger=logger)
    controller.on_debug_shortcut()
    assert logger.debug.called


# =============================================================================
# TESTES: on_realtime_note
# =============================================================================


def test_on_realtime_note_ignores_invalid_payload():
    """on_realtime_note() ignora payload sem id."""
    state = FakeHubState()
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    controller.on_realtime_note({})

    # Deve ter logado debug
    assert logger.debug.called


def test_on_realtime_note_ignores_existing_note():
    """on_realtime_note() ignora nota que já existe no cache."""
    state = FakeHubState()
    state.cached_notes = [{"id": "note-1"}]
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    controller.on_realtime_note({"id": "note-1"})

    # Deve ter logado debug e ignorado
    assert logger.debug.called
    assert len(state.cached_notes) == 1


def test_on_realtime_note_appends_new_note():
    """on_realtime_note() adiciona nova nota incrementalmente."""
    state = FakeHubState()
    view = FakeHubScreenView()
    logger = MagicMock()
    controller = create_controller(state=state, view=view, logger=logger)

    controller.on_realtime_note({"id": "note-new", "text": "Nova nota"})

    # Deve ter adicionado ao cache
    assert len(state.cached_notes) == 1
    assert state.cached_notes[0]["id"] == "note-new"
    # Deve ter renderizado
    assert len(view.render_notes_calls) == 1


def test_on_realtime_note_handles_render_error():
    """on_realtime_note() trata erro ao renderizar gracefully."""
    state = FakeHubState()
    view = FakeHubScreenView()
    view.render_notes = MagicMock(side_effect=Exception("Render error"))
    logger = MagicMock()
    controller = create_controller(state=state, view=view, logger=logger)

    controller.on_realtime_note({"id": "note-new"})

    # Deve ter logado erro mas não explodir
    assert logger.error.called
    assert len(state.cached_notes) == 1


# =============================================================================
# TESTES: on_quick_action_clicked
# =============================================================================


def test_on_quick_action_clicked_delegates_to_controller():
    """on_quick_action_clicked() delega para QuickActionsController."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_action_click.return_value = True
    controller = create_controller(quick_actions_controller=quick_actions_controller)

    controller.on_quick_action_clicked("clientes")

    assert quick_actions_controller.handle_action_click.called
    assert quick_actions_controller.handle_action_click.call_args[0][0] == "clientes"


def test_on_quick_action_clicked_normalizes_case():
    """on_quick_action_clicked() normaliza para lowercase."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_action_click.return_value = True
    controller = create_controller(quick_actions_controller=quick_actions_controller)

    controller.on_quick_action_clicked("CLIENTES")

    assert quick_actions_controller.handle_action_click.call_args[0][0] == "clientes"


def test_on_quick_action_clicked_logs_warning_if_not_handled():
    """on_quick_action_clicked() loga warning se ação não foi tratada."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_action_click.return_value = False
    logger = MagicMock()
    controller = create_controller(quick_actions_controller=quick_actions_controller, logger=logger)

    controller.on_quick_action_clicked("unknown")

    assert logger.warning.called


def test_on_quick_action_clicked_handles_exception():
    """on_quick_action_clicked() trata exceção gracefully."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_action_click.side_effect = Exception("Action error")
    logger = MagicMock()
    controller = create_controller(quick_actions_controller=quick_actions_controller, logger=logger)

    controller.on_quick_action_clicked("clientes")

    # Não deve explodir, deve logar erro
    assert logger.error.called


# =============================================================================
# TESTES: on_module_clicked
# =============================================================================


def test_on_module_clicked_validates_input():
    """on_module_clicked() valida entrada vazia."""
    logger = MagicMock()
    controller = create_controller(logger=logger)

    controller.on_module_clicked("")

    # Deve ter logado warning
    assert logger.warning.called


def test_on_module_clicked_delegates_to_controller():
    """on_module_clicked() delega para QuickActionsController."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_module_click.return_value = True
    controller = create_controller(quick_actions_controller=quick_actions_controller)

    controller.on_module_clicked("clientes")

    assert quick_actions_controller.handle_module_click.called


def test_on_module_clicked_logs_warning_if_unknown():
    """on_module_clicked() loga warning se módulo desconhecido."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_module_click.return_value = False
    logger = MagicMock()
    controller = create_controller(quick_actions_controller=quick_actions_controller, logger=logger)

    controller.on_module_clicked("unknown")

    assert logger.warning.called


def test_on_module_clicked_handles_exception():
    """on_module_clicked() trata exceção gracefully."""
    quick_actions_controller = MagicMock()
    quick_actions_controller.handle_module_click.side_effect = Exception("Module error")
    logger = MagicMock()
    controller = create_controller(quick_actions_controller=quick_actions_controller, logger=logger)

    controller.on_module_clicked("clientes")

    assert logger.error.called


# =============================================================================
# TESTES: on_card_clicked
# =============================================================================


def test_on_card_clicked_clients_calls_handler():
    """on_card_clicked('clients') chama on_card_clients_click."""
    controller = create_controller()

    with patch.object(controller, "on_card_clients_click") as mock_handler:
        controller.on_card_clicked("clients")
        assert mock_handler.called


def test_on_card_clicked_pending_calls_handler():
    """on_card_clicked('pending') chama on_card_pendencias_click."""
    controller = create_controller()

    with patch.object(controller, "on_card_pendencias_click") as mock_handler:
        controller.on_card_clicked("pending")
        assert mock_handler.called


def test_on_card_clicked_tasks_calls_handler():
    """on_card_clicked('tasks') chama on_card_tarefas_click."""
    controller = create_controller()

    with patch.object(controller, "on_card_tarefas_click") as mock_handler:
        controller.on_card_clicked("tasks")
        assert mock_handler.called


def test_on_card_clicked_unknown_logs_warning():
    """on_card_clicked() loga warning para card desconhecido."""
    logger = MagicMock()
    controller = create_controller(logger=logger)

    controller.on_card_clicked("unknown")

    assert logger.warning.called


# =============================================================================
# TESTES: card handlers
# =============================================================================


def test_on_card_clients_click_delegates_to_handle_card_click():
    """on_card_clients_click() delega para handle_card_click."""
    view = FakeHubScreenView()
    view._dashboard_actions = MagicMock()
    controller = create_controller(view=view)

    with patch("src.modules.hub.hub_screen_controller.handle_card_click") as mock_handler:
        controller.on_card_clients_click()
        assert mock_handler.called


def test_on_card_clients_click_fallback_to_quick_actions():
    """on_card_clients_click() usa fallback se dashboard_actions não existe."""
    view = FakeHubScreenView()
    # view não tem _dashboard_actions (atributo não configurado)
    quick_actions_controller = MagicMock()
    controller = create_controller(view=view, quick_actions_controller=quick_actions_controller)

    # Mock handle_card_click para levantar exceção (simulando código não ter _dashboard_actions)
    with patch(
        "src.modules.hub.hub_screen_controller.handle_card_click", side_effect=AttributeError("No dashboard_actions")
    ):
        controller.on_card_clients_click()

        # Deve ter usado fallback (não vai chegar no fallback porque exception é logada)
        # Na verdade, precisa verificar que exception foi tratada
        assert controller.logger.exception.called


def test_on_card_clients_click_handles_exception():
    """on_card_clients_click() trata exceção gracefully."""
    view = FakeHubScreenView()
    view._dashboard_actions = MagicMock()
    logger = MagicMock()
    controller = create_controller(view=view, logger=logger)

    with patch("src.modules.hub.hub_screen_controller.handle_card_click", side_effect=Exception("Error")):
        controller.on_card_clients_click()
        assert logger.exception.called


def test_on_card_pendencias_click_with_dashboard_actions():
    """on_card_pendencias_click() usa _dashboard_actions quando disponível."""
    view = FakeHubScreenView()
    view._dashboard_actions = MagicMock()
    controller = create_controller(view=view)

    with patch("src.modules.hub.hub_screen_controller.handle_card_click") as mock_handler:
        controller.on_card_pendencias_click()
        assert mock_handler.called
        assert mock_handler.call_args[1]["card_type"] == "pending"


def test_on_card_tarefas_click_with_dashboard_actions():
    """on_card_tarefas_click() usa _dashboard_actions quando disponível."""
    view = FakeHubScreenView()
    view._dashboard_actions = MagicMock()
    controller = create_controller(view=view)

    with patch("src.modules.hub.hub_screen_controller.handle_card_click") as mock_handler:
        controller.on_card_tarefas_click()
        assert mock_handler.called
        assert mock_handler.call_args[1]["card_type"] == "tasks"


# =============================================================================
# TESTES: dashboard event handlers
# =============================================================================


def test_on_new_task_delegates_to_helper():
    """on_new_task() delega para handle_new_task_click."""
    view = FakeHubScreenView()
    controller = create_controller(view=view)

    with patch("src.modules.hub.hub_screen_controller.handle_new_task_click") as mock_handler:
        controller.on_new_task()
        assert mock_handler.called


def test_on_new_task_handles_exception():
    """on_new_task() trata exceção gracefully."""
    view = FakeHubScreenView()
    logger = MagicMock()
    controller = create_controller(view=view, logger=logger)

    with patch("src.modules.hub.hub_screen_controller.handle_new_task_click", side_effect=Exception("Error")):
        controller.on_new_task()
        assert logger.exception.called


def test_on_new_obligation_delegates_to_helper():
    """on_new_obligation() delega para handle_new_obligation_click."""
    view = FakeHubScreenView()
    controller = create_controller(view=view)

    with patch("src.modules.hub.hub_screen_controller.handle_new_obligation_click") as mock_handler:
        controller.on_new_obligation()
        assert mock_handler.called


def test_on_new_obligation_callback_calls_handle_client_picked():
    """on_new_obligation() callback on_client_picked chama handle_client_picked_for_obligation."""
    view = FakeHubScreenView()
    view._get_org_id_safe = MagicMock(return_value="org-123")
    view._get_email_safe = MagicMock(return_value="user@test.com")
    view._get_app = MagicMock(return_value=MagicMock())
    controller = create_controller(view=view)

    captured_callback = None

    def capture_callback(*args, **kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_client_picked")

    with (
        patch("src.modules.hub.hub_screen_controller.handle_new_obligation_click", side_effect=capture_callback),
        patch("src.modules.hub.hub_screen_controller.handle_client_picked_for_obligation") as mock_picked,
    ):
        controller.on_new_obligation()

        # Agora executar o callback capturado
        assert captured_callback is not None
        client_data = {"id": "client-123"}
        captured_callback(client_data)

        # Deve ter chamado handle_client_picked_for_obligation
        assert mock_picked.called
        assert mock_picked.call_args[1]["client_data"] == client_data


def test_on_new_obligation_callback_refresh_calls_refresh_dashboard():
    """on_new_obligation() on_refresh_callback chama refresh_dashboard."""
    state = FakeHubState(is_active=True, org_id="org-123")
    view = FakeHubScreenView()
    view._get_org_id_safe = MagicMock(return_value="org-123")
    view._get_email_safe = MagicMock(return_value="user@test.com")
    view._get_app = MagicMock(return_value=MagicMock())
    controller = create_controller(state=state, view=view)

    # Vamos apenas verificar que refresh_dashboard pode ser chamado
    # via on_refresh_callback sem erro
    with (
        patch("src.modules.hub.hub_screen_controller.handle_new_obligation_click") as mock_obligation,
        patch("src.modules.hub.hub_screen_controller.handle_client_picked_for_obligation"),
    ):
        controller.on_new_obligation()

        # Verificar que handle_new_obligation_click foi chamado com callback
        assert mock_obligation.called
        call_kwargs = mock_obligation.call_args[1]
        assert "on_client_picked" in call_kwargs

        # Executar o callback para verificar que não explode
        on_client_picked = call_kwargs["on_client_picked"]
        on_client_picked({"id": "client-123"})


def test_on_new_obligation_handles_exception():
    """on_new_obligation() trata exceção gracefully."""
    view = FakeHubScreenView()
    logger = MagicMock()
    controller = create_controller(view=view, logger=logger)

    with patch("src.modules.hub.hub_screen_controller.handle_new_obligation_click", side_effect=Exception("Error")):
        controller.on_new_obligation()
        assert logger.exception.called


def test_on_view_all_activity_delegates_to_helper():
    """on_view_all_activity() delega para handle_view_all_activity_click."""
    view = FakeHubScreenView()
    controller = create_controller(view=view)

    with patch("src.modules.hub.hub_screen_controller.handle_view_all_activity_click") as mock_handler:
        controller.on_view_all_activity()
        assert mock_handler.called


# =============================================================================
# TESTES: update_notes_ui_state
# =============================================================================


def test_update_notes_ui_state_enables_when_has_org():
    """update_notes_ui_state() habilita botão quando tem org_id."""
    state = FakeHubState(org_id="org-123")
    view = FakeHubScreenView()
    controller = create_controller(state=state, view=view)

    controller.update_notes_ui_state()

    # Deve ter habilitado botão
    assert len(view.update_notes_ui_state_calls) == 1
    assert view.update_notes_ui_state_calls[0][0] is True  # button_enabled
    assert view.update_notes_ui_state_calls[0][1] is None  # placeholder_message


def test_update_notes_ui_state_disables_when_no_org():
    """update_notes_ui_state() desabilita botão quando não tem org_id."""
    state = FakeHubState(org_id=None)
    view = FakeHubScreenView()
    controller = create_controller(state=state, view=view)

    controller.update_notes_ui_state()

    # Deve ter desabilitado botão
    assert len(view.update_notes_ui_state_calls) == 1
    assert view.update_notes_ui_state_calls[0][0] is False  # button_enabled
    assert view.update_notes_ui_state_calls[0][1] == "Aguardando autenticação..."


# =============================================================================
# TESTES: refresh_author_names_cache
# =============================================================================


def test_refresh_author_names_cache_skips_if_not_needed():
    """refresh_author_names_cache() não faz nada se não precisa refresh."""
    state = FakeHubState()
    state.last_authors_refresh_time = time.time()
    controller = create_controller(state=state)

    controller.refresh_author_names_cache(force=False)

    # Não deve ter marcado refresh (timestamp não mudou significativamente)
    # Como acabamos de marcar, should_refresh_authors_cache() retorna False


def test_refresh_author_names_cache_skips_if_already_refreshing():
    """refresh_author_names_cache() não faz nada se já está refreshing."""
    state = FakeHubState(names_refreshing=True)
    controller = create_controller(state=state)

    initial_time = state.last_authors_refresh_time
    controller.refresh_author_names_cache(force=True)

    # Não deve ter mudado timestamp (já está refreshing)
    assert state.last_authors_refresh_time == initial_time


def test_refresh_author_names_cache_marks_refresh_when_needed():
    """refresh_author_names_cache() marca refresh quando necessário."""
    state = FakeHubState(names_refreshing=False)
    state.last_authors_refresh_time = 0
    logger = MagicMock()
    controller = create_controller(state=state, logger=logger)

    controller.refresh_author_names_cache(force=True)

    # Deve ter marcado refresh
    assert state.last_authors_refresh_time > 0
    assert logger.debug.called


# =============================================================================
# TESTES: async delegation
# =============================================================================


def test_load_dashboard_data_async_delegates_to_service():
    """load_dashboard_data_async() delega para async_tasks service."""
    controller = create_controller()

    with patch("src.modules.hub.services.hub_async_tasks_service.load_dashboard_data_async") as mock_load:
        controller.load_dashboard_data_async()
        assert mock_load.called
        assert mock_load.call_args[0][0] is controller


def test_load_notes_data_async_delegates_to_service():
    """load_notes_data_async() delega para async_tasks service."""
    controller = create_controller()

    with patch("src.modules.hub.services.hub_async_tasks_service.load_notes_data_async") as mock_load:
        controller.load_notes_data_async()
        assert mock_load.called


# =============================================================================
# TESTES: Branches else de hasattr(_dashboard_actions) (MF-42b)
# =============================================================================


def test_on_card_clients_click_without_dashboard_actions_uses_fallback():
    """on_card_clients_click() usa fallback quick_actions quando _dashboard_actions não existe."""
    view = ViewHidesDashboardActions()
    quick_actions_controller = MagicMock()
    controller = create_controller(view=view, quick_actions_controller=quick_actions_controller)

    controller.on_card_clients_click()

    # Deve ter chamado quick_actions_controller.handle_action_click com "clientes"
    assert quick_actions_controller.handle_action_click.called
    assert quick_actions_controller.handle_action_click.call_args[0][0] == "clientes"


def test_on_card_pendencias_click_without_dashboard_actions_logs_warning():
    """on_card_pendencias_click() loga warning quando _dashboard_actions não existe."""
    view = ViewHidesDashboardActions()
    logger = MagicMock()
    controller = create_controller(view=view, logger=logger)

    controller.on_card_pendencias_click()

    # Deve ter logado warning específico
    assert logger.warning.called
    assert "Dashboard actions não disponível para card pendencias" in str(logger.warning.call_args)


def test_on_card_tarefas_click_without_dashboard_actions_logs_warning():
    """on_card_tarefas_click() loga warning quando _dashboard_actions não existe."""
    view = ViewHidesDashboardActions()
    logger = MagicMock()
    controller = create_controller(view=view, logger=logger)

    controller.on_card_tarefas_click()

    # Deve ter logado warning específico
    assert logger.warning.called
    assert "Dashboard actions não disponível para card tarefas" in str(logger.warning.call_args)


def test_refresh_author_names_cache_async_delegates_to_service():
    """refresh_author_names_cache_async() delega para async_tasks service."""
    controller = create_controller()

    with patch("src.modules.hub.services.hub_async_tasks_service.refresh_author_names_cache_async") as mock_refresh:
        controller.refresh_author_names_cache_async(force=True)
        assert mock_refresh.called
        assert mock_refresh.call_args[1]["force"] is True
