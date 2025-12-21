# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false
"""Testes unitários para src/modules/hub/services/hub_async_tasks_service.py (MF-40).

Cobertura:
- load_dashboard_data_async: carregamento assíncrono, org_id validation, callbacks
- _update_dashboard_ui_from_state: decisão de cenário (erro/vazio/dados)
- load_notes_data_async: carregamento assíncrono de notas, callbacks
- _update_notes_ui_from_state: renderização de notas, erro, vazio
- refresh_author_names_cache_async: cooldown, force, threading, cache update

Estratégia:
- Fakes para controller/view/state/VM (duck typing para testes)
- Monkeypatch para threading.Thread (execução síncrona)
- Monkeypatch para time.time() (controle de cooldown)
- Validação de branches (org_id ausente, erros, vazios, sucesso)

Nota: pyright: reportArgumentType=false desabilita avisos de tipo para fakes de teste.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

from src.modules.hub.services.hub_async_tasks_service import (
    _update_dashboard_ui_from_state,
    _update_notes_ui_from_state,
    load_dashboard_data_async,
    load_notes_data_async,
    refresh_author_names_cache_async,
)


# =============================================================================
# FAKES & HELPERS
# =============================================================================


class FakeState:
    """State fake com campos necessários."""

    def __init__(self):
        self.org_id: str | None = None
        self.is_dashboard_loaded = False
        self.is_notes_loaded = False
        self.cached_authors: dict[str, Any] = {}
        self.cached_notes: list[Any] = []
        self.names_refreshing = False
        self.last_author_cache_refresh: float = 0.0

    def update_notes_hash(self, notes):
        """Stub para atualizar hash de notas."""
        pass

    def mark_authors_refresh(self):
        """Marca refresh de autores."""
        self.last_author_cache_refresh = time.time()


class FakeDashboardView:
    """Fake para dashboard view."""

    def __init__(self):
        self.dashboard_scroll = MagicMock()
        self.dashboard_scroll.content = MagicMock()
        self.dashboard_scroll.content.winfo_children = MagicMock(return_value=[])


class FakeNotesView:
    """Fake para notes view."""

    def __init__(self):
        self.rendered_error: str | None = None
        self.rendered_empty: str | None = None

    def render_error(self, message: str):
        self.rendered_error = message

    def render_empty(self, message: str):
        self.rendered_empty = message


class FakeView:
    """View fake implementando interface mínima."""

    def __init__(self):
        self._org_id: str | None = None
        self._after_callbacks: list = []
        self._dashboard_view: FakeDashboardView | None = None
        self._notes_view: FakeNotesView | None = None
        self.updated_dashboard_states: list = []
        self.rendered_notes_calls: list = []

    def _get_org_id_safe(self) -> str | None:
        return self._org_id

    def after(self, ms: int, func):
        """Executa callback imediatamente."""
        self._after_callbacks.append((ms, func))
        func()

    def update_dashboard(self, state):
        """Registra chamadas de atualização de dashboard."""
        self.updated_dashboard_states.append(state)

    def render_notes(self, notes, force=False):
        """Registra chamadas de renderização de notas."""
        self.rendered_notes_calls.append((notes, force))


class FakeAsyncRunner:
    """Fake para async runner (execução síncrona)."""

    def __init__(self, tk_root):
        self.tk_root = tk_root
        self.run_calls: list = []
        self.logger = None

    def run(self, func, on_success, on_error):
        """Executa func imediatamente e agenda callback via after."""
        self.run_calls.append(("run", func, on_success, on_error))
        try:
            result = func()
            # Simula after(0, on_success, result)
            self.tk_root.after(0, lambda: on_success(result))
        except Exception as exc:
            # Simula after(0, on_error, exc)
            self.tk_root.after(0, lambda exc=exc: on_error(exc))


class FakeDashboardVM:
    """Fake para DashboardViewModel."""

    def __init__(self):
        self.load_calls: list = []
        self.from_error_calls: list = []
        self._next_result = None
        self._should_raise = False

    def load(self, org_id, today):
        """Simula carregamento de dashboard."""
        self.load_calls.append((org_id, today))
        if self._should_raise:
            raise RuntimeError("Dashboard load error")
        return self._next_result

    def from_error(self, message: str):
        """Cria estado de erro."""
        self.from_error_calls.append(message)
        state = MagicMock()
        state.error_message = message
        state.snapshot = None
        return state


class FakeNotesVM:
    """Fake para NotesViewModel."""

    def __init__(self):
        self.load_calls: list = []
        self.fetch_missing_authors_calls: list = []
        self._next_result = None
        self._should_raise = False
        self._missing_authors_result: dict[str, str] = {}

    def load(self, org_id, author_names_cache):
        """Simula carregamento de notas."""
        self.load_calls.append((org_id, author_names_cache))
        if self._should_raise:
            raise RuntimeError("Notes load error")
        return self._next_result

    def fetch_missing_authors(self, emails: list[str]) -> dict[str, str]:
        """Simula busca de autores ausentes."""
        self.fetch_missing_authors_calls.append(emails)
        return self._missing_authors_result


class FakeController:
    """Controller fake com todas as dependências."""

    def __init__(self):
        self.state = FakeState()
        self.view = FakeView()
        self.async_runner = FakeAsyncRunner(self.view)  # Passa view como tk_root
        self.dashboard_vm = FakeDashboardVM()
        self.notes_vm = FakeNotesVM()
        self.logger = MagicMock()


# =============================================================================
# TESTES: load_dashboard_data_async
# =============================================================================


def test_load_dashboard_data_async_no_org_id_returns_early(monkeypatch):
    """load_dashboard_data_async sem org_id retorna early sem carregar."""
    controller = FakeController()
    controller.state.org_id = None
    controller.view._org_id = None

    # Mock ttkbootstrap para evitar import error
    monkeypatch.setitem(__import__("sys").modules, "ttkbootstrap", MagicMock())

    load_dashboard_data_async(controller)

    # Não deve chamar async_runner.run
    assert len(controller.async_runner.run_calls) == 0
    assert controller.logger.debug.called


def test_load_dashboard_data_async_syncs_org_id_from_view():
    """load_dashboard_data_async sincroniza org_id do view para state."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = None

    # Configurar dashboard_vm para retornar estado válido
    state = MagicMock()
    state.error_message = None
    state.snapshot = {"data": "test"}
    controller.dashboard_vm._next_result = state

    load_dashboard_data_async(controller)

    # org_id deve ser sincronizado
    assert controller.state.org_id == "org-123"
    assert len(controller.async_runner.run_calls) == 1


