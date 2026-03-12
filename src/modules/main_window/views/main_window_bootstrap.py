# -*- coding: utf-8 -*-
"""
MainWindow Bootstrap - Inicialização centralizada.

Este módulo extrai a lógica de __init__ do MainWindow para reduzir complexidade.
Responsável por:
- Build do layout (via main_window_layout.py)
- Inicialização de serviços (notifications, supabase, theme manager, etc.)
- Registro de telas no router
- Configuração de pollers (notifications, health, status)
- Binding de shortcuts globais
- Wire de sessão e health checks
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .main_window import App

log = logging.getLogger("app_gui")


def bootstrap_main_window(app: App) -> None:
    """
    Inicializa todos os componentes do MainWindow.

    Esta função centraliza toda a lógica de setup que antes estava no __init__,
    permitindo que o construtor fique limpo e focado apenas em estado básico.

    Args:
        app: Instância do MainWindow já inicializada com super().__init__
    """
    from src.core.utils.perf_timer import perf_timer
    from src.modules.main_window.views.main_window_layout import build_main_window_layout
    from src.modules.main_window.views.main_window_services import (
        init_auth_controller,
        init_status_monitor,
        init_supabase_client,
        init_theme_manager,
    )
    from src.modules.main_window.controllers import (
        MainWindowPollers,
        ScreenRouter,
        register_main_window_screens,
    )
    from src.modules.main_window.app_actions import AppActions
    from src.core.keybindings import bind_global_shortcuts

    # ═══════════════════════════════════════════════════════════════
    # 1. BUILD LAYOUT (em fases: skeleton + deferred)
    # ═══════════════════════════════════════════════════════════════
    # FASE 5A PASSO 3: Layout em 2 fases para reduzir freeze
    # - skeleton: estrutura mínima (imediato)
    # - deferred: componentes complexos (after 0)
    start_hidden = getattr(app, "_start_hidden", False)

    with perf_timer("startup.build_layout_skeleton", log, threshold_ms=50):
        app._layout = build_main_window_layout(
            app,
            start_hidden=start_hidden,
        )

    # FASE 5A FIX: Expor layout_refs para acesso ao footer_controller
    app.layout_refs = app._layout
    app.footer_controller = app._layout.footer_controller  # Exposição direta para compatibilidade

    # Expor refs do layout como atributos do MainWindow (compatibilidade)
    app.sep_menu_toolbar = app._layout.sep_menu_toolbar
    app.sep_toolbar_main = app._layout.sep_toolbar_main
    app._topbar = app._layout.topbar
    app._menu = app._layout.menu
    app._content_container = app._layout.content_container
    app.nav = app._layout.nav
    app.footer = app._layout.footer
    app.clients_count_var = app._layout.clients_count_var
    app.status_var_dot = app._layout.status_var_dot
    app.status_var_text = app._layout.status_var_text

    # Refs complementares
    app._pdf_viewer_window = None
    app._pdf_viewer_signature = None
    app.status_dot = None  # type: ignore[assignment]
    app.status_lbl = None  # type: ignore[assignment]

    # ═══════════════════════════════════════════════════════════════
    # 2. INIT SERVICES
    # ═══════════════════════════════════════════════════════════════

    # Notifications — DESATIVADO v1.5.99 (eliminado para resolver ReadError no shutdown)
    app._notifications_service = None
    app.notifications_service = None
    app._mute_notifications = False
    app._last_unread_count = 0
    app._notifications_baselined = True  # True = nunca faz baseline

    # Supabase client
    with perf_timer("startup.init_supabase", log, threshold_ms=50):
        app.supabase = init_supabase_client()
        app._client = app.supabase

    # Status fields
    app._status_base_text = app.status_var_text.get() or ""
    app._status_monitor = None
    app._main_frame_ref = None
    app._main_loaded = False

    # Theme manager
    with perf_timer("startup.init_theme_manager", log, threshold_ms=50):
        app._theme_listener = init_theme_manager(app)

    # ═══════════════════════════════════════════════════════════════
    # 3. ROUTER & SCREENS
    # ═══════════════════════════════════════════════════════════════
    with perf_timer("startup.init_router", log, threshold_ms=100):
        app._router = ScreenRouter(
            container=app._content_container,
            logger=log,
        )

        # Registrar todas as telas (hub, clients, cashflow, sites, etc.)
        register_main_window_screens(app._router, app)

    # ═══════════════════════════════════════════════════════════════
    # 4. STATUS MONITOR (health checks)
    # ═══════════════════════════════════════════════════════════════
    app._status_monitor = init_status_monitor(app)

    # Wire session and health
    _wire_session_and_health(app)

    # ═══════════════════════════════════════════════════════════════
    # 5. AUTH CONTROLLER
    # ═══════════════════════════════════════════════════════════════
    app.auth = init_auth_controller(app)

    # ═══════════════════════════════════════════════════════════════
    # 6. ACTIONS HELPER
    # ═══════════════════════════════════════════════════════════════
    app._actions = AppActions(app, logger=log)

    # ═══════════════════════════════════════════════════════════════
    # 7. KEYBINDINGS
    # ═══════════════════════════════════════════════════════════════
    bind_global_shortcuts(
        app,
        {
            "quit": app.destroy,
            "refresh": app.refresh_current_view,
            "new": app.novo_cliente,
            "edit": app.editar_cliente,
            "delete": app._excluir_cliente,
            "upload": app.enviar_para_supabase,
            "lixeira": app.abrir_lixeira,
            "hub": app.show_hub_screen,
            "find": lambda: getattr(app, "_main_frame_ref", None)
            and getattr(app._main_frame_ref, "_buscar", lambda: None)(),
        },
    )

    # ═══════════════════════════════════════════════════════════════
    # 8. POLLERS (notifications, health, status)
    # ═══════════════════════════════════════════════════════════════
    from src.modules.main_window.controllers.main_window_pollers import Scheduler

    # App herda de tb.Window (Tk), que tem after/after_cancel - cast para o Protocol
    app._pollers = MainWindowPollers(
        cast(Scheduler, app),
        on_poll_notifications=None,  # DESATIVADO v1.5.99: notificações removidas
        on_poll_health=app._poll_health_impl,
        on_refresh_status=app._refresh_status_impl,
        logger=log,
    )

    # Iniciar pollers
    app._pollers.start()

    # ═══════════════════════════════════════════════════════════════
    # 9. BINDINGS FINAIS
    # ═══════════════════════════════════════════════════════════════

    # Correção para FIX 3: Filtra para evitar rajada de chamadas em sub-widgets
    app.bind("<FocusIn>", lambda e: app._update_user_status() if e.widget is app else None, add="+")

    # ── FIX RESTORE #3: Helper robusto para resolver APP_BG ──────
    # Correção para FIX RESTORE #3: Resolve APP_BG (str ou tuple) para cor flat.
    from src.ui.ui_tokens import APP_BG

    def _resolve_bg() -> str:
        """Retorna cor flat do APP_BG respeitando o modo de aparência atual."""
        try:
            if isinstance(APP_BG, tuple):
                import customtkinter as _ctk  # noqa: PLC0415

                idx = 1 if _ctk.get_appearance_mode().lower() == "dark" else 0
                return APP_BG[idx]  # type: ignore[return-value]
            return APP_BG  # type: ignore[return-value]
        except Exception:  # noqa: BLE001
            return "#0b0b0b"

    # ── FIX RESTORE #1 + #2: Restore robusto via cover + sequência agendada ──
    # Correção para FIX RESTORE #1: Detecção min→restore e cover nativo.
    # Correção para FIX RESTORE #2: Pollers só retomam após repaint completo.
    app._was_iconic = False  # type: ignore[attr-defined]
    app._restore_job_id = None  # type: ignore[attr-defined]  # Correção para FIX RESTORE #1: controle de after pendente
    app._restore_cover = None  # type: ignore[attr-defined]  # Correção para FIX RESTORE #1: ref do cover nativo

    def _on_unmap(event: tk.Event) -> None:  # type: ignore[type-arg]
        """Correção para FIX RESTORE #1: Marca minimização real + pausa pollers."""
        if event.widget is not app:
            return
        try:
            if app.state() == "iconic":
                app._was_iconic = True
                # Correção para FIX RESTORE #2: Pausa pollers imediatamente no minimize
                try:
                    app._pollers.stop()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

    def _place_cover() -> None:
        """Correção para FIX RESTORE #1: Cover nativo tk.Frame sobre a área do app."""
        try:
            if app._restore_cover is not None:
                return  # já existe
            cover = tk.Frame(app, bg=_resolve_bg())
            cover.place(x=0, y=0, relwidth=1, relheight=1)
            cover.lift()
            app._restore_cover = cover
        except Exception:  # noqa: BLE001
            app._restore_cover = None

    def _remove_cover() -> None:
        """Correção para FIX RESTORE #1: Remove cover best-effort."""
        try:
            cover = app._restore_cover
            app._restore_cover = None
            if cover is not None and cover.winfo_exists():
                cover.place_forget()
                cover.destroy()
        except Exception:  # noqa: BLE001
            app._restore_cover = None

    def _restore_sequence() -> None:
        """Correção para FIX RESTORE #1: Sequência controlada de repaint pós-restore."""
        app._restore_job_id = None
        try:
            if not app.winfo_exists():
                _remove_cover()
                return
            # Um ciclo completo de processamento de eventos do WM
            app.update()
            app.update_idletasks()
            # Remover cover no próximo tick (após repaint)
            app.after(0, _remove_cover)
            # Correção para FIX RESTORE #2: Retomar pollers e status após repaint
            try:
                app.after(150, app._pollers.start)
            except Exception:  # noqa: BLE001
                pass
            try:
                app.after(200, app._update_user_status)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            _remove_cover()

    def _on_map(event: tk.Event) -> None:  # type: ignore[type-arg]
        """Correção para FIX RESTORE #1: Handler de restore real (apenas após minimize)."""
        if event.widget is not app:
            return
        if not app._was_iconic:
            return
        try:
            state = app.state()
        except Exception:  # noqa: BLE001
            return
        if state not in ("normal", "zoomed"):
            return
        app._was_iconic = False
        # Correção para FIX RESTORE #1: Só aplica cover+sequência no Windows
        if sys.platform != "win32":
            # Em outros SOs, apenas retomar pollers normalmente
            try:
                app._pollers.start()
            except Exception:  # noqa: BLE001
                pass
            return
        # Coloca cover nativo para mascarar preto imediatamente
        _place_cover()
        # Cancelar job anterior se existir (minimize/restore rápido)
        try:
            if app._restore_job_id is not None:
                app.after_cancel(app._restore_job_id)
        except Exception:  # noqa: BLE001
            pass
        # Agendar sequência de restore (~100ms para dar tempo ao WM)
        app._restore_job_id = app.after(100, _restore_sequence)

    app.bind("<Unmap>", _on_unmap, add="+")
    app.bind("<Map>", _on_map, add="+")

    # MICROFASE 24: Usar tema global do CustomTkinter
    from src.ui.theme_manager import theme_manager as global_theme_manager

    tema_atual = global_theme_manager.get_current_mode()
    log.info("Bootstrap do MainWindow concluído com tema: %s", tema_atual)


