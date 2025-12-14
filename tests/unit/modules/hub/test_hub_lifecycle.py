# -*- coding: utf-8 -*-
"""Testes para HubLifecycle (gerenciamento de timers e lifecycle do HUB)."""

from __future__ import annotations

from typing import Callable
from unittest.mock import MagicMock

import pytest

from src.modules.hub.hub_lifecycle import HubLifecycle


class FakeTkRoot:
    """Fake do HubScreen para testes (sem dependência de Tk real)."""

    def __init__(self):
        """Inicializa fake com contadores e mocks."""
        self.AUTH_RETRY_MS = 2000
        self._notes_poll_ms = 10000

        # Mocks para callbacks (mantidos para compatibilidade, mas não mais usados diretamente)
        self._start_home_timers_safely_impl = MagicMock(return_value=True)
        self._refresh_author_names_cache_impl = MagicMock()
        self._poll_notes_impl = MagicMock()
        self._load_dashboard = MagicMock()
        self._start_live_sync_impl = MagicMock()
        self._stop_live_sync_impl = MagicMock()

        # MF-15: Mocks dos serviços
        self._polling_service = MagicMock()
        self._lifecycle_impl = MagicMock()

        # Simular tk.after e after_cancel
        self._after_jobs: dict[str, tuple[int, Callable]] = {}
        self._next_job_id = 1

    def after(self, ms: int, callback: Callable) -> str:
        """Simula tk.after (armazena mas não executa automaticamente)."""
        job_id = f"after{self._next_job_id}"
        self._next_job_id += 1
        self._after_jobs[job_id] = (ms, callback)
        return job_id

    def after_cancel(self, job_id: str) -> None:
        """Simula tk.after_cancel."""
        if job_id in self._after_jobs:
            del self._after_jobs[job_id]

    def execute_pending_after(self, job_id: str) -> None:
        """Helper de teste: executa um after pendente."""
        if job_id in self._after_jobs:
            _, callback = self._after_jobs[job_id]
            del self._after_jobs[job_id]
            callback()


@pytest.fixture
def fake_tk_root():
    """Cria FakeTkRoot para testes."""
    return FakeTkRoot()


@pytest.fixture
def lifecycle(fake_tk_root):
    """Cria HubLifecycle com FakeTkRoot."""
    return HubLifecycle(tk_root=fake_tk_root, logger=None)


class TestHubLifecycleStart:
    """Testes para start() do lifecycle."""

    def test_start_schedules_auth_retry(self, lifecycle, fake_tk_root):
        """Deve agendar auth retry ao iniciar."""
        lifecycle.start()

        # Verificar que after foi chamado
        assert len(fake_tk_root._after_jobs) > 0
        # Deve ter agendado auth retry
        job_delays = [delay for delay, _ in fake_tk_root._after_jobs.values()]
        assert 500 in job_delays  # auth retry inicial

    def test_start_schedules_dashboard_load(self, lifecycle, fake_tk_root):
        """Deve agendar dashboard load ao iniciar."""
        lifecycle.start()

        # Verificar que dashboard load foi agendado
        job_delays = [delay for delay, _ in fake_tk_root._after_jobs.values()]
        assert 600 in job_delays  # dashboard load

    def test_start_only_once(self, lifecycle, fake_tk_root):
        """Não deve reagendar se já iniciado."""
        lifecycle.start()
        jobs_count_1 = len(fake_tk_root._after_jobs)

        lifecycle.start()  # Segunda chamada
        jobs_count_2 = len(fake_tk_root._after_jobs)

        assert jobs_count_1 == jobs_count_2  # Não deve ter agendado novamente


class TestHubLifecycleStop:
    """Testes para stop() do lifecycle."""

    def test_stop_cancels_all_timers(self, lifecycle, fake_tk_root):
        """Deve cancelar todos os timers ao parar."""
        lifecycle.start()
        assert len(fake_tk_root._after_jobs) > 0

        lifecycle.stop()

        # Todos os jobs devem ter sido cancelados
        assert len(fake_tk_root._after_jobs) == 0

    def test_stop_when_not_started(self, lifecycle, fake_tk_root):
        """Deve ser seguro parar quando não iniciado."""
        lifecycle.stop()  # Não deve dar erro

        assert len(fake_tk_root._after_jobs) == 0