def test_load_dashboard_data_async_success_calls_update_ui():
    """load_dashboard_data_async com sucesso chama callback on_success."""
    controller = FakeController()
    controller.view._org_id = "org-456"
    controller.state.org_id = "org-456"

    state = MagicMock()
    state.error_message = None
    state.snapshot = {"cards": []}
    controller.dashboard_vm._next_result = state

    load_dashboard_data_async(controller)

    # Callback de sucesso deve ter chamado update_dashboard
    assert len(controller.view.updated_dashboard_states) == 1
    assert controller.view.updated_dashboard_states[0] == state


def test_load_dashboard_data_async_error_calls_on_error():
    """load_dashboard_data_async com erro chama callback on_error."""
    controller = FakeController()
    controller.view._org_id = "org-789"
    controller.state.org_id = "org-789"
    controller.dashboard_vm._should_raise = True

    load_dashboard_data_async(controller)

    # Callback de erro deve ter criado estado de erro
    assert len(controller.dashboard_vm.from_error_calls) == 1
    assert "Não foi possível carregar o dashboard" in controller.dashboard_vm.from_error_calls[0]


def test_load_dashboard_data_async_no_org_id_shows_waiting_message(monkeypatch):
    """load_dashboard_data_async sem org_id tenta mostrar mensagem de aguardo."""
    controller = FakeController()
    controller.view._org_id = None
    controller.state.org_id = None
    controller.view._dashboard_view = FakeDashboardView()

    # Mock ttkbootstrap
    fake_tb = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "ttkbootstrap", fake_tb)

    load_dashboard_data_async(controller)

    # Deve ter tentado destruir widgets
    assert controller.view._dashboard_view.dashboard_scroll.content.winfo_children.called


def test_load_dashboard_data_async_waiting_message_error_handled(monkeypatch):
    """load_dashboard_data_async trata erro ao mostrar mensagem de aguardo."""
    controller = FakeController()
    controller.view._org_id = None
    controller.state.org_id = None
    controller.view._dashboard_view = FakeDashboardView()
    controller.view._dashboard_view.dashboard_scroll.content.winfo_children.side_effect = RuntimeError("Widget error")

    # Mock ttkbootstrap
    monkeypatch.setitem(__import__("sys").modules, "ttkbootstrap", MagicMock())

    load_dashboard_data_async(controller)

    # Não deve explodir
    assert controller.logger.debug.called


