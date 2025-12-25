# -*- coding: utf-8 -*-
"""Testes unitários para MainWindowPollers (headless, sem Tkinter real).

Estratégia:
- FakeScheduler simula Tk.after/after_cancel
- Valida agendamento, cancelamento e reagendamento
- Garante robustez a exceções nos callbacks
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pytest

from src.modules.main_window.controllers.main_window_pollers import MainWindowPollers


class FakeScheduler:
    """Scheduler headless para testes (simula Tk.after/after_cancel)."""

    def __init__(self) -> None:
        self._job_counter = 0
        self.scheduled_jobs: dict[str, tuple[int, Callable[[], None]]] = {}
        self.canceled_jobs: list[str] = []

    def after(self, ms: int, func: Callable[[], None]) -> str:
        """Agenda job e retorna ID único."""
        self._job_counter += 1
        job_id = f"job_{self._job_counter}"
        self.scheduled_jobs[job_id] = (ms, func)
        return job_id

    def after_cancel(self, after_id: str) -> None:
        """Cancela job (registra na lista de cancelamentos)."""
        self.canceled_jobs.append(after_id)
        if after_id in self.scheduled_jobs:
            del self.scheduled_jobs[after_id]

    def execute_job(self, job_id: str) -> None:
        """Executa callback de um job manualmente (para testes)."""
        if job_id in self.scheduled_jobs:
            _, func = self.scheduled_jobs[job_id]
            func()


# ===== Fixtures =====


@pytest.fixture
def fake_scheduler() -> FakeScheduler:
    """Retorna scheduler fake para testes."""
    return FakeScheduler()


@pytest.fixture
def mock_callbacks() -> dict[str, Callable[[], None]]:
    """Retorna dict com callbacks mock (rastreiam chamadas)."""
    calls: dict[str, list[Any]] = {
        "notifications": [],
        "health": [],
        "status": [],
    }

    def make_callback(name: str) -> Callable[[], None]:
        def callback() -> None:
            calls[name].append(True)

        return callback

    return {
        "on_poll_notifications": make_callback("notifications"),
        "on_poll_health": make_callback("health"),
        "on_refresh_status": make_callback("status"),
        "calls": calls,  # type: ignore[dict-item]
    }


# ===== Testes =====


def test_start_schedules_all_three_jobs_with_correct_delays(
    fake_scheduler: FakeScheduler,
    mock_callbacks: dict[str, Callable[[], None]],
) -> None:
    """start() deve agendar 3 jobs com delays iniciais corretos."""
    pollers = MainWindowPollers(
        fake_scheduler,
        on_poll_notifications=mock_callbacks["on_poll_notifications"],
        on_poll_health=mock_callbacks["on_poll_health"],
        on_refresh_status=mock_callbacks["on_refresh_status"],
    )

    pollers.start()

    # Validar que 3 jobs foram agendados
    assert len(fake_scheduler.scheduled_jobs) == 3

    # Validar delays iniciais
    jobs_by_delay = {ms: job_id for job_id, (ms, _) in fake_scheduler.scheduled_jobs.items()}
    assert 1000 in jobs_by_delay  # notifications ou health (ambos 1s inicial)
    assert 300 in jobs_by_delay  # status

    # Validar IDs não são None
    assert pollers.notifications_job_id is not None
    assert pollers.health_job_id is not None
    assert pollers.status_job_id is not None


def test_stop_cancels_all_jobs_and_resets_ids(
    fake_scheduler: FakeScheduler,
    mock_callbacks: dict[str, Callable[[], None]],
) -> None:
    """stop() deve cancelar todos os jobs e zerar IDs."""
    pollers = MainWindowPollers(
        fake_scheduler,
        on_poll_notifications=mock_callbacks["on_poll_notifications"],
        on_poll_health=mock_callbacks["on_poll_health"],
        on_refresh_status=mock_callbacks["on_refresh_status"],
    )

    pollers.start()
    initial_ids = [
        pollers.notifications_job_id,
        pollers.health_job_id,
        pollers.status_job_id,
    ]

    pollers.stop()

    # Validar que os 3 IDs foram cancelados
    assert len(fake_scheduler.canceled_jobs) == 3
    for job_id in initial_ids:
        assert job_id in fake_scheduler.canceled_jobs

    # Validar IDs zerados
    assert pollers.notifications_job_id is None
    assert pollers.health_job_id is None
    assert pollers.status_job_id is None


def test_poll_notifications_wrapper_calls_callback_and_reschedules_20s(
    fake_scheduler: FakeScheduler,
    mock_callbacks: dict[str, Callable[[], None]],
) -> None:
    """_poll_notifications_wrapper() chama callback e reagenda para 20s."""
    pollers = MainWindowPollers(
        fake_scheduler,
        on_poll_notifications=mock_callbacks["on_poll_notifications"],
        on_poll_health=mock_callbacks["on_poll_health"],
        on_refresh_status=mock_callbacks["on_refresh_status"],
    )

    pollers.start()
    initial_notif_id = pollers.notifications_job_id
    assert initial_notif_id is not None

    # Executar wrapper de notifications
    fake_scheduler.execute_job(initial_notif_id)

    # Validar callback foi chamado
    assert len(mock_callbacks["calls"]["notifications"]) == 1  # type: ignore[arg-type]

    # Validar que job anterior foi cancelado
    assert initial_notif_id in fake_scheduler.canceled_jobs

    # Validar novo job agendado para 20000ms
    new_notif_id = pollers.notifications_job_id
    assert new_notif_id is not None
    assert new_notif_id != initial_notif_id
    assert fake_scheduler.scheduled_jobs[new_notif_id][0] == 20000


def test_poll_health_wrapper_calls_callback_and_reschedules_5s(
    fake_scheduler: FakeScheduler,
    mock_callbacks: dict[str, Callable[[], None]],
) -> None:
    """_poll_health_wrapper() chama callback e reagenda para 5s."""
    pollers = MainWindowPollers(
        fake_scheduler,
        on_poll_notifications=mock_callbacks["on_poll_notifications"],
        on_poll_health=mock_callbacks["on_poll_health"],
        on_refresh_status=mock_callbacks["on_refresh_status"],
    )

    pollers.start()
    initial_health_id = pollers.health_job_id
    assert initial_health_id is not None

    # Executar wrapper de health
    fake_scheduler.execute_job(initial_health_id)

    # Validar callback foi chamado
    assert len(mock_callbacks["calls"]["health"]) == 1  # type: ignore[arg-type]

    # Validar que job anterior foi cancelado
    assert initial_health_id in fake_scheduler.canceled_jobs

    # Validar novo job agendado para 5000ms
    new_health_id = pollers.health_job_id
    assert new_health_id is not None
    assert new_health_id != initial_health_id
    assert fake_scheduler.scheduled_jobs[new_health_id][0] == 5000


def test_refresh_status_wrapper_calls_callback_and_reschedules_300ms(
    fake_scheduler: FakeScheduler,
    mock_callbacks: dict[str, Callable[[], None]],
) -> None:
    """_refresh_status_wrapper() chama callback e reagenda para 300ms."""
    pollers = MainWindowPollers(
        fake_scheduler,
        on_poll_notifications=mock_callbacks["on_poll_notifications"],
        on_poll_health=mock_callbacks["on_poll_health"],
        on_refresh_status=mock_callbacks["on_refresh_status"],
    )

    pollers.start()
    initial_status_id = pollers.status_job_id
    assert initial_status_id is not None

    # Executar wrapper de status
    fake_scheduler.execute_job(initial_status_id)

    # Validar callback foi chamado
    assert len(mock_callbacks["calls"]["status"]) == 1  # type: ignore[arg-type]

    # Validar que job anterior foi cancelado
    assert initial_status_id in fake_scheduler.canceled_jobs

    # Validar novo job agendado para 300ms
    new_status_id = pollers.status_job_id
    assert new_status_id is not None
    assert new_status_id != initial_status_id
    assert fake_scheduler.scheduled_jobs[new_status_id][0] == 300


def test_wrapper_does_not_propagate_callback_exception(
    fake_scheduler: FakeScheduler,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exceção no callback não deve ser propagada (engolida e logged)."""

    def failing_callback() -> None:
        raise ValueError("callback explode")

    pollers = MainWindowPollers(
        fake_scheduler,
        on_poll_notifications=failing_callback,
        on_poll_health=lambda: None,
        on_refresh_status=lambda: None,
    )

    pollers.start()
    initial_notif_id = pollers.notifications_job_id
    assert initial_notif_id is not None

    # Executar wrapper (não deve propagar exceção)
    with caplog.at_level(logging.ERROR):
        fake_scheduler.execute_job(initial_notif_id)

    # Validar que exceção foi logged
    assert "Erro no callback de notifications" in caplog.text
    assert "callback explode" in caplog.text

    # Validar que job foi reagendado mesmo com erro
    assert pollers.notifications_job_id is not None
    assert pollers.notifications_job_id != initial_notif_id


def test_start_handles_scheduler_exception_gracefully(
    mock_callbacks: dict[str, Callable[[], None]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Se scheduler.after() lançar exceção, job_id fica None (não trava)."""

    class FailingScheduler:
        """Scheduler que sempre falha em after()."""

        def after(self, ms: int, func: Callable[[], None]) -> str:
            raise RuntimeError("scheduler boom")

        def after_cancel(self, after_id: str) -> None:
            pass

    pollers = MainWindowPollers(
        FailingScheduler(),  # type: ignore[arg-type]
        on_poll_notifications=mock_callbacks["on_poll_notifications"],
        on_poll_health=mock_callbacks["on_poll_health"],
        on_refresh_status=mock_callbacks["on_refresh_status"],
    )

    with caplog.at_level(logging.WARNING):
        pollers.start()

    # Validar que warnings foram logged
    assert "Falha ao iniciar notifications poller" in caplog.text
    assert "Falha ao iniciar status refresh poller" in caplog.text
    assert "Falha ao iniciar health poller" in caplog.text

    # Job IDs devem ser None
    assert pollers.notifications_job_id is None
    assert pollers.health_job_id is None
    assert pollers.status_job_id is None
