# -*- coding: utf-8 -*-
"""MF-65: Testes headless para hub_lifecycle_facade.py.

Testa HubLifecycleFacade com mocks, sem dependências reais.
Meta: 100% coverage (statements + branches).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_lifecycle_manager() -> MagicMock:
    """Mock do HubLifecycleManager."""
    return MagicMock()


@pytest.fixture
def mock_lifecycle_impl() -> MagicMock:
    """Mock do HubLifecycleImpl."""
    return MagicMock()


@pytest.fixture
def mock_polling_service() -> MagicMock:
    """Mock do HubPollingService."""
    return MagicMock()


@pytest.fixture
def mock_state_manager() -> MagicMock:
    """Mock do HubStateManager."""
    return MagicMock()


@pytest.fixture
def mock_callbacks() -> dict[str, MagicMock]:
    """Callbacks mock."""
    return {
        "auth_ready": MagicMock(return_value=True),
        "get_org_id": MagicMock(return_value="org-123"),
        "get_email": MagicMock(return_value="user@example.com"),
        "start_live_sync": MagicMock(),
        "render_notes": MagicMock(),
        "refresh_author_cache": MagicMock(),
        "clear_author_cache": MagicMock(),
    }


@pytest.fixture
def mock_parent() -> SimpleNamespace:
    """Parent mock (HubScreen) com atributos necessários."""
    notes_history = MagicMock()
    notes_history.index.return_value = "1.0"  # Histórico vazio

    state = SimpleNamespace(notes_last_data=[{"id": 1, "text": "Test note"}])

    parent = SimpleNamespace(
        notes_history=notes_history,
        state=state,
        _last_org_for_names=None,
    )
    return parent


@pytest.fixture
def facade(
    mock_parent: SimpleNamespace,
    mock_lifecycle_manager: MagicMock,
    mock_lifecycle_impl: MagicMock,
    mock_polling_service: MagicMock,
    mock_state_manager: MagicMock,
    mock_callbacks: dict[str, MagicMock],
) -> Any:
    """Facade com todas as dependências mock."""
    from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

    return HubLifecycleFacade(
        parent=mock_parent,
        lifecycle_manager=mock_lifecycle_manager,
        lifecycle_impl=mock_lifecycle_impl,
        polling_service=mock_polling_service,
        state_manager=mock_state_manager,
        auth_ready_callback=mock_callbacks["auth_ready"],
        get_org_id=mock_callbacks["get_org_id"],
        get_email=mock_callbacks["get_email"],
        start_live_sync_callback=mock_callbacks["start_live_sync"],
        render_notes_callback=mock_callbacks["render_notes"],
        refresh_author_cache_callback=mock_callbacks["refresh_author_cache"],
        clear_author_cache_callback=mock_callbacks["clear_author_cache"],
        debug_logger=None,
    )


# =============================================================================
# TEST: __init__
# =============================================================================


class TestInit:
    """Testes de inicialização."""

    def test_init_stores_all_dependencies(
        self,
        mock_parent: SimpleNamespace,
        mock_lifecycle_manager: MagicMock,
        mock_lifecycle_impl: MagicMock,
        mock_polling_service: MagicMock,
        mock_state_manager: MagicMock,
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """__init__ armazena todas as dependências corretamente."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=mock_lifecycle_manager,
            lifecycle_impl=mock_lifecycle_impl,
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            auth_ready_callback=mock_callbacks["auth_ready"],
            get_org_id=mock_callbacks["get_org_id"],
            get_email=mock_callbacks["get_email"],
            start_live_sync_callback=mock_callbacks["start_live_sync"],
            render_notes_callback=mock_callbacks["render_notes"],
            refresh_author_cache_callback=mock_callbacks["refresh_author_cache"],
            clear_author_cache_callback=mock_callbacks["clear_author_cache"],
            debug_logger=debug_logger,
        )

        assert facade._parent is mock_parent
        assert facade._lifecycle_manager is mock_lifecycle_manager
        assert facade._lifecycle_impl is mock_lifecycle_impl
        assert facade._polling_service is mock_polling_service
        assert facade._state_manager is mock_state_manager
        assert facade._auth_ready_callback is mock_callbacks["auth_ready"]
        assert facade._get_org_id is mock_callbacks["get_org_id"]
        assert facade._get_email is mock_callbacks["get_email"]
        assert facade._start_live_sync_callback is mock_callbacks["start_live_sync"]
        assert facade._render_notes_callback is mock_callbacks["render_notes"]
        assert facade._refresh_author_cache_callback is mock_callbacks["refresh_author_cache"]
        assert facade._clear_author_cache_callback is mock_callbacks["clear_author_cache"]
        assert facade._debug_logger is debug_logger