# =============================================================================
# TESTES: _update_dashboard_ui_from_state
# =============================================================================


def test_update_dashboard_ui_from_state_with_error_message():
    """_update_dashboard_ui_from_state com erro renderiza erro e retorna early."""
    controller = FakeController()
    state = MagicMock()
    state.error_message = "Dashboard error"
    state.snapshot = None

    _update_dashboard_ui_from_state(controller, state)

    assert len(controller.view.updated_dashboard_states) == 1
    assert controller.view.updated_dashboard_states[0] == state
    assert not controller.state.is_dashboard_loaded


def test_update_dashboard_ui_from_state_no_snapshot_creates_error():
    """_update_dashboard_ui_from_state sem snapshot cria estado de erro."""
    controller = FakeController()
    state = MagicMock()
    state.error_message = None
    state.snapshot = None

    _update_dashboard_ui_from_state(controller, state)

    # Deve ter criado estado de erro
    assert len(controller.dashboard_vm.from_error_calls) == 1
    assert "Não foi possível carregar dados do dashboard" in controller.dashboard_vm.from_error_calls[0]


def test_update_dashboard_ui_from_state_with_data_success():
    """_update_dashboard_ui_from_state com dados renderiza e marca loaded."""
    controller = FakeController()
    state = MagicMock()
    state.error_message = None
    state.snapshot = {"data": "valid"}

    _update_dashboard_ui_from_state(controller, state)

    assert len(controller.view.updated_dashboard_states) == 1
    assert controller.state.is_dashboard_loaded


# =============================================================================
# TESTES: load_notes_data_async
# =============================================================================


def test_load_notes_data_async_no_org_id_returns_early():
    """load_notes_data_async sem org_id retorna early."""
    controller = FakeController()
    controller.state.org_id = None
    controller.view._org_id = None

    load_notes_data_async(controller)

    assert len(controller.async_runner.run_calls) == 0
    assert controller.logger.debug.called


def test_load_notes_data_async_syncs_org_id():
    """load_notes_data_async sincroniza org_id do view."""
    controller = FakeController()
    controller.view._org_id = "org-notes"
    controller.state.org_id = None

    state = MagicMock()
    state.notes = []
    state.error_message = None
    controller.notes_vm._next_result = state

    load_notes_data_async(controller)

    assert controller.state.org_id == "org-notes"


