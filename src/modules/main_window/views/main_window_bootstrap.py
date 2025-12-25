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
    from src.modules.main_window.views.main_window_layout import build_main_window_layout
    from src.modules.main_window.views.main_window_services import (
        init_auth_controller,
        init_notifications_service,
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
    # 1. BUILD LAYOUT
    # ═══════════════════════════════════════════════════════════════
    tema_atual = app.tema_atual
    start_hidden = getattr(app, "_start_hidden", False)

    app._layout = build_main_window_layout(
        app,
        theme_name=tema_atual,
        start_hidden=start_hidden,
    )

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

    # Notifications
    app._notifications_service = init_notifications_service(app)
    app.notifications_service = app._notifications_service
    app._mute_notifications = False
    app._last_unread_count = 0

    # Supabase client
    app.supabase = init_supabase_client()
    app._client = app.supabase

    # Status fields
    app._status_base_text = app.status_var_text.get() or ""
    app._status_monitor = None
    app._main_frame_ref = None
    app._main_loaded = False

    # Theme manager
    app._theme_listener = init_theme_manager(app)

    # ═══════════════════════════════════════════════════════════════
    # 3. ROUTER & SCREENS
    # ═══════════════════════════════════════════════════════════════
    app._router = ScreenRouter(
        container=app._content_container,
        logger=log,
    )

    # Registrar todas as telas (hub, clients, passwords, etc.)
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
            "subpastas": app.open_client_storage_subfolders,
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
        on_poll_notifications=app._poll_notifications_impl,
        on_poll_health=app._poll_health_impl,
        on_refresh_status=app._refresh_status_impl,
        logger=log,
    )

    # Iniciar pollers
    app._pollers.start()

    # ═══════════════════════════════════════════════════════════════
    # 9. BINDINGS FINAIS
    # ═══════════════════════════════════════════════════════════════
    app.bind("<FocusIn>", lambda e: app._update_user_status(), add="+")

    log.info("Bootstrap do MainWindow concluído com tema: %s", tema_atual)


def _wire_session_and_health(app: App) -> None:
    """Wire de sessão e health checks ao rodapé."""
    try:
        # Conectar callbacks do StatusMonitor ao footer
        if app._status_monitor and hasattr(app.footer, "on_status_update"):
            app._status_monitor.on_status_change = app.footer.on_status_update
    except Exception as exc:
        log.debug("Falha ao wire session/health: %s", exc)
