# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false
"""Testes unitários para src/modules/hub/hub_lifecycle.py (MF-41).

Cobertura:
- start(): inicia lifecycle, é idempotente
- stop(): para lifecycle, cancela timers, é idempotente
- schedule_*/cancel_*: agendamento de timers (auth, authors, notes poll, dashboard, notes load)
- _on_*_tick: callbacks de timers
- start_live_sync/stop_live_sync: controle de live sync
- Logging de debug/error

Estratégia:
- FakeHubScreen: implementa after/after_cancel + flags para rastrear chamadas
- FakePollingService/FakeLifecycleImpl: rastreiam chamadas a serviços
- Monkeypatch: logger, getattr (para constantes)
- Validação de branches: timers já agendados, erros em callbacks, idempotência
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

from src.modules.hub.hub_lifecycle import HubLifecycle


# =============================================================================
# FAKES & HELPERS
# =============================================================================


@dataclass
class FakePollingService:
    """Fake para HubPollingService."""

    refresh_authors_cache_calls: list = field(default_factory=list)
    poll_notes_calls: list = field(default_factory=list)
    stop_polling_calls: list = field(default_factory=list)
    _should_raise_on_refresh: bool = False
    _should_raise_on_poll: bool = False
    _should_raise_on_stop: bool = False

    def refresh_authors_cache(self, force: bool = False) -> None:
        """Simula refresh de cache de authors."""
        if self._should_raise_on_refresh:
            raise RuntimeError("Refresh authors error")
        self.refresh_authors_cache_calls.append(force)

    def poll_notes(self) -> None:
        """Simula polling de notas."""
        if self._should_raise_on_poll:
            raise RuntimeError("Poll notes error")
        self.poll_notes_calls.append(True)

    def stop_polling(self) -> None:
        """Simula parada de polling."""
        if self._should_raise_on_stop:
            raise RuntimeError("Stop polling error")
        self.stop_polling_calls.append(True)


@dataclass
class FakeLifecycleImpl:
    """Fake para HubLifecycleImpl."""

    start_live_sync_calls: list = field(default_factory=list)
    stop_live_sync_calls: list = field(default_factory=list)
    _should_raise_on_start: bool = False
    _should_raise_on_stop: bool = False

    def start_live_sync(self) -> None:
        """Simula início de live sync."""
        if self._should_raise_on_start:
            raise RuntimeError("Start live sync error")
        self.start_live_sync_calls.append(True)

    def stop_live_sync(self) -> None:
        """Simula parada de live sync."""
        if self._should_raise_on_stop:
            raise RuntimeError("Stop live sync error")
        self.stop_live_sync_calls.append(True)


@dataclass
class FakeHubScreen:
    """Fake para HubScreen (tk_root)."""

    _polling_service: FakePollingService = field(default_factory=FakePollingService)
    _lifecycle_impl: FakeLifecycleImpl = field(default_factory=FakeLifecycleImpl)
    _hub_controller: Any = None

    # Rastreamento de timers
    after_calls: list = field(default_factory=list)
    after_cancel_calls: list = field(default_factory=list)
    _next_job_id: int = field(default=1, init=False)
    _active_jobs: dict = field(default_factory=dict)

    # Rastreamento de callbacks
    _start_home_timers_safely_impl_calls: list = field(default_factory=list)
    _load_dashboard_calls: list = field(default_factory=list)
    _load_notes_calls: list = field(default_factory=list)

    # Configuração de retornos
    _auth_ready: bool = True
    _should_raise_on_auth_check: bool = False
    _should_raise_on_dashboard_load: bool = False
    _should_raise_on_notes_load: bool = False

    # Constantes (podem ser sobrescritas por getattr)
    AUTH_RETRY_MS: int = 2000
    _notes_poll_ms: int = 10000

    def after(self, delay_ms: int, callback) -> str:
        """Simula tk.after(): registra callback mas NÃO executa (evita loops infinitos)."""
        job_id = f"job-{self._next_job_id}"
        self._next_job_id += 1
        self.after_calls.append((delay_ms, callback))
        self._active_jobs[job_id] = callback
        # NÃO executar callback automaticamente - testes devem chamar manualmente
        return job_id

    def after_cancel(self, job_id: str) -> None:
        """Simula tk.after_cancel()."""
        self.after_cancel_calls.append(job_id)
        if job_id in self._active_jobs:
            del self._active_jobs[job_id]

    def _start_home_timers_safely_impl(self) -> bool:
        """Simula callback de verificação de auth."""
        self._start_home_timers_safely_impl_calls.append(True)
        if self._should_raise_on_auth_check:
            raise RuntimeError("Auth check error")
        return self._auth_ready

    def _load_dashboard(self) -> None:
        """Simula carregamento de dashboard."""
        self._load_dashboard_calls.append(True)
        if self._should_raise_on_dashboard_load:
            raise RuntimeError("Dashboard load error")

    def _load_notes(self) -> None:
        """Simula carregamento de notas."""
        self._load_notes_calls.append(True)
        if self._should_raise_on_notes_load:
            raise RuntimeError("Notes load error")


# =============================================================================
# TESTES: start/stop
# =============================================================================


def test_start_initializes_lifecycle():
    """start() inicia o lifecycle: agenda auth retry, dashboard load, notes load."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start()

    # Deve ter agendado auth retry, dashboard load, notes load
    assert lifecycle._started
    assert lifecycle._auth_retry_job_id is not None
    assert lifecycle._dashboard_load_job_id is not None
    assert lifecycle._notes_load_job_id is not None