def test_load_notes_data_async_success_updates_ui():
    """load_notes_data_async com sucesso atualiza UI."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"

    state = MagicMock()
    state.notes = [{"id": 1, "body": "Note 1"}]
    state.error_message = None
    controller.notes_vm._next_result = state

    load_notes_data_async(controller)

    # Notas devem ter sido armazenadas no state
    assert controller.state.cached_notes == state.notes
    assert controller.state.is_notes_loaded


def test_load_notes_data_async_error_renders_error():
    """load_notes_data_async com erro renderiza mensagem de erro."""
    controller = FakeController()
    controller.view._org_id = "org-456"
    controller.state.org_id = "org-456"
    controller.view._notes_view = FakeNotesView()
    controller.notes_vm._should_raise = True

    load_notes_data_async(controller)

    # Deve ter renderizado erro
    assert controller.view._notes_view.rendered_error is not None
    assert "Erro ao carregar notas" in controller.view._notes_view.rendered_error


# =============================================================================
# TESTES: _update_notes_ui_from_state
# =============================================================================


def test_update_notes_ui_from_state_with_error_message():
    """_update_notes_ui_from_state com erro renderiza erro."""
    controller = FakeController()
    controller.view._notes_view = FakeNotesView()
    state = MagicMock()
    state.error_message = "Notes error"

    _update_notes_ui_from_state(controller, state)

    assert controller.view._notes_view.rendered_error == "Notes error"
    assert not controller.state.is_notes_loaded


def test_update_notes_ui_from_state_with_notes_renders():
    """_update_notes_ui_from_state com notas renderiza via view."""
    controller = FakeController()
    state = MagicMock()
    state.error_message = None
    state.notes = [{"id": 1}, {"id": 2}]

    _update_notes_ui_from_state(controller, state)

    assert controller.state.cached_notes == state.notes
    assert len(controller.view.rendered_notes_calls) == 1
    assert controller.state.is_notes_loaded


def test_update_notes_ui_from_state_empty_notes_shows_message():
    """_update_notes_ui_from_state sem notas mostra mensagem de vazio."""
    controller = FakeController()
    controller.view._notes_view = FakeNotesView()
    state = MagicMock()
    state.error_message = None
    state.notes = []

    _update_notes_ui_from_state(controller, state)

    assert controller.view._notes_view.rendered_empty is not None
    assert "Nenhuma anotação" in controller.view._notes_view.rendered_empty


def test_update_notes_ui_from_state_render_error_handled():
    """_update_notes_ui_from_state trata erro ao renderizar."""
    controller = FakeController()
    controller.view.render_notes = MagicMock(side_effect=RuntimeError("Render error"))
    state = MagicMock()
    state.error_message = None
    state.notes = [{"id": 1}]

    _update_notes_ui_from_state(controller, state)

    # Não deve explodir
    assert controller.logger.error.called


def test_update_notes_ui_from_state_error_render_exception_handled():
    """_update_notes_ui_from_state trata exceção ao renderizar erro."""
    controller = FakeController()
    controller.view._notes_view = FakeNotesView()
    controller.view._notes_view.render_error = MagicMock(side_effect=RuntimeError("Render error"))
    state = MagicMock()
    state.error_message = "Test error"

    _update_notes_ui_from_state(controller, state)

    # Não deve explodir
    assert controller.logger.error.called


# =============================================================================
# TESTES: refresh_author_names_cache_async
# =============================================================================


def test_refresh_author_names_cache_async_respects_cooldown(monkeypatch):
    """refresh_author_names_cache_async respeita cooldown quando force=False."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    now = 1000.0
    controller.state.last_author_cache_refresh = now - 100.0  # 100s atrás (dentro do cooldown de 300s)

    monkeypatch.setattr(time, "time", lambda: now)

    refresh_author_names_cache_async(controller, force=False)

    # Não deve ter iniciado refresh (dentro do cooldown)
    assert len(controller.async_runner.run_calls) == 0


def test_refresh_author_names_cache_async_force_ignores_cooldown(monkeypatch):
    """refresh_author_names_cache_async com force=True ignora cooldown."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    now = 1000.0
    controller.state.last_author_cache_refresh = now - 50.0  # Recente (dentro do cooldown)
    controller.state.cached_authors = {"user@test.com": "Unknown"}

    monkeypatch.setattr(time, "time", lambda: now)

    # Mock threading
    threads_started = []

    class FakeThread:
        def __init__(self, target, daemon, name):
            self.target = target
            threads_started.append(self)

        def start(self):
            self.target()

    monkeypatch.setattr("threading.Thread", FakeThread)

    controller.notes_vm._missing_authors_result = {"user@test.com": "Test User"}

    refresh_author_names_cache_async(controller, force=True)

    # Deve ter iniciado refresh mesmo dentro do cooldown
    assert len(threads_started) == 1


def test_refresh_author_names_cache_async_already_refreshing_skips():
    """refresh_author_names_cache_async não inicia se já está refreshing."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    controller.state.names_refreshing = True
    controller.state.last_author_cache_refresh = 0.0

    refresh_author_names_cache_async(controller, force=True)

    # Não deve ter iniciado (já refreshing)
    assert len(controller.async_runner.run_calls) == 0


def test_refresh_author_names_cache_async_no_org_id_returns():
    """refresh_author_names_cache_async sem org_id retorna early."""
    controller = FakeController()
    controller.state.org_id = None
    controller.view._org_id = None
    controller.state.last_author_cache_refresh = 0.0

    refresh_author_names_cache_async(controller, force=True)

    assert not controller.state.names_refreshing


def test_refresh_author_names_cache_async_syncs_org_id():
    """refresh_author_names_cache_async sincroniza org_id do view."""
    controller = FakeController()
    controller.view._org_id = "org-sync"
    controller.state.org_id = None
    controller.state.last_author_cache_refresh = 0.0

    # Não tem cached_authors, então retorna early após sync
    refresh_author_names_cache_async(controller, force=True)

    assert controller.state.org_id == "org-sync"