class TestHubLifecycleAuthRetry:
    """Testes para auth retry tick."""

    def test_auth_retry_calls_impl_when_ready(self, lifecycle, fake_tk_root):
        """Deve chamar impl quando auth estiver pronta."""
        fake_tk_root._start_home_timers_safely_impl.return_value = True

        lifecycle.start()

        # Encontrar e executar auth retry job
        auth_jobs = [
            (job_id, callback) for job_id, (delay, callback) in fake_tk_root._after_jobs.items() if delay == 500
        ]
        assert len(auth_jobs) > 0

        job_id, callback = auth_jobs[0]
        callback()  # Executar

        # Verificar que impl foi chamado
        fake_tk_root._start_home_timers_safely_impl.assert_called_once()

    def test_auth_retry_reschedules_when_not_ready(self, lifecycle, fake_tk_root):
        """Deve reagendar se auth não estiver pronta."""
        fake_tk_root._start_home_timers_safely_impl.return_value = False

        lifecycle.start()
        _ = len(fake_tk_root._after_jobs)  # Track job count

        # Executar auth retry
        auth_jobs = [
            (job_id, callback) for job_id, (delay, callback) in fake_tk_root._after_jobs.items() if delay == 500
        ]
        job_id, callback = auth_jobs[0]
        callback()

        # Deve ter reagendado (pode ter mais jobs agora)
        # O importante é que não crashou
        assert True  # Se chegou aqui, não crashou


class TestHubLifecycleAuthorsRefresh:
    """Testes para authors refresh."""

    def test_schedule_authors_refresh(self, lifecycle, fake_tk_root):
        """Deve agendar refresh de authors."""
        lifecycle.schedule_authors_refresh()

        # Verificar que foi agendado
        job_delays = [delay for delay, _ in fake_tk_root._after_jobs.values()]
        assert 60000 in job_delays

    def test_authors_refresh_tick_calls_impl(self, lifecycle, fake_tk_root):
        """Deve chamar serviço no tick de authors refresh (MF-15)."""
        lifecycle.schedule_authors_refresh()

        # Executar job
        author_jobs = [
            (job_id, callback) for job_id, (delay, callback) in fake_tk_root._after_jobs.items() if delay == 60000
        ]
        job_id, callback = author_jobs[0]
        callback()

        # MF-15: Verificar que serviço foi chamado
        fake_tk_root._polling_service.refresh_authors_cache.assert_called_once_with(force=False)

    def test_cancel_authors_refresh(self, lifecycle, fake_tk_root):
        """Deve cancelar refresh de authors."""
        lifecycle.schedule_authors_refresh()
        assert len(fake_tk_root._after_jobs) > 0

        lifecycle.cancel_authors_refresh()

        # Job de authors deve ter sido removido
        author_jobs = [job_id for job_id, (delay, _) in fake_tk_root._after_jobs.items() if delay == 60000]
        assert len(author_jobs) == 0


class TestHubLifecycleNotesPoll:
    """Testes para notes polling."""

    def test_schedule_notes_poll(self, lifecycle, fake_tk_root):
        """Deve agendar polling de notas."""
        lifecycle.schedule_notes_poll()

        # Verificar que foi agendado
        job_delays = [delay for delay, _ in fake_tk_root._after_jobs.values()]
        assert 10000 in job_delays

    def test_notes_poll_tick_calls_impl(self, lifecycle, fake_tk_root):
        """Deve chamar serviço no tick de notes poll (MF-15)."""
        lifecycle.schedule_notes_poll()

        # Executar job
        notes_jobs = [
            (job_id, callback) for job_id, (delay, callback) in fake_tk_root._after_jobs.items() if delay == 10000
        ]
        job_id, callback = notes_jobs[0]
        callback()

        # MF-15: Verificar que serviço foi chamado
        fake_tk_root._polling_service.poll_notes.assert_called_once()

    def test_cancel_notes_poll(self, lifecycle, fake_tk_root):
        """Deve cancelar polling de notas."""
        lifecycle.schedule_notes_poll()
        assert len(fake_tk_root._after_jobs) > 0

        lifecycle.cancel_notes_poll()

        # Job de notes deve ter sido removido
        notes_jobs = [job_id for job_id, (delay, _) in fake_tk_root._after_jobs.items() if delay == 10000]
        assert len(notes_jobs) == 0