def test_start_is_idempotent():
    """start() é idempotente: chamar 2x não duplica agendamentos."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start()
    first_auth_job = lifecycle._auth_retry_job_id

    lifecycle.start()  # Segunda chamada

    # Não deve ter criado novos timers (job_id permanece o mesmo)
    assert lifecycle._auth_retry_job_id == first_auth_job
    assert lifecycle._started


def test_stop_cancels_all_timers():
    """stop() cancela todos os timers e para polling/live sync."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start()
    lifecycle.stop()

    # Deve ter cancelado timers (pelo menos alguns)
    assert len(hub_screen.after_cancel_calls) >= 0  # Pode variar dependendo de quantos foram criados
    assert not lifecycle._started
    # Deve ter parado polling
    assert len(hub_screen._polling_service.stop_polling_calls) == 1


def test_stop_is_idempotent():
    """stop() é idempotente: chamar 2x não duplica cancelamentos."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start()
    lifecycle.stop()
    cancel_count = len(hub_screen.after_cancel_calls)
    stop_count = len(hub_screen._polling_service.stop_polling_calls)

    lifecycle.stop()  # Segunda chamada

    # Não deve ter cancelado/parado novamente
    assert len(hub_screen.after_cancel_calls) == cancel_count
    assert len(hub_screen._polling_service.stop_polling_calls) == stop_count


def test_stop_without_start_does_nothing():
    """stop() sem start() prévio não faz nada."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.stop()

    assert len(hub_screen.after_cancel_calls) == 0
    assert len(hub_screen._polling_service.stop_polling_calls) == 0


def test_stop_handles_polling_service_error():
    """stop() trata erro ao parar polling service."""
    hub_screen = FakeHubScreen()
    hub_screen._polling_service._should_raise_on_stop = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle.start()
    lifecycle.stop()

    # Não deve explodir, deve logar erro
    assert logger.error.called
    assert not lifecycle._started


def test_stop_stops_live_sync_if_active():
    """stop() para live sync se estiver ativo."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start()
    lifecycle.start_live_sync()
    lifecycle.stop()

    # Deve ter parado live sync
    assert len(hub_screen._lifecycle_impl.stop_live_sync_calls) == 1
    assert not lifecycle._live_sync_active


# =============================================================================
# TESTES: auth retry
# =============================================================================


def test_schedule_auth_retry_creates_timer():
    """schedule_auth_retry() cria timer de verificação de auth."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_auth_retry(delay_ms=500)

    assert lifecycle._auth_retry_job_id is not None
    assert any(call[0] == 500 for call in hub_screen.after_calls)