def test_refresh_author_names_cache_async_no_missing_emails_completes(monkeypatch):
    """refresh_author_names_cache_async sem emails ausentes completa imediatamente."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    controller.state.last_author_cache_refresh = 0.0
    controller.state.cached_authors = {}  # Nenhum email

    monkeypatch.setattr(time, "time", lambda: 1000.0)

    refresh_author_names_cache_async(controller, force=True)

    # Deve ter marcado refresh mesmo sem emails
    assert controller.state.names_refreshing is False
    assert controller.state.last_author_cache_refresh > 0


def test_refresh_author_names_cache_async_success_updates_cache(monkeypatch):
    """refresh_author_names_cache_async com sucesso atualiza cache."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    controller.state.last_author_cache_refresh = 0.0
    controller.state.cached_authors = {"user@test.com": "Unknown"}
    now = 1000.0

    monkeypatch.setattr(time, "time", lambda: now)

    # Mock threading
    threads_started = []

    class FakeThread:
        def __init__(self, target, daemon, name):
            self.target = target
            threads_started.append(self)

        def start(self):
            self.target()

    monkeypatch.setattr("threading.Thread", FakeThread)

    controller.notes_vm._missing_authors_result = {"user@test.com": "Real Name"}

    refresh_author_names_cache_async(controller, force=True)

    # Cache deve ter sido atualizado
    assert "user@test.com" in controller.state.cached_authors
    assert controller.state.cached_authors["user@test.com"] == "Real Name"
    assert not controller.state.names_refreshing


def test_refresh_author_names_cache_async_error_handled(monkeypatch):
    """refresh_author_names_cache_async trata erro no fetch."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    controller.state.last_author_cache_refresh = 0.0
    controller.state.cached_authors = {"user@test.com": "Unknown"}

    monkeypatch.setattr(time, "time", lambda: 1000.0)

    # Mock threading
    class FakeThread:
        def __init__(self, target, daemon, name):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr("threading.Thread", FakeThread)

    # Configurar erro no fetch
    def fetch_error(emails):
        raise RuntimeError("Fetch error")

    controller.notes_vm.fetch_missing_authors = fetch_error

    refresh_author_names_cache_async(controller, force=True)

    # Não deve explodir, names_refreshing deve ser False
    assert not controller.state.names_refreshing
    assert controller.logger.error.called


def test_refresh_author_names_cache_async_converts_tuple_cache(monkeypatch):
    """refresh_author_names_cache_async converte cache em formato tuple corretamente."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    controller.state.last_author_cache_refresh = 0.0
    now = 1000.0
    # Cache com formato tuple (nome, expiry)
    controller.state.cached_authors = {
        "old@test.com": ("Old Name", now - 500),
        "new@test.com": "Unknown",
    }

    monkeypatch.setattr(time, "time", lambda: now)

    # Mock threading
    class FakeThread:
        def __init__(self, target, daemon, name):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr("threading.Thread", FakeThread)

    controller.notes_vm._missing_authors_result = {"new@test.com": "New Name"}

    refresh_author_names_cache_async(controller, force=True)

    # Cache deve ter ambos os nomes (mantém old, atualiza new)
    assert controller.state.cached_authors["old@test.com"] == "Old Name"
    assert controller.state.cached_authors["new@test.com"] == "New Name"


def test_refresh_author_names_cache_async_no_notes_vm_completes(monkeypatch):
    """refresh_author_names_cache_async sem notes_vm completa com cache vazio."""
    controller = FakeController()
    delattr(controller, "notes_vm")
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    controller.state.last_author_cache_refresh = 0.0
    controller.state.cached_authors = {"user@test.com": "Unknown"}

    monkeypatch.setattr(time, "time", lambda: 1000.0)

    refresh_author_names_cache_async(controller, force=True)

    # Deve ter completado sem erro
    assert not controller.state.names_refreshing


def test_refresh_author_names_cache_async_after_cooldown_refreshes(monkeypatch):
    """refresh_author_names_cache_async após cooldown expirar inicia refresh."""
    controller = FakeController()
    controller.view._org_id = "org-123"
    controller.state.org_id = "org-123"
    now = 1000.0
    controller.state.last_author_cache_refresh = now - 400.0  # 400s atrás (fora do cooldown de 300s)
    controller.state.cached_authors = {"user@test.com": "Unknown"}

    monkeypatch.setattr(time, "time", lambda: now)

    # Mock threading
    threads_started = []

    class FakeThread:
        def __init__(self, target, daemon, name):
            self.target = target
            threads_started.append(self)

        def start(self):
            self.target()

    monkeypatch.setattr("threading.Thread", FakeThread)

    controller.notes_vm._missing_authors_result = {"user@test.com": "Refreshed Name"}

    refresh_author_names_cache_async(controller, force=False)

    # Deve ter iniciado refresh (cooldown expirou)
    assert len(threads_started) == 1
    assert controller.state.cached_authors["user@test.com"] == "Refreshed Name"


