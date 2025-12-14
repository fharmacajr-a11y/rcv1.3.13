# -*- coding: utf-8 -*-
"""HubLifecycle: gerenciamento de lifecycle (timers, polling, live sync) do HUB.

Este módulo concentra toda a lógica de agendamento e ciclo de vida do HUB:
- Timers periódicos (refresh de authors, polling de notas, etc.)
- Live sync de notas (Realtime + fallback polling)
- Setup/teardown de timers

Não contém lógica de negócio - apenas **quando** executar callbacks.
O **o que fazer** permanece em HubScreen/Controllers/ViewModels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen
    from src.modules.hub.services.hub_polling_service import HubPollingService
    from src.modules.hub.services.hub_lifecycle_impl import HubLifecycleImpl


@dataclass
class HubLifecycle:
    """Gerenciador de lifecycle do HUB (timers, polling, live sync).

    Responsabilidades:
    - Agendar/cancelar timers periódicos (authors, notes, dashboard)
    - Controlar live sync de notas (Realtime + polling fallback)
    - Garantir cleanup adequado no stop()

    NÃO implementa lógica de negócio - delega para callbacks do HubScreen.
    """

    tk_root: "HubScreen"  # Referência ao HubScreen para usar tk.after e chamar callbacks
    logger: Optional[logging.Logger] = None

    # Timer IDs (None = não agendado)
    _auth_retry_job_id: Optional[str] = field(default=None, init=False)
    _authors_refresh_job_id: Optional[str] = field(default=None, init=False)
    _notes_poll_job_id: Optional[str] = field(default=None, init=False)
    _dashboard_load_job_id: Optional[str] = field(default=None, init=False)
    _notes_load_job_id: Optional[str] = field(default=None, init=False)

    # Estado do lifecycle
    _started: bool = field(default=False, init=False)
    _live_sync_active: bool = field(default=False, init=False)

    @property
    def _polling_service(self) -> "HubPollingService":
        """Acesso ao serviço de polling (MF-15)."""
        return self.tk_root._polling_service

    @property
    def _lifecycle_impl(self) -> "HubLifecycleImpl":
        """Acesso ao serviço de lifecycle (MF-15)."""
        return self.tk_root._lifecycle_impl

    def start(self) -> None:
        """Inicia o lifecycle do HUB: timers de auth, authors, notes, dashboard."""
        if self._started:
            self._log_debug("Lifecycle já iniciado, ignorando start()")
            return

        self._started = True
        self._log_debug("Iniciando lifecycle do HUB")

        # Agendar início seguro (aguarda auth estar pronta)
        self.schedule_auth_retry()

        # Agendar carregamento do dashboard
        self.schedule_dashboard_load(delay_ms=600)

        # Agendar carregamento inicial de notas (um pouco depois do dashboard)
        self.schedule_notes_load(delay_ms=800)

    def stop(self) -> None:
        """Para o lifecycle do HUB: cancela todos os timers e live sync.

        MF-15: Para polling e live sync via serviços dedicados.
        """
        if not self._started:
            return

        self._log_debug("Parando lifecycle do HUB")
        self._started = False

        # Cancelar todos os timers
        self.cancel_auth_retry()
        self.cancel_authors_refresh()
        self.cancel_notes_poll()
        self.cancel_dashboard_load()
        self.cancel_notes_load()

        # Parar polling (MF-15: via serviço)
        try:
            self._polling_service.stop_polling()
        except Exception as e:
            self._log_error(f"Erro ao parar polling: {e}")

        # Parar live sync (MF-15: via serviço)
        if self._live_sync_active:
            self.stop_live_sync()

    # ============================================================================
    # AUTH RETRY (aguarda autenticação estar pronta)
    # ============================================================================

    def schedule_auth_retry(self, delay_ms: int = 500) -> None:
        """Agenda verificação de auth (retry até auth estar pronta)."""
        if self._auth_retry_job_id is not None:
            return  # Já agendado

        self._auth_retry_job_id = self.tk_root.after(delay_ms, self._on_auth_retry_tick)
        self._log_debug(f"Auth retry agendado em {delay_ms}ms")

    def cancel_auth_retry(self) -> None:
        """Cancela verificação de auth."""
        if self._auth_retry_job_id is not None:
            try:
                self.tk_root.after_cancel(self._auth_retry_job_id)
            except Exception as e:
                self._log_debug(f"Erro ao cancelar auth retry: {e}")
            self._auth_retry_job_id = None

    def _on_auth_retry_tick(self) -> None:
        """Callback do timer de auth retry."""
        self._auth_retry_job_id = None

        try:
            # Chamar callback do HubScreen para verificar auth
            if self.tk_root._start_home_timers_safely_impl():
                # Auth pronta, timers iniciados
                self._log_debug("Auth pronta, iniciando timers do HUB")
            else:
                # Auth não pronta, reagendar
                auth_retry_ms = getattr(self.tk_root, "AUTH_RETRY_MS", 2000)
                self.schedule_auth_retry(delay_ms=auth_retry_ms)
        except Exception as e:
            self._log_error(f"Erro no auth retry tick: {e}")
            # Tentar novamente
            auth_retry_ms = getattr(self.tk_root, "AUTH_RETRY_MS", 2000)
            self.schedule_auth_retry(delay_ms=auth_retry_ms)

    # ============================================================================
    # AUTHORS REFRESH (atualização periódica do cache de nomes)
    # ============================================================================

    def schedule_authors_refresh(self, delay_ms: int = 60000) -> None:
        """Agenda refresh periódico do cache de authors."""
        if self._authors_refresh_job_id is not None:
            return  # Já agendado

        self._authors_refresh_job_id = self.tk_root.after(delay_ms, self._on_authors_refresh_tick)
        self._log_debug(f"Authors refresh agendado em {delay_ms}ms")

    def cancel_authors_refresh(self) -> None:
        """Cancela refresh periódico de authors."""
        if self._authors_refresh_job_id is not None:
            try:
                self.tk_root.after_cancel(self._authors_refresh_job_id)
            except Exception as e:
                self._log_debug(f"Erro ao cancelar authors refresh: {e}")
            self._authors_refresh_job_id = None

    def _on_authors_refresh_tick(self) -> None:
        """Callback do timer de authors refresh.

        MF-15: Chama HubPollingService.refresh_authors_cache diretamente.
        """
        self._authors_refresh_job_id = None

        try:
            # MF-15: Chamar serviço de polling ao invés de HubScreen._*_impl
            self._polling_service.refresh_authors_cache(force=False)
        except Exception as e:
            self._log_error(f"Erro no authors refresh tick: {e}")
        finally:
            # Reagendar (ciclo contínuo)
            if self._started:
                self.schedule_authors_refresh()

    # ============================================================================
    # NOTES POLL (polling periódico de notas)
    # ============================================================================

    def schedule_notes_poll(self, delay_ms: int = 10000) -> None:
        """Agenda polling periódico de notas."""
        if self._notes_poll_job_id is not None:
            return  # Já agendado

        self._notes_poll_job_id = self.tk_root.after(delay_ms, self._on_notes_poll_tick)
        self._log_debug(f"Notes poll agendado em {delay_ms}ms")

    def cancel_notes_poll(self) -> None:
        """Cancela polling periódico de notas."""
        if self._notes_poll_job_id is not None:
            try:
                self.tk_root.after_cancel(self._notes_poll_job_id)
            except Exception as e:
                self._log_debug(f"Erro ao cancelar notes poll: {e}")
            self._notes_poll_job_id = None

    def _on_notes_poll_tick(self) -> None:
        """Callback do timer de notes poll.

        MF-15: Chama HubPollingService.poll_notes diretamente.
        """
        self._notes_poll_job_id = None

        try:
            # MF-15: Chamar serviço de polling ao invés de HubScreen._*_impl
            self._polling_service.poll_notes()
        except Exception as e:
            self._log_error(f"Erro no notes poll tick: {e}")
        finally:
            # Reagendar (ciclo contínuo)
            if self._started:
                notes_poll_ms = getattr(self.tk_root, "_notes_poll_ms", 10000)
                self.schedule_notes_poll(delay_ms=notes_poll_ms)

    # ============================================================================
    # DASHBOARD LOAD (carregamento inicial do dashboard)
    # ============================================================================

    def schedule_dashboard_load(self, delay_ms: int = 600) -> None:
        """Agenda carregamento do dashboard."""
        if self._dashboard_load_job_id is not None:
            return  # Já agendado

        self._dashboard_load_job_id = self.tk_root.after(delay_ms, self._on_dashboard_load_tick)
        self._log_debug(f"Dashboard load agendado em {delay_ms}ms")

    def cancel_dashboard_load(self) -> None:
        """Cancela carregamento do dashboard."""
        if self._dashboard_load_job_id is not None:
            try:
                self.tk_root.after_cancel(self._dashboard_load_job_id)
            except Exception as e:
                self._log_debug(f"Erro ao cancelar dashboard load: {e}")
            self._dashboard_load_job_id = None

    def _on_dashboard_load_tick(self) -> None:
        """Callback do timer de dashboard load."""
        self._dashboard_load_job_id = None

        try:
            # Chamar callback do HubScreen para carregar dashboard
            self.tk_root._load_dashboard()
        except Exception as e:
            self._log_error(f"Erro no dashboard load tick: {e}")

    # ============================================================================
    # NOTES LOAD (carregamento inicial de notas)
    # ============================================================================

    def schedule_notes_load(self, delay_ms: int = 800) -> None:
        """Agenda carregamento inicial de notas."""
        if self._notes_load_job_id is not None:
            return  # Já agendado

        self._notes_load_job_id = self.tk_root.after(delay_ms, self._on_notes_load_tick)
        self._log_debug(f"Notes load agendado em {delay_ms}ms")

    def cancel_notes_load(self) -> None:
        """Cancela carregamento inicial de notas."""
        if self._notes_load_job_id is not None:
            try:
                self.tk_root.after_cancel(self._notes_load_job_id)
            except Exception as e:
                self._log_debug(f"Erro ao cancelar notes load: {e}")
            self._notes_load_job_id = None

    def _on_notes_load_tick(self) -> None:
        """Callback do timer de notes load."""
        self._notes_load_job_id = None

        try:
            # Chamar callback do HubScreen para carregar notas
            if hasattr(self.tk_root, "_load_notes"):
                self.tk_root._load_notes()
            else:
                # Fallback: chamar via controller
                self.tk_root._hub_controller.load_notes_data_async()
        except Exception as e:
            self._log_error(f"Erro no notes load tick: {e}")

    # ============================================================================
    # LIVE SYNC (Realtime + polling fallback)
    # ============================================================================

    def start_live_sync(self) -> None:
        """Inicia live sync de notas (Realtime + polling fallback).

        MF-15: Delega setup para HubLifecycleImpl, apenas controla estado aqui.
        """
        if self._live_sync_active:
            return

        self._live_sync_active = True
        self._log_debug("Iniciando live sync")

        try:
            # MF-15: Chamar serviço de lifecycle ao invés de HubScreen._*_impl
            self._lifecycle_impl.start_live_sync()
        except Exception as e:
            self._log_error(f"Erro ao iniciar live sync: {e}")
            self._live_sync_active = False

    def stop_live_sync(self) -> None:
        """Para live sync de notas.

        MF-15: Delega teardown para HubLifecycleImpl.
        """
        if not self._live_sync_active:
            return

        self._live_sync_active = False
        self._log_debug("Parando live sync")

        try:
            # MF-15: Chamar serviço de lifecycle ao invés de HubScreen._*_impl
            self._lifecycle_impl.stop_live_sync()
        except Exception as e:
            self._log_error(f"Erro ao parar live sync: {e}")

    # ============================================================================
    # HELPERS DE LOGGING
    # ============================================================================

    def _log_debug(self, message: str) -> None:
        """Log de debug."""
        if self.logger:
            self.logger.debug(f"[HubLifecycle] {message}")

    def _log_error(self, message: str) -> None:
        """Log de erro."""
        if self.logger:
            self.logger.error(f"[HubLifecycle] {message}")