def _wire_session_and_health(app: App, *, _attempt: int = 0) -> None:
    """Wire de sessão e health checks ao rodapé.

    Limita a 30 tentativas (~3s) para evitar loop infinito caso o footer
    nunca seja criado (ex.: exceção no boot).
    """
    _max_wire_attempts = 30

    try:
        # FASE 5A PASSO 3: Guarda contra footer=None (deferred ainda não completou)
        if not hasattr(app, "footer") or app.footer is None:
            if _attempt >= _max_wire_attempts:
                log.warning(
                    "Footer não ficou pronto após %d tentativas; abortando wire session/health.",
                    _max_wire_attempts,
                )
                return
            if not app.winfo_exists():
                log.debug("App destruído antes de wire session/health; abortando.")
                return
            log.debug("Footer ainda não pronto, reagendando wire session/health em 100ms (tentativa %d)", _attempt + 1)
            app.after(100, lambda: _wire_session_and_health(app, _attempt=_attempt + 1))
            return

        # Conectar callbacks do StatusMonitor ao footer
        if app._status_monitor and hasattr(app.footer, "on_status_update"):
            app._status_monitor.on_status_change = app.footer.on_status_update
            log.info("StatusMonitor conectado ao footer (on_status_change callback)")
    except Exception as exc:
        log.debug("Falha ao wire session/health: %s", exc)
