"""Handlers de eventos e callbacks do MainWindow.

Extrai lógica complexa de handlers para reduzir complexidade do main_window.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.main_window.views.main_window import MainWindow  # noqa: F401  # pyright: ignore[reportAttributeAccessIssue]

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICAÇÕES — DESATIVADO v1.5.99 (eliminado para resolver ReadError no shutdown)
# Todas as funções abaixo são NO-OPs seguros mantidos para compatibilidade.
# ═══════════════════════════════════════════════════════════════════════════


def show_notification_toast(app: "MainWindow", count: int) -> None:  # noqa: ARG001
    """NO-OP: Notificações desativadas v1.5.99."""


def poll_notifications_impl(app: "MainWindow") -> None:  # noqa: ARG001
    """NO-OP: Notificações desativadas v1.5.99."""


def on_notifications_clicked(app: "MainWindow") -> None:  # noqa: ARG001
    """NO-OP: Notificações desativadas v1.5.99."""


def mark_all_notifications_read(app: "MainWindow") -> bool:  # noqa: ARG001
    """NO-OP: Notificações desativadas v1.5.99."""
    return False


def delete_notification_for_me(app: "MainWindow", notification_id: str) -> bool:  # noqa: ARG001
    """NO-OP: Notificações desativadas v1.5.99."""
    return False


def delete_all_notifications_for_me(app: "MainWindow") -> bool:  # noqa: ARG001
    """NO-OP: Notificações desativadas v1.5.99."""
    return False


def wire_session_and_health(app: "MainWindow") -> None:
    """Conecta o health check do Supabase ao rodapé para atualização automática.

    Args:
        app: Instância do MainWindow
    """
    try:
        from src.modules.main_window.views.constants import HEALTH_POLL_INTERVAL

        # Criar polling manual do estado do health check
        # DEPRECATED: Poll_health agora é gerenciado por MainWindowPollers (P2-MF3C)
        def poll_health():
            try:
                from src.infra.supabase_client import get_supabase_state

                state, _ = get_supabase_state()

                # FASE 5A FIX: Usar FooterController (sempre existe)
                if hasattr(app, "layout_refs") and app.layout_refs and hasattr(app.layout_refs, "footer_controller"):
                    app.layout_refs.footer_controller.set_cloud(state)
                    log.debug("Footer controller atualizado: %s", state)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao obter estado da nuvem no polling: %s", exc)
            # Reagendar polling (P0 #2: cancelar anterior)
            if app._health_poll_job_id is not None:
                try:
                    app.after_cancel(app._health_poll_job_id)
                except Exception as exc:  # noqa: BLE001
                    # Job pode não existir mais
                    log.debug("after_cancel health_poll falhou: %s", type(exc).__name__)
            try:
                app._health_poll_job_id = app.after(HEALTH_POLL_INTERVAL, poll_health)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao reagendar polling de health: %s", exc)
                app._health_poll_job_id = None

        # Iniciar polling
        app._health_poll_job_id = app.after(1000, poll_health)

        # Tentar obter estado inicial
        try:
            from src.infra.supabase_client import get_supabase_state

            current, _ = get_supabase_state()

            # FASE 5A FIX: Usar FooterController (sempre existe)
            if hasattr(app, "layout_refs") and app.layout_refs and hasattr(app.layout_refs, "footer_controller"):
                app.layout_refs.footer_controller.set_cloud(current)
                log.debug("Footer controller inicial: %s", current)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao definir estado inicial da nuvem: %s", exc)

    except Exception as e:
        log.warning("Erro ao conectar health check: %s", e)
