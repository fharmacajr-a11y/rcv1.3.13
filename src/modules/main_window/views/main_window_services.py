"""Funções auxiliares para inicializar serviços do MainWindow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.modules.main_window.views.main_window import MainWindow  # noqa: F401

log = logging.getLogger(__name__)


def init_notifications_service(app: "MainWindow") -> Optional[Any]:
    """Inicializa o serviço de notificações.

    Args:
        app: Instância do MainWindow

    Returns:
        Instância do NotificationsService ou None se falhar
    """
    try:
        from src.infra.repositories.notifications_repository import NotificationsRepositoryAdapter
        from src.core.notifications_service import NotificationsService

        notifications_repo = NotificationsRepositoryAdapter()
        service = NotificationsService(
            repository=notifications_repo,
            org_id_provider=app._get_org_id_cached_simple,
            user_provider=app._get_user_with_org,
            logger=log,
        )
        log.info("[MainWindow] NotificationsService inicializado com sucesso")
        return service
    except Exception as exc:
        log.exception("[MainWindow] Falha ao inicializar NotificationsService: %s", exc)
        return None


def init_status_monitor(app: "MainWindow") -> Optional[Any]:
    """Inicializa o monitor de status (health checks).

    Args:
        app: Instância do MainWindow

    Returns:
        Instância do StatusMonitor ou None se falhar
    """
    try:
        from src.core.status_monitor import StatusMonitor
        from src.core.app_core import NO_FS

        monitor = StatusMonitor(app._handle_status_update, app_after=app.after)
        monitor.set_cloud_only(NO_FS)
        monitor.start()
        return monitor
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao inicializar StatusMonitor: %s", exc)
        return None


def init_auth_controller(app: "MainWindow") -> Any:
    """Inicializa o controlador de autenticação.

    Args:
        app: Instância do MainWindow

    Returns:
        Instância do AuthController
    """
    from src.core.auth_controller import AuthController

    return AuthController(on_user_change=lambda username: app._refresh_status_display())


def init_theme_manager(app: "MainWindow") -> Optional[Any]:
    """Configura o gerenciador de temas.

    Args:
        app: Instância do MainWindow

    Returns:
        Callback do theme listener ou None
    """
    try:
        from src.ui import theme_manager, themes

        theme_manager.register_window(app)

        def listener(theme: str) -> None:
            themes.apply_button_styles(app, theme=theme)

        theme_manager.add_listener(listener)
        return listener
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao inicializar theme manager: %s", exc)
        return None


def init_supabase_client() -> Optional[Any]:
    """Carrega cliente Supabase.

    Returns:
        Cliente supabase ou None se falhar
    """
    try:
        from src.infra.supabase_client import supabase

        return supabase
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao carregar supabase client: %s", exc)
        return None