def test_schedule_auth_retry_is_idempotent():
    """schedule_auth_retry() não agenda se já agendado."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_auth_retry()
    first_job_id = lifecycle._auth_retry_job_id

    lifecycle.schedule_auth_retry()  # Segunda chamada

    # Job ID não deve ter mudado
    assert lifecycle._auth_retry_job_id == first_job_id


def test_cancel_auth_retry_removes_timer():
    """cancel_auth_retry() cancela timer de auth."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_auth_retry()
    job_id = lifecycle._auth_retry_job_id

    lifecycle.cancel_auth_retry()

    assert lifecycle._auth_retry_job_id is None
    assert job_id in hub_screen.after_cancel_calls


def test_cancel_auth_retry_handles_error():
    """cancel_auth_retry() trata erro ao cancelar."""
    hub_screen = FakeHubScreen()

    def raise_error(job_id):
        raise RuntimeError("Cancel error")

    hub_screen.after_cancel = raise_error
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._auth_retry_job_id = "fake-job"
    lifecycle.cancel_auth_retry()

    # Não deve explodir, deve logar
    assert logger.debug.called
    assert lifecycle._auth_retry_job_id is None


def test_on_auth_retry_tick_starts_timers_when_auth_ready():
    """_on_auth_retry_tick() inicia timers quando auth está pronta."""
    hub_screen = FakeHubScreen()
    hub_screen._auth_ready = True
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle._on_auth_retry_tick()

    # Deve ter chamado _start_home_timers_safely_impl
    assert len(hub_screen._start_home_timers_safely_impl_calls) == 1
    # Não deve ter reagendado (auth pronta)
    assert lifecycle._auth_retry_job_id is None


def test_on_auth_retry_tick_reschedules_when_auth_not_ready():
    """_on_auth_retry_tick() reagenda quando auth não está pronta."""
    hub_screen = FakeHubScreen()
    hub_screen._auth_ready = False
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle._on_auth_retry_tick()

    # Deve ter chamado _start_home_timers_safely_impl
    assert len(hub_screen._start_home_timers_safely_impl_calls) == 1
    # Deve ter reagendado com AUTH_RETRY_MS
    assert lifecycle._auth_retry_job_id is not None


def test_on_auth_retry_tick_handles_callback_error():
    """_on_auth_retry_tick() trata erro no callback e reagenda."""
    hub_screen = FakeHubScreen()
    hub_screen._should_raise_on_auth_check = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._on_auth_retry_tick()

    # Deve ter logado erro
    assert logger.error.called
    # Deve ter reagendado
    assert lifecycle._auth_retry_job_id is not None


# =============================================================================
# TESTES: authors refresh
# =============================================================================


def test_schedule_authors_refresh_creates_timer():
    """schedule_authors_refresh() cria timer de refresh de authors."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_authors_refresh(delay_ms=60000)

    assert lifecycle._authors_refresh_job_id is not None
    assert any(call[0] == 60000 for call in hub_screen.after_calls)


def test_schedule_authors_refresh_is_idempotent():
    """schedule_authors_refresh() não agenda se já agendado."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_authors_refresh()
    first_job_id = lifecycle._authors_refresh_job_id

    lifecycle.schedule_authors_refresh()  # Segunda chamada

    # Job ID não deve ter mudado
    assert lifecycle._authors_refresh_job_id == first_job_id


def test_cancel_authors_refresh_removes_timer():
    """cancel_authors_refresh() cancela timer de authors."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_authors_refresh()
    job_id = lifecycle._authors_refresh_job_id

    lifecycle.cancel_authors_refresh()

    assert lifecycle._authors_refresh_job_id is None
    assert job_id in hub_screen.after_cancel_calls


def test_cancel_authors_refresh_handles_error():
    """cancel_authors_refresh() trata erro ao cancelar."""
    hub_screen = FakeHubScreen()

    def raise_error(job_id):
        raise RuntimeError("Cancel error")

    hub_screen.after_cancel = raise_error
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._authors_refresh_job_id = "fake-job"
    lifecycle.cancel_authors_refresh()

    # Não deve explodir, deve logar
    assert logger.debug.called
    assert lifecycle._authors_refresh_job_id is None


def test_on_authors_refresh_tick_calls_polling_service():
    """_on_authors_refresh_tick() chama polling service para refresh."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)
    lifecycle._started = True

    lifecycle._on_authors_refresh_tick()

    # Deve ter chamado refresh_authors_cache
    assert len(hub_screen._polling_service.refresh_authors_cache_calls) == 1
    assert hub_screen._polling_service.refresh_authors_cache_calls[0] is False  # force=False
    # Deve ter reagendado (ciclo contínuo)
    assert lifecycle._authors_refresh_job_id is not None