# =============================================================================
# TEST: start_live_sync_impl
# =============================================================================


class TestStartLiveSyncImpl:
    """Testes de start_live_sync_impl."""

    def test_start_live_sync_impl_calls_lifecycle_impl(self, facade: Any, mock_lifecycle_impl: MagicMock) -> None:
        """start_live_sync_impl() chama lifecycle_impl.start_live_sync()."""
        facade.start_live_sync_impl()

        mock_lifecycle_impl.start_live_sync.assert_called_once()

    def test_start_live_sync_impl_catches_exception(self, facade: Any, mock_lifecycle_impl: MagicMock) -> None:
        """start_live_sync_impl() captura exceção e loga."""
        mock_lifecycle_impl.start_live_sync.side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.start_live_sync_impl()

        mock_lifecycle_impl.start_live_sync.assert_called_once()

    def test_start_live_sync_impl_logs_with_debug_logger(
        self, mock_lifecycle_impl: MagicMock, mock_parent: SimpleNamespace
    ) -> None:
        """start_live_sync_impl() loga com debug_logger quando disponível."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        mock_lifecycle_impl.start_live_sync.side_effect = RuntimeError("Test error")

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,
            lifecycle_impl=mock_lifecycle_impl,
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.start_live_sync_impl()

        # Verifica que debug_logger foi chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("erro" in args.lower() for args in call_args_list)


# =============================================================================
# TEST: stop_live_sync_impl
# =============================================================================


class TestStopLiveSyncImpl:
    """Testes de stop_live_sync_impl."""

    def test_stop_live_sync_impl_calls_lifecycle_impl(self, facade: Any, mock_lifecycle_impl: MagicMock) -> None:
        """stop_live_sync_impl() chama lifecycle_impl.stop_live_sync()."""
        facade.stop_live_sync_impl()

        mock_lifecycle_impl.stop_live_sync.assert_called_once()

    def test_stop_live_sync_impl_catches_exception(self, facade: Any, mock_lifecycle_impl: MagicMock) -> None:
        """stop_live_sync_impl() captura exceção e loga."""
        mock_lifecycle_impl.stop_live_sync.side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.stop_live_sync_impl()

        mock_lifecycle_impl.stop_live_sync.assert_called_once()

    def test_stop_live_sync_impl_logs_with_debug_logger(
        self, mock_lifecycle_impl: MagicMock, mock_parent: SimpleNamespace
    ) -> None:
        """stop_live_sync_impl() loga com debug_logger quando disponível."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        mock_lifecycle_impl.stop_live_sync.side_effect = RuntimeError("Test error")

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,
            lifecycle_impl=mock_lifecycle_impl,
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.stop_live_sync_impl()

        # Verifica que debug_logger foi chamado
        assert debug_logger.call_count >= 1


# =============================================================================
# TEST: start_live_sync (alias)
# =============================================================================


class TestStartLiveSync:
    """Testes de start_live_sync (alias)."""

    def test_start_live_sync_calls_impl(self, facade: Any, mock_lifecycle_impl: MagicMock) -> None:
        """start_live_sync() é alias de start_live_sync_impl()."""
        facade.start_live_sync()

        mock_lifecycle_impl.start_live_sync.assert_called_once()


# =============================================================================
# TEST: start_polling
# =============================================================================