# =============================================================================
# TESTES: SMOKE / INTEGRAÇÃO
# =============================================================================


def test_smoke_full_dashboard_load_flow():
    """Smoke: fluxo completo de carregamento de dashboard."""
    controller = FakeController()
    controller.view._org_id = "org-smoke"
    controller.state.org_id = "org-smoke"

    state = MagicMock()
    state.error_message = None
    state.snapshot = {"cards": ["card1"]}
    controller.dashboard_vm._next_result = state

    load_dashboard_data_async(controller)

    assert controller.state.is_dashboard_loaded
    assert len(controller.view.updated_dashboard_states) == 1


def test_smoke_full_notes_load_flow():
    """Smoke: fluxo completo de carregamento de notas."""
    controller = FakeController()
    controller.view._org_id = "org-smoke"
    controller.state.org_id = "org-smoke"

    state = MagicMock()
    state.error_message = None
    state.notes = [{"id": 1, "body": "Test"}]
    controller.notes_vm._next_result = state

    load_notes_data_async(controller)

    assert controller.state.is_notes_loaded
    assert len(controller.state.cached_notes) == 1


def test_smoke_author_cache_refresh_flow(monkeypatch):
    """Smoke: fluxo completo de refresh de cache de autores."""
    controller = FakeController()
    controller.view._org_id = "org-smoke"
    controller.state.org_id = "org-smoke"
    controller.state.last_author_cache_refresh = 0.0
    controller.state.cached_authors = {"author@test.com": "Unknown"}

    monkeypatch.setattr(time, "time", lambda: 1000.0)

    class FakeThread:
        def __init__(self, target, daemon, name):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr("threading.Thread", FakeThread)

    controller.notes_vm._missing_authors_result = {"author@test.com": "Author Name"}

    refresh_author_names_cache_async(controller, force=True)

    assert controller.state.cached_authors["author@test.com"] == "Author Name"
    assert controller.state.last_author_cache_refresh > 0


# =============================================================================
# TESTES: MISSING COVERAGE (MF-40b)
# =============================================================================


def test_load_dashboard_data_async_no_org_id_creates_waiting_label(monkeypatch):
    """load_dashboard_data_async sem org_id cria label de aguardo (linha 62)."""
    controller = FakeController()
    controller.view._org_id = None
    controller.state.org_id = None

    # Mock dashboard_view com scroll
    fake_scroll = MagicMock()
    fake_content = MagicMock()
    fake_content.winfo_children.return_value = []
    fake_scroll.content = fake_content

    dashboard_view = FakeDashboardView()
    dashboard_view.dashboard_scroll = fake_scroll
    controller.view._dashboard_view = dashboard_view

    # Mock ttkbootstrap.Label
    fake_tb = MagicMock()
    fake_label = MagicMock()
    fake_tb.Label.return_value = fake_label
    monkeypatch.setitem(__import__("sys").modules, "ttkbootstrap", fake_tb)

    load_dashboard_data_async(controller)

    # Deve ter criado label de aguardo
    assert fake_tb.Label.called
    assert fake_label.pack.called


def test_load_notes_data_async_error_render_error_exception_handled(monkeypatch):
    """load_notes_data_async trata exceção ao renderizar erro (linhas 158-159)."""
    controller = FakeController()
    controller.view._org_id = "org-error"
    controller.state.org_id = "org-error"

    # Configurar notes_view que explode ao renderizar erro
    fake_notes_view = FakeNotesView()
    fake_notes_view.render_error = MagicMock(side_effect=RuntimeError("Render error exploded"))
    controller.view._notes_view = fake_notes_view

    # Configurar VM para levantar erro
    controller.notes_vm._should_raise = True

    load_notes_data_async(controller)

    # Não deve explodir, deve apenas logar
    assert controller.logger.error.called
    # Verificar que tentou chamar render_error
    assert fake_notes_view.render_error.called