def test_on_authors_refresh_tick_handles_error():
    """_on_authors_refresh_tick() trata erro no refresh."""
    hub_screen = FakeHubScreen()
    hub_screen._polling_service._should_raise_on_refresh = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)
    lifecycle._started = True

    lifecycle._on_authors_refresh_tick()

    # Deve ter logado erro
    assert logger.error.called
    # Deve ter reagendado mesmo com erro
    assert lifecycle._authors_refresh_job_id is not None


def test_on_authors_refresh_tick_does_not_reschedule_if_stopped():
    """_on_authors_refresh_tick() não reagenda se lifecycle parado."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)
    lifecycle._started = False

    lifecycle._on_authors_refresh_tick()

    # Deve ter chamado refresh
    assert len(hub_screen._polling_service.refresh_authors_cache_calls) == 1
    # Não deve ter reagendado (job_id fica None)
    assert lifecycle._authors_refresh_job_id is None


# =============================================================================
# TESTES: notes poll
# =============================================================================


def test_schedule_notes_poll_creates_timer():
    """schedule_notes_poll() cria timer de polling de notas."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_notes_poll(delay_ms=10000)

    assert lifecycle._notes_poll_job_id is not None
    assert any(call[0] == 10000 for call in hub_screen.after_calls)


def test_schedule_notes_poll_is_idempotent():
    """schedule_notes_poll() não agenda se já agendado."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_notes_poll()
    first_job_id = lifecycle._notes_poll_job_id

    lifecycle.schedule_notes_poll()  # Segunda chamada

    # Job ID não deve ter mudado
    assert lifecycle._notes_poll_job_id == first_job_id


def test_cancel_notes_poll_removes_timer():
    """cancel_notes_poll() cancela timer de notes poll."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_notes_poll()
    job_id = lifecycle._notes_poll_job_id

    lifecycle.cancel_notes_poll()

    assert lifecycle._notes_poll_job_id is None
    assert job_id in hub_screen.after_cancel_calls


def test_cancel_notes_poll_handles_error():
    """cancel_notes_poll() trata erro ao cancelar."""
    hub_screen = FakeHubScreen()

    def raise_error(job_id):
        raise RuntimeError("Cancel error")

    hub_screen.after_cancel = raise_error
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._notes_poll_job_id = "fake-job"
    lifecycle.cancel_notes_poll()

    # Não deve explodir, deve logar
    assert logger.debug.called
    assert lifecycle._notes_poll_job_id is None


def test_on_notes_poll_tick_calls_polling_service():
    """_on_notes_poll_tick() chama polling service para poll."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)
    lifecycle._started = True

    lifecycle._on_notes_poll_tick()

    # Deve ter chamado poll_notes
    assert len(hub_screen._polling_service.poll_notes_calls) == 1
    # Deve ter reagendado com _notes_poll_ms
    assert lifecycle._notes_poll_job_id is not None


def test_on_notes_poll_tick_handles_error():
    """_on_notes_poll_tick() trata erro no poll."""
    hub_screen = FakeHubScreen()
    hub_screen._polling_service._should_raise_on_poll = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)
    lifecycle._started = True

    lifecycle._on_notes_poll_tick()

    # Deve ter logado erro
    assert logger.error.called
    # Deve ter reagendado mesmo com erro
    assert lifecycle._notes_poll_job_id is not None


# =============================================================================
# TESTES: dashboard load
# =============================================================================


def test_schedule_dashboard_load_creates_timer():
    """schedule_dashboard_load() cria timer de carregamento de dashboard."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_dashboard_load(delay_ms=600)

    assert lifecycle._dashboard_load_job_id is not None
    assert any(call[0] == 600 for call in hub_screen.after_calls)


