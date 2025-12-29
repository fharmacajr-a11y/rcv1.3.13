"""Handlers de eventos e callbacks do MainWindow.

Extrai lógica complexa de handlers para reduzir complexidade do main_window.py.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.main_window.views.main_window import MainWindow  # noqa: F401

log = logging.getLogger(__name__)


def show_notification_toast(app: "MainWindow", count: int) -> None:
    """Mostra toast do Windows quando chegar nova notificação.

    Args:
        app: Instância do MainWindow
        count: Número de novas notificações

    Notas:
        - Requer winotify instalado (pip install winotify)
        - Em versões instaladas do app, pode ser necessário registrar AppId
          via atalho no Menu Iniciar para banners aparecerem corretamente
    """
    try:
        from winotify import Notification, audio  # type: ignore[import-untyped]
    except ImportError:
        # winotify não instalado - fallback silencioso
        log.info(
            "[Notifications] winotify não instalado; toasts do Windows desativados. "
            "Para ativar, rode: pip install winotify"
        )
        return

    try:
        from src.utils.resource_path import resource_path

        # Título e mensagem
        title = "RCGestor"
        message = f"Você tem {count} nova(s) notificação(ões)"

        # Obter caminho do ícone (winotify requer caminho absoluto)
        icon_path = None
        try:
            png_path = resource_path("rc.png")
            if os.path.exists(png_path):
                # Garantir caminho absoluto
                icon_path = os.path.abspath(png_path)
                log.debug("[Notifications] Toast: ícone encontrado em %s", icon_path)
            else:
                log.debug("[Notifications] Toast: ícone rc.png não encontrado, usando sem ícone")
        except Exception as exc:
            log.debug("[Notifications] Toast: erro ao buscar ícone, continuando sem ícone: %s", exc)

        # Log de diagnóstico
        log.info(
            "[Notifications] Toast: tentando mostrar (app_id=RCGestor, title=%s, icon=%s)",
            title,
            icon_path or "None",
        )

        # Criar toast (com ou sem ícone)
        if icon_path:
            toast = Notification(
                app_id="RCGestor",
                title=title,
                msg=message,
                duration="short",
                icon=icon_path,
            )
        else:
            toast = Notification(
                app_id="RCGestor",
                title=title,
                msg=message,
                duration="short",
            )

        # Definir áudio (usar Default para som de notificação)
        toast.set_audio(audio.Default, loop=False)

        # Mostrar
        toast.show()

        log.info("[Notifications] Toast exibido com sucesso: %s", message)

    except Exception:
        # Erro ao mostrar toast - logar stack completo
        log.exception("[Notifications] Erro ao mostrar toast do Windows")
        # Nota: não re-raise para não quebrar a aplicação


def poll_notifications_impl(app: "MainWindow") -> None:
    """Implementação headless de polling de notificações (sem lógica de reagendamento).

    Args:
        app: Instância do MainWindow
    """
    if not app._notifications_service:
        return

    # Verificar se temos org_id
    org_id = app._get_org_id_cached_simple()
    if not org_id:
        return

    try:
        # Buscar contador de não lidas (incluindo próprias)
        unread_count = app._notifications_service.fetch_unread_count(include_self=True)

        # Atualizar badge no TopBar
        if hasattr(app, "_topbar") and app._topbar:
            app._topbar.set_notifications_count(unread_count)

        # Criar baseline na primeira execução (evitar "chuva de toast" ao abrir)
        if not getattr(app, "_notifications_baselined", False):
            app._last_unread_count = unread_count
            app._notifications_baselined = True
            return

        # Detectar NOVAS notificações (contador aumentou)
        if unread_count > app._last_unread_count:
            new_count = unread_count - app._last_unread_count
            log.info("[Notifications] Polling: %d NOVA(S) notificação(ões) detectada(s)", new_count)

            # Mostrar toast se não estiver silenciado
            if not app._mute_notifications:
                show_notification_toast(app, new_count)
        else:
            log.debug("[Notifications] Polling: %d não lida(s) (sem mudanças)", unread_count)

        # Atualizar contador anterior
        app._last_unread_count = unread_count

    except Exception:
        log.exception("[Notifications] Erro ao fazer polling")


def on_notifications_clicked(app: "MainWindow") -> None:
    """Callback quando usuário clica no botão de notificações.

    Args:
        app: Instância do MainWindow
    """
    if not app._notifications_service:
        return

    try:
        # Buscar últimas notificações (já formatadas para UI)
        notifications = app._notifications_service.fetch_latest_for_ui(limit=20)

        # Buscar contador de não lidas e atualizar badge (incluindo próprias)
        unread_count = app._notifications_service.fetch_unread_count(include_self=True)
        if hasattr(app, "_topbar") and app._topbar:
            app._topbar.set_notifications_count(unread_count)

        # Atualizar dados no TopBar (também passa flag de mute)
        if hasattr(app, "_topbar") and app._topbar:
            app._topbar.set_notifications_data(notifications, mute_callback=app._toggle_mute_notifications)

    except Exception:
        log.exception("[Notifications] Erro ao buscar notificações")


def mark_all_notifications_read(app: "MainWindow") -> bool:
    """Marca todas notificações como lidas.

    Args:
        app: Instância do MainWindow

    Returns:
        True se sucesso, False caso contrário
    """
    if not app._notifications_service:
        return False

    try:
        # Chamar serviço para marcar como lidas
        success = app._notifications_service.mark_all_read()

        if success:
            # Atualizar badge para 0
            if hasattr(app, "_topbar") and app._topbar:
                app._topbar.set_notifications_count(0)

            # Atualizar contador anterior
            app._last_unread_count = 0

            log.info("[Notifications] Todas notificações marcadas como lidas")
            return True
        else:
            log.warning("[Notifications] Serviço retornou False ao marcar notificações como lidas")
            return False

    except Exception:
        log.exception("[Notifications] Erro ao marcar notificações como lidas")
        return False


def delete_notification_for_me(app: "MainWindow", notification_id: str) -> bool:
    """Exclui uma notificação apenas para o usuário atual (soft delete).

    A notificação fica oculta apenas para este usuário, outros membros
    da organização ainda podem vê-la.

    Args:
        app: Instância do MainWindow
        notification_id: ID da notificação a excluir

    Returns:
        True se sucesso, False caso contrário
    """
    if not app._notifications_service:
        log.warning("[Notifications] Serviço de notificações não disponível")
        return False

    try:
        success = app._notifications_service.hide_notification_for_me(notification_id)

        if success:
            log.info("[Notifications] Notificação %s excluída para o usuário", notification_id)
            # Recarregar notificações para atualizar a view
            on_notifications_clicked(app)
            return True
        else:
            log.warning("[Notifications] Falha ao excluir notificação %s", notification_id)
            return False

    except Exception:
        log.exception("[Notifications] Erro ao excluir notificação %s", notification_id)
        return False


def delete_all_notifications_for_me(app: "MainWindow") -> bool:
    """Exclui todas notificações apenas para o usuário atual (soft delete).

    Todas as notificações ficam ocultas apenas para este usuário,
    outros membros da organização ainda podem vê-las.

    Args:
        app: Instância do MainWindow

    Returns:
        True se sucesso, False caso contrário
    """
    if not app._notifications_service:
        log.warning("[Notifications] Serviço de notificações não disponível")
        return False

    try:
        success = app._notifications_service.hide_all_for_me()

        if success:
            log.info("[Notifications] Todas notificações excluídas para o usuário")
            # Atualizar badge para 0
            if hasattr(app, "_topbar") and app._topbar:
                app._topbar.set_notifications_count(0)
            # Atualizar contador anterior
            app._last_unread_count = 0
            # Recarregar notificações para atualizar a view
            on_notifications_clicked(app)
            return True
        else:
            log.warning("[Notifications] Falha ao excluir todas notificações")
            return False

    except Exception:
        log.exception("[Notifications] Erro ao excluir todas notificações")
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
                from infra.supabase_client import get_supabase_state

                state, _ = get_supabase_state()
                app.footer.set_cloud(state)
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
            from infra.supabase_client import get_supabase_state

            current, _ = get_supabase_state()
            app.footer.set_cloud(current)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao definir estado inicial da nuvem: %s", exc)

    except Exception as e:
        log.warning("Erro ao conectar health check: %s", e)
