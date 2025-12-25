# -*- coding: utf-8 -*-
"""MainWindow Pollers - gerencia jobs periódicos (Tk after/after_cancel).

REFATORAÇÃO P2-MF3C:
- Extração dos pollers/jobs do MainWindow
- Centraliza lógica de agendamento/cancelamento
- Previne memory leaks com cleanup adequado
"""

from __future__ import annotations

import logging
from typing import Callable, Protocol

_log = logging.getLogger(__name__)


class Scheduler(Protocol):
    """Protocol para scheduler compatível com Tk.after/after_cancel."""

    def after(self, ms: int, func: Callable[[], None]) -> str:
        """Agenda execução após ms milissegundos."""
        ...

    def after_cancel(self, after_id: str) -> None:
        """Cancela job agendado."""
        ...


class MainWindowPollers:
    """Gerenciador de pollers periódicos do MainWindow.

    Responsável por:
    - Notificações polling (20s)
    - Status refresh (300ms)
    - Health check polling (5s)

    Mantém IDs dos jobs e cancela adequadamente no stop().
    """

    def __init__(
        self,
        scheduler: Scheduler,
        *,
        on_poll_notifications: Callable[[], None],
        on_poll_health: Callable[[], None],
        on_refresh_status: Callable[[], None],
        logger: logging.Logger | None = None,
    ):
        """Inicializa o gerenciador de pollers.

        Args:
            scheduler: Objeto com métodos after() e after_cancel() (ex: Tk Window)
            on_poll_notifications: Callback para polling de notificações
            on_poll_health: Callback para health check
            on_refresh_status: Callback para refresh de status
            logger: Logger customizado (opcional)
        """
        self._scheduler = scheduler
        self._on_poll_notifications = on_poll_notifications
        self._on_poll_health = on_poll_health
        self._on_refresh_status = on_refresh_status
        self._log = logger or _log

        # IDs dos jobs agendados (para cancelamento)
        self._jobs: dict[str, str | None] = {
            "notifications": None,
            "health": None,
            "status": None,
        }

    def start(self) -> None:
        """Inicia todos os pollers com timings iniciais."""
        # Notifications: inicial 1s, depois 20s (no próprio callback)
        try:
            self._jobs["notifications"] = self._scheduler.after(1000, self._poll_notifications_wrapper)
            self._log.debug("Notifications poller iniciado (1s inicial)")
        except Exception as exc:
            self._log.warning("Falha ao iniciar notifications poller: %s", exc)

        # Status refresh: inicial 300ms (INITIAL_STATUS_DELAY)
        try:
            self._jobs["status"] = self._scheduler.after(300, self._refresh_status_wrapper)
            self._log.debug("Status refresh poller iniciado (300ms inicial)")
        except Exception as exc:
            self._log.warning("Falha ao iniciar status refresh poller: %s", exc)

        # Health: inicial 1s, depois 5s (no próprio callback)
        try:
            self._jobs["health"] = self._scheduler.after(1000, self._poll_health_wrapper)
            self._log.debug("Health poller iniciado (1s inicial)")
        except Exception as exc:
            self._log.warning("Falha ao iniciar health poller: %s", exc)

    def stop(self) -> None:
        """Para todos os pollers cancelando jobs pendentes."""
        for name, job_id in self._jobs.items():
            if job_id is not None:
                try:
                    self._scheduler.after_cancel(job_id)
                    self._log.debug("Cancelado job: %s", name)
                except Exception as exc:
                    self._log.debug("Falha ao cancelar job %s: %s", name, exc)
                self._jobs[name] = None

    # ===== Wrappers internos (cancelam anterior + reagendam) =====

    def _poll_notifications_wrapper(self) -> None:
        """Wrapper para polling de notificações com reagendamento."""
        # Executar callback do MainWindow
        try:
            self._on_poll_notifications()
        except Exception as exc:
            self._log.exception("Erro no callback de notifications: %s", exc)

        # Reagendar para 20s (cancelar anterior)
        if self._jobs["notifications"] is not None:
            try:
                self._scheduler.after_cancel(self._jobs["notifications"])
            except Exception as cancel_exc:  # noqa: BLE001
                # Não crítico: job pode já ter sido cancelado
                self._log.debug("Job notifications já cancelado ou inválido: %s", type(cancel_exc).__name__)

        try:
            self._jobs["notifications"] = self._scheduler.after(20000, self._poll_notifications_wrapper)
        except Exception as exc:
            self._log.debug("Falha ao reagendar notifications: %s", exc)
            self._jobs["notifications"] = None

    def _poll_health_wrapper(self) -> None:
        """Wrapper para health check com reagendamento."""
        # Executar callback do MainWindow
        try:
            self._on_poll_health()
        except Exception as exc:
            self._log.exception("Erro no callback de health: %s", exc)

        # Reagendar para 5s (HEALTH_POLL_INTERVAL, cancelar anterior)
        if self._jobs["health"] is not None:
            try:
                self._scheduler.after_cancel(self._jobs["health"])
            except Exception as cancel_exc:  # noqa: BLE001
                # Não crítico: job pode já ter sido cancelado
                self._log.debug("Job health já cancelado ou inválido: %s", type(cancel_exc).__name__)

        try:
            self._jobs["health"] = self._scheduler.after(5000, self._poll_health_wrapper)
        except Exception as exc:
            self._log.debug("Falha ao reagendar health: %s", exc)
            self._jobs["health"] = None

    def _refresh_status_wrapper(self) -> None:
        """Wrapper para status refresh com reagendamento."""
        # Executar callback do MainWindow
        try:
            self._on_refresh_status()
        except Exception as exc:
            self._log.exception("Erro no callback de status refresh: %s", exc)

        # Reagendar para 300ms (STATUS_REFRESH_INTERVAL, cancelar anterior)
        if self._jobs["status"] is not None:
            try:
                self._scheduler.after_cancel(self._jobs["status"])
            except Exception as cancel_exc:  # noqa: BLE001
                # Não crítico: job pode já ter sido cancelado
                self._log.debug("Job status já cancelado ou inválido: %s", type(cancel_exc).__name__)

        try:
            self._jobs["status"] = self._scheduler.after(300, self._refresh_status_wrapper)
        except Exception as exc:
            self._log.debug("Falha ao reagendar status refresh: %s", exc)
            self._jobs["status"] = None

    # ===== Acesso aos IDs dos jobs (para compatibilidade com testes) =====

    @property
    def notifications_job_id(self) -> str | None:
        """ID do job de notificações (para compatibilidade)."""
        return self._jobs["notifications"]

    @property
    def health_job_id(self) -> str | None:
        """ID do job de health (para compatibilidade)."""
        return self._jobs["health"]

    @property
    def status_job_id(self) -> str | None:
        """ID do job de status (para compatibilidade)."""
        return self._jobs["status"]