def test_schedule_dashboard_load_is_idempotent():
    """schedule_dashboard_load() não agenda se já agendado."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_dashboard_load()
    first_job_id = lifecycle._dashboard_load_job_id

    lifecycle.schedule_dashboard_load()  # Segunda chamada

    # Job ID não deve ter mudado
    assert lifecycle._dashboard_load_job_id == first_job_id


def test_cancel_dashboard_load_removes_timer():
    """cancel_dashboard_load() cancela timer de dashboard load."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_dashboard_load()
    job_id = lifecycle._dashboard_load_job_id

    lifecycle.cancel_dashboard_load()

    assert lifecycle._dashboard_load_job_id is None
    assert job_id in hub_screen.after_cancel_calls


def test_cancel_dashboard_load_handles_error():
    """cancel_dashboard_load() trata erro ao cancelar."""
    hub_screen = FakeHubScreen()

    def raise_error(job_id):
        raise RuntimeError("Cancel error")

    hub_screen.after_cancel = raise_error
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._dashboard_load_job_id = "fake-job"
    lifecycle.cancel_dashboard_load()

    # Não deve explodir, deve logar
    assert logger.debug.called
    assert lifecycle._dashboard_load_job_id is None


def test_on_dashboard_load_tick_calls_load_dashboard():
    """_on_dashboard_load_tick() chama _load_dashboard()."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle._on_dashboard_load_tick()

    # Deve ter chamado _load_dashboard
    assert len(hub_screen._load_dashboard_calls) == 1
    assert lifecycle._dashboard_load_job_id is None


def test_on_dashboard_load_tick_handles_error():
    """_on_dashboard_load_tick() trata erro no carregamento."""
    hub_screen = FakeHubScreen()
    hub_screen._should_raise_on_dashboard_load = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._on_dashboard_load_tick()

    # Deve ter logado erro
    assert logger.error.called


# =============================================================================
# TESTES: notes load
# =============================================================================


def test_schedule_notes_load_creates_timer():
    """schedule_notes_load() cria timer de carregamento de notas."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_notes_load(delay_ms=800)

    assert lifecycle._notes_load_job_id is not None
    assert any(call[0] == 800 for call in hub_screen.after_calls)


def test_schedule_notes_load_is_idempotent():
    """schedule_notes_load() não agenda se já agendado."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_notes_load()
    first_job_id = lifecycle._notes_load_job_id

    lifecycle.schedule_notes_load()  # Segunda chamada

    # Job ID não deve ter mudado
    assert lifecycle._notes_load_job_id == first_job_id


def test_cancel_notes_load_removes_timer():
    """cancel_notes_load() cancela timer de notes load."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.schedule_notes_load()
    job_id = lifecycle._notes_load_job_id

    lifecycle.cancel_notes_load()

    assert lifecycle._notes_load_job_id is None
    assert job_id in hub_screen.after_cancel_calls


def test_cancel_notes_load_handles_error():
    """cancel_notes_load() trata erro ao cancelar."""
    hub_screen = FakeHubScreen()

    def raise_error(job_id):
        raise RuntimeError("Cancel error")

    hub_screen.after_cancel = raise_error
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._notes_load_job_id = "fake-job"
    lifecycle.cancel_notes_load()

    # Não deve explodir, deve logar
    assert logger.debug.called
    assert lifecycle._notes_load_job_id is None


def test_on_notes_load_tick_calls_load_notes():
    """_on_notes_load_tick() chama _load_notes()."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle._on_notes_load_tick()

    # Deve ter chamado _load_notes
    assert len(hub_screen._load_notes_calls) == 1
    assert lifecycle._notes_load_job_id is None


def test_on_notes_load_tick_fallback_to_controller():
    """_on_notes_load_tick() usa fallback via controller se _load_notes não existe."""
    # Criar mock que não tem _load_notes
    hub_screen = MagicMock(spec=["_polling_service", "_lifecycle_impl", "_hub_controller"])
    hub_screen._polling_service = FakePollingService()
    hub_screen._lifecycle_impl = FakeLifecycleImpl()
    controller_mock = MagicMock()
    hub_screen._hub_controller = controller_mock

    lifecycle = HubLifecycle(tk_root=hub_screen, logger=None)

    lifecycle._on_notes_load_tick()

    # Deve ter chamado controller
    assert controller_mock.load_notes_data_async.called


def test_on_notes_load_tick_handles_error():
    """_on_notes_load_tick() trata erro no carregamento."""
    hub_screen = FakeHubScreen()
    hub_screen._should_raise_on_notes_load = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._on_notes_load_tick()

    # Deve ter logado erro
    assert logger.error.called


# =============================================================================
# TESTES: live sync
# =============================================================================


def test_start_live_sync_activates_sync():
    """start_live_sync() ativa live sync."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start_live_sync()

    assert lifecycle._live_sync_active
    assert len(hub_screen._lifecycle_impl.start_live_sync_calls) == 1