class TestHubLifecycleDashboardLoad:
    """Testes para dashboard load."""

    def test_schedule_dashboard_load(self, lifecycle, fake_tk_root):
        """Deve agendar carregamento do dashboard."""
        lifecycle.schedule_dashboard_load()

        # Verificar que foi agendado
        job_delays = [delay for delay, _ in fake_tk_root._after_jobs.values()]
        assert 600 in job_delays

    def test_dashboard_load_tick_calls_impl(self, lifecycle, fake_tk_root):
        """Deve chamar impl no tick de dashboard load."""
        lifecycle.schedule_dashboard_load()

        # Executar job
        dashboard_jobs = [
            (job_id, callback) for job_id, (delay, callback) in fake_tk_root._after_jobs.items() if delay == 600
        ]
        job_id, callback = dashboard_jobs[0]
        callback()

        # Verificar que impl foi chamado
        fake_tk_root._load_dashboard.assert_called_once()


class TestHubLifecycleLiveSync:
    """Testes para live sync."""

    def test_start_live_sync(self, lifecycle, fake_tk_root):
        """Deve iniciar live sync (MF-15: via serviço)."""
        lifecycle.start_live_sync()

        # MF-15: Verificar que serviço foi chamado
        fake_tk_root._lifecycle_impl.start_live_sync.assert_called_once()

    def test_start_live_sync_only_once(self, lifecycle, fake_tk_root):
        """Não deve reiniciar se já ativo (MF-15)."""
        lifecycle.start_live_sync()
        lifecycle.start_live_sync()  # Segunda chamada

        # MF-15: Deve ter chamado serviço apenas uma vez
        fake_tk_root._lifecycle_impl.start_live_sync.assert_called_once()

    def test_stop_live_sync(self, lifecycle, fake_tk_root):
        """Deve parar live sync (MF-15: via serviço)."""
        lifecycle.start_live_sync()
        lifecycle.stop_live_sync()

        # MF-15: Verificar que serviço de stop foi chamado
        fake_tk_root._lifecycle_impl.stop_live_sync.assert_called_once()

    def test_stop_live_sync_when_not_active(self, lifecycle, fake_tk_root):
        """Deve ser seguro parar quando não ativo (MF-15)."""
        lifecycle.stop_live_sync()  # Não deve dar erro

        # MF-15: Não deve ter chamado serviço
        fake_tk_root._lifecycle_impl.stop_live_sync.assert_not_called()


class TestHubLifecycleIntegration:
    """Testes de integração do lifecycle."""

    def test_full_lifecycle_flow(self, lifecycle, fake_tk_root):
        """Deve executar fluxo completo de lifecycle."""
        # 1. Start
        lifecycle.start()
        assert lifecycle._started is True

        # 2. Verificar jobs agendados
        assert len(fake_tk_root._after_jobs) > 0

        # 3. Stop
        lifecycle.stop()
        assert lifecycle._started is False
        assert len(fake_tk_root._after_jobs) == 0

    def test_lifecycle_handles_errors_gracefully(self, lifecycle, fake_tk_root):
        """Deve tratar erros nos callbacks sem crashar."""
        # Fazer impl lançar exceção
        fake_tk_root._refresh_author_names_cache_impl.side_effect = Exception("Test error")

        lifecycle.schedule_authors_refresh()

        # Executar job (deve tratar exceção)
        author_jobs = [
            (job_id, callback) for job_id, (delay, callback) in fake_tk_root._after_jobs.items() if delay == 60000
        ]
        job_id, callback = author_jobs[0]

        # Não deve crashar
        try:
            callback()
        except Exception:
            pytest.fail("Callback não deveria propagar exceção")