class TestStartPolling:
    """Testes de start_polling."""

    def test_start_polling_activates_and_starts_manager(
        self,
        facade: Any,
        mock_state_manager: MagicMock,
        mock_lifecycle_manager: MagicMock,
    ) -> None:
        """start_polling() ativa polling e inicia lifecycle_manager."""
        facade.start_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(True)
        mock_lifecycle_manager.start.assert_called_once()

    def test_start_polling_with_none_lifecycle_manager(
        self, mock_parent: SimpleNamespace, mock_state_manager: MagicMock
    ) -> None:
        """start_polling() não explode quando lifecycle_manager é None."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=mock_state_manager,
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=None,
        )

        # Não deve lançar exceção
        facade.start_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(True)

    def test_start_polling_catches_exception(self, facade: Any, mock_state_manager: MagicMock) -> None:
        """start_polling() captura exceção e loga."""
        mock_state_manager.set_polling_active.side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.start_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(True)

    def test_start_polling_logs_debug(self, mock_parent: SimpleNamespace) -> None:
        """start_polling() loga debug quando polling inicia."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.start_polling()

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1

    def test_start_polling_logs_error_with_debug_logger(
        self, mock_parent: SimpleNamespace, mock_state_manager: MagicMock
    ) -> None:
        """start_polling() loga erro com debug_logger quando há exceção."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        mock_state_manager.set_polling_active.side_effect = RuntimeError("Test error")

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=mock_state_manager,
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.start_polling()

        # Debug_logger deve ter sido chamado no bloco de exceção
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("erro" in args.lower() for args in call_args_list)


# =============================================================================
# TEST: stop_polling
# =============================================================================


class TestStopPolling:
    """Testes de stop_polling."""

    def test_stop_polling_deactivates_and_stops_manager(
        self,
        facade: Any,
        mock_state_manager: MagicMock,
        mock_lifecycle_manager: MagicMock,
    ) -> None:
        """stop_polling() desativa polling e para lifecycle_manager."""
        facade.stop_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(False)
        mock_lifecycle_manager.stop.assert_called_once()

    def test_stop_polling_with_none_lifecycle_manager(
        self, mock_parent: SimpleNamespace, mock_state_manager: MagicMock
    ) -> None:
        """stop_polling() não explode quando lifecycle_manager é None."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=mock_state_manager,
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=None,
        )

        # Não deve lançar exceção
        facade.stop_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(False)

    def test_stop_polling_catches_exception(self, facade: Any, mock_state_manager: MagicMock) -> None:
        """stop_polling() captura exceção e loga."""
        mock_state_manager.set_polling_active.side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.stop_polling()

        mock_state_manager.set_polling_active.assert_called_once_with(False)

    def test_stop_polling_logs_debug(self, mock_parent: SimpleNamespace) -> None:
        """stop_polling() loga debug quando polling para."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.stop_polling()

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1

    def test_stop_polling_logs_error_with_debug_logger(
        self, mock_parent: SimpleNamespace, mock_state_manager: MagicMock
    ) -> None:
        """stop_polling() loga erro com debug_logger quando há exceção."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        mock_state_manager.set_polling_active.side_effect = RuntimeError("Test error")

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=mock_state_manager,
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.stop_polling()

        # Debug_logger deve ter sido chamado no bloco de exceção
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("erro" in args.lower() for args in call_args_list)


# =============================================================================
# TEST: start_timers
# =============================================================================