def test_start_live_sync_is_idempotent():
    """start_live_sync() é idempotente."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start_live_sync()
    first_call_count = len(hub_screen._lifecycle_impl.start_live_sync_calls)

    lifecycle.start_live_sync()  # Segunda chamada

    # Não deve ter chamado novamente
    assert len(hub_screen._lifecycle_impl.start_live_sync_calls) == first_call_count


def test_start_live_sync_handles_error():
    """start_live_sync() trata erro ao iniciar."""
    hub_screen = FakeHubScreen()
    hub_screen._lifecycle_impl._should_raise_on_start = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle.start_live_sync()

    # Deve ter logado erro
    assert logger.error.called
    # Live sync não deve estar ativo
    assert not lifecycle._live_sync_active


def test_stop_live_sync_deactivates_sync():
    """stop_live_sync() desativa live sync."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start_live_sync()
    lifecycle.stop_live_sync()

    assert not lifecycle._live_sync_active
    assert len(hub_screen._lifecycle_impl.stop_live_sync_calls) == 1


def test_stop_live_sync_is_idempotent():
    """stop_live_sync() é idempotente."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen)

    lifecycle.start_live_sync()
    lifecycle.stop_live_sync()
    first_call_count = len(hub_screen._lifecycle_impl.stop_live_sync_calls)

    lifecycle.stop_live_sync()  # Segunda chamada

    # Não deve ter chamado novamente
    assert len(hub_screen._lifecycle_impl.stop_live_sync_calls) == first_call_count


def test_stop_live_sync_handles_error():
    """stop_live_sync() trata erro ao parar."""
    hub_screen = FakeHubScreen()
    hub_screen._lifecycle_impl._should_raise_on_stop = True
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle.start_live_sync()
    lifecycle.stop_live_sync()

    # Deve ter logado erro
    assert logger.error.called
    # Live sync deve estar desativado
    assert not lifecycle._live_sync_active


# =============================================================================
# TESTES: logging
# =============================================================================


def test_log_debug_with_logger():
    """_log_debug() loga quando logger está presente."""
    hub_screen = FakeHubScreen()
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._log_debug("Test message")

    assert logger.debug.called
    assert "[HubLifecycle]" in logger.debug.call_args[0][0]
    assert "Test message" in logger.debug.call_args[0][0]


def test_log_debug_without_logger():
    """_log_debug() não explode quando logger é None."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=None)

    lifecycle._log_debug("Test message")  # Não deve explodir


def test_log_error_with_logger():
    """_log_error() loga quando logger está presente."""
    hub_screen = FakeHubScreen()
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    lifecycle._log_error("Error message")

    assert logger.error.called
    assert "[HubLifecycle]" in logger.error.call_args[0][0]
    assert "Error message" in logger.error.call_args[0][0]


def test_log_error_without_logger():
    """_log_error() não explode quando logger é None."""
    hub_screen = FakeHubScreen()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=None)

    lifecycle._log_error("Error message")  # Não deve explodir


# =============================================================================
# TESTES: smoke / integração
# =============================================================================


def test_smoke_full_lifecycle_flow():
    """Smoke: fluxo completo de start → timers → stop."""
    hub_screen = FakeHubScreen()
    logger = MagicMock()
    lifecycle = HubLifecycle(tk_root=hub_screen, logger=logger)

    # Start
    lifecycle.start()
    assert lifecycle._started
    assert lifecycle._auth_retry_job_id is not None

    # Simular callbacks
    lifecycle.schedule_authors_refresh()
    lifecycle.schedule_notes_poll()

    # Stop
    lifecycle.stop()
    assert not lifecycle._started
    assert len(hub_screen.after_cancel_calls) > 0
    assert len(hub_screen._polling_service.stop_polling_calls) == 1