class TestStartTimers:
    """Testes de start_timers."""

    def test_start_timers_starts_lifecycle_manager(self, facade: Any, mock_lifecycle_manager: MagicMock) -> None:
        """start_timers() chama lifecycle_manager.start()."""
        facade.start_timers()

        mock_lifecycle_manager.start.assert_called_once()

    def test_start_timers_with_none_lifecycle_manager(self, mock_parent: SimpleNamespace) -> None:
        """start_timers() não explode quando lifecycle_manager é None."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=None,
        )

        # Não deve lançar exceção
        facade.start_timers()

    def test_start_timers_catches_exception(self, facade: Any, mock_lifecycle_manager: MagicMock) -> None:
        """start_timers() captura exceção e loga."""
        mock_lifecycle_manager.start.side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.start_timers()

        mock_lifecycle_manager.start.assert_called_once()

    def test_start_timers_logs_debug(self, mock_parent: SimpleNamespace) -> None:
        """start_timers() loga debug quando timers iniciam."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.start_timers()

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1

    def test_start_timers_logs_error_with_debug_logger(
        self, mock_parent: SimpleNamespace, mock_lifecycle_manager: MagicMock
    ) -> None:
        """start_timers() loga erro com debug_logger quando há exceção."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        mock_lifecycle_manager.start.side_effect = RuntimeError("Test error")

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=mock_lifecycle_manager,
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.start_timers()

        # Debug_logger deve ter sido chamado no bloco de exceção
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("erro" in args.lower() for args in call_args_list)


# =============================================================================
# TEST: schedule_poll
# =============================================================================


class TestSchedulePoll:
    """Testes de schedule_poll."""

    def test_schedule_poll_calls_polling_service(self, facade: Any, mock_polling_service: MagicMock) -> None:
        """schedule_poll() chama polling_service.schedule_next_poll()."""
        facade.schedule_poll(delay_ms=5000)

        mock_polling_service.schedule_next_poll.assert_called_once_with(delay_ms=5000)

    def test_schedule_poll_default_delay(self, facade: Any, mock_polling_service: MagicMock) -> None:
        """schedule_poll() usa delay padrão de 6000ms."""
        facade.schedule_poll()

        mock_polling_service.schedule_next_poll.assert_called_once_with(delay_ms=6000)

    def test_schedule_poll_catches_exception(self, facade: Any, mock_polling_service: MagicMock) -> None:
        """schedule_poll() captura exceção e loga."""
        mock_polling_service.schedule_next_poll.side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.schedule_poll()

        mock_polling_service.schedule_next_poll.assert_called_once()

    def test_schedule_poll_logs_debug(self, mock_parent: SimpleNamespace) -> None:
        """schedule_poll() loga debug quando polling agendado."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.schedule_poll(delay_ms=5000)

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1

    def test_schedule_poll_logs_error_with_debug_logger(
        self, mock_parent: SimpleNamespace, mock_polling_service: MagicMock
    ) -> None:
        """schedule_poll() loga erro com debug_logger quando há exceção."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        mock_polling_service.schedule_next_poll.side_effect = RuntimeError("Test error")

        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=MagicMock(),
            lifecycle_impl=MagicMock(),
            polling_service=mock_polling_service,
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade.schedule_poll()

        # Debug_logger deve ter sido chamado no bloco de exceção
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("erro" in args.lower() for args in call_args_list)


# =============================================================================
# TEST: on_show
# =============================================================================


class TestOnShow:
    """Testes de on_show."""

    def test_on_show_starts_live_sync(self, facade: Any, mock_callbacks: dict[str, MagicMock]) -> None:
        """on_show() inicia live sync."""
        facade.on_show()

        mock_callbacks["start_live_sync"].assert_called_once()

    def test_on_show_renders_notes_when_history_empty(
        self,
        facade: Any,
        mock_parent: SimpleNamespace,
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """on_show() renderiza notas quando histórico está vazio."""
        facade.on_show()

        # Verifica que render_notes foi chamado com state.notes_last_data
        mock_callbacks["render_notes"].assert_called_once_with(mock_parent.state.notes_last_data, True)

    def test_on_show_does_not_render_when_history_not_empty(
        self,
        facade: Any,
        mock_parent: SimpleNamespace,
        mock_callbacks: dict[str, MagicMock],
    ) -> None:
        """on_show() não renderiza quando histórico não está vazio."""
        # Simula histórico não vazio
        mock_parent.notes_history.index.return_value = "5.0"

        facade.on_show()

        # Verifica que render_notes NÃO foi chamado
        mock_callbacks["render_notes"].assert_not_called()

    def test_on_show_handles_notes_history_none(
        self, facade: Any, mock_parent: SimpleNamespace, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """on_show() não explode quando notes_history é None."""
        # Remove notes_history
        delattr(mock_parent, "notes_history")

        # Não deve lançar exceção
        facade.on_show()

        # Live sync deve ter sido iniciado
        mock_callbacks["start_live_sync"].assert_called_once()

    def test_on_show_handles_state_none(
        self, facade: Any, mock_parent: SimpleNamespace, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """on_show() não explode quando state é None."""
        # Remove state
        delattr(mock_parent, "state")

        # Não deve lançar exceção
        facade.on_show()

        # Live sync deve ter sido iniciado
        mock_callbacks["start_live_sync"].assert_called_once()
        # Render notes não deve ter sido chamado (sem state)
        mock_callbacks["render_notes"].assert_not_called()

    def test_on_show_handles_notes_last_data_empty(
        self, facade: Any, mock_parent: SimpleNamespace, mock_callbacks: dict[str, MagicMock]
    ) -> None:
        """on_show() não renderiza quando notes_last_data está vazio."""
        # State com notes_last_data vazio
        mock_parent.state.notes_last_data = []

        facade.on_show()

        # Render notes não deve ter sido chamado
        mock_callbacks["render_notes"].assert_not_called()

    def test_on_show_clears_and_refreshes_author_cache(self, facade: Any, mock_callbacks: dict[str, MagicMock]) -> None:
        """on_show() limpa e atualiza cache de autores."""
        facade.on_show()

        mock_callbacks["clear_author_cache"].assert_called_once()
        mock_callbacks["refresh_author_cache"].assert_called_once_with(True)

    def test_on_show_resets_last_org_for_names(self, facade: Any, mock_parent: SimpleNamespace) -> None:
        """on_show() reseta _last_org_for_names."""
        mock_parent._last_org_for_names = "org-123"

        facade.on_show()

        assert mock_parent._last_org_for_names is None

    def test_on_show_handles_missing_last_org_for_names(self, facade: Any, mock_parent: SimpleNamespace) -> None:
        """on_show() não explode quando _last_org_for_names não existe."""
        # Remove _last_org_for_names
        delattr(mock_parent, "_last_org_for_names")

        # Não deve lançar exceção
        facade.on_show()

    def test_on_show_catches_start_live_sync_exception(self, facade: Any, mock_callbacks: dict[str, MagicMock]) -> None:
        """on_show() captura exceção de start_live_sync."""
        mock_callbacks["start_live_sync"].side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.on_show()

        mock_callbacks["start_live_sync"].assert_called_once()

    def test_on_show_catches_render_notes_exception(self, facade: Any, mock_callbacks: dict[str, MagicMock]) -> None:
        """on_show() captura exceção de render_notes."""
        mock_callbacks["render_notes"].side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.on_show()

        mock_callbacks["render_notes"].assert_called_once()

    def test_on_show_catches_clear_cache_exception(self, facade: Any, mock_callbacks: dict[str, MagicMock]) -> None:
        """on_show() captura exceção de clear_author_cache."""
        mock_callbacks["clear_author_cache"].side_effect = RuntimeError("Test error")

        # Não deve propagar exceção
        facade.on_show()

        mock_callbacks["clear_author_cache"].assert_called_once()

    def test_on_show_catches_index_exception(self, facade: Any, mock_parent: SimpleNamespace) -> None:
        """on_show() captura exceção de notes_history.index()."""
        mock_parent.notes_history.index.side_effect = RuntimeError("Index error")

        # Não deve propagar exceção (assume histórico vazio)
        facade.on_show()


# =============================================================================
# TEST: _log_debug
# =============================================================================


class TestLogDebugPrivateMethod:
    """Testes do método privado _log_debug."""

    def test_log_debug_with_debug_logger_calls_it(self, mock_parent: SimpleNamespace) -> None:
        """_log_debug() chama debug_logger quando ele existe."""
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        debug_logger = MagicMock()
        facade = HubLifecycleFacade(
            parent=mock_parent,
            lifecycle_manager=None,
            lifecycle_impl=MagicMock(),
            polling_service=MagicMock(),
            state_manager=MagicMock(),
            auth_ready_callback=MagicMock(),
            get_org_id=MagicMock(),
            get_email=MagicMock(),
            start_live_sync_callback=MagicMock(),
            render_notes_callback=MagicMock(),
            refresh_author_cache_callback=MagicMock(),
            clear_author_cache_callback=MagicMock(),
            debug_logger=debug_logger,
        )

        facade._log_debug("Test message")

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count == 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Test message" in args for args in call_args_list)

    def test_log_debug_without_debug_logger_does_not_crash(self, facade: Any) -> None:
        """_log_debug() não explode quando debug_logger é None."""
        # Não deve lançar exceção
        facade._log_debug("Test message")
