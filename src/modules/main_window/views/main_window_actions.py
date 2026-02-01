# -*- coding: utf-8 -*-
"""
MainWindow Actions - Métodos extraídos para redução de LOC.

Este módulo contém os métodos principais do MainWindow que foram extraídos
para permitir que a classe principal fique <= 650 LOC (idealmente <= 550).

Cada função recebe 'app' como primeiro argumento para evitar dependências circulares.
O MainWindow mantém wrappers de 1-3 linhas que delegam para essas funções.

MICROFASE 24+: Migrado para usar ThemeManager global quando CTk disponível.
"""

from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Callable, Optional

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER

# ttkbootstrap foi REMOVIDO - CustomTkinter é obrigatório agora
# if not HAS_CUSTOMTKINTER:
#     import ttkbootstrap as tb

if TYPE_CHECKING:
    from .main_window import App

log = logging.getLogger("app_gui")


# ═══════════════════════════════════════════════════════════════════════════
# POLLING & NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════


def poll_notifications(app: App) -> None:
    """DEPRECATED: Polling periódico de notificações (a cada 20s).

    AVISO: Este método está deprecated desde P2-MF3C.
    Use MainWindowPollers + _poll_notifications_impl() ao invés.
    Mantido apenas para compatibilidade com código legado.
    """
    if not app._notifications_service:
        return

    # Verificar se temos org_id
    org_id = app._get_org_id_cached_simple()
    if not org_id:
        # Reagendar sem org_id (P0 #2: cancelar anterior)
        if app._notifications_poll_job_id is not None:
            try:
                app.after_cancel(app._notifications_poll_job_id)
            except Exception as cancel_exc:  # noqa: BLE001
                # Não crítico: job pode já ter sido cancelado
                log.debug("Job notifications já cancelado: %s", type(cancel_exc).__name__)
        app._notifications_poll_job_id = app.after(20000, lambda: poll_notifications(app))
        return

    try:
        # Buscar contador de não lidas (incluindo próprias)
        unread_count = app._notifications_service.fetch_unread_count(include_self=True)

        # Atualizar badge no TopBar
        if hasattr(app, "_topbar") and app._topbar:
            app._topbar.set_notifications_count(unread_count)

        # Detectar NOVAS notificações (contador aumentou)
        if unread_count > app._last_unread_count:
            new_count = unread_count - app._last_unread_count
            log.info("[Notifications] Polling: %d NOVA(S) notificação(ões) detectada(s)", new_count)

            # Mostrar toast se não estiver silenciado
            if not app._mute_notifications:
                app._show_notification_toast(new_count)
        else:
            log.debug("[Notifications] Polling: %d não lida(s) (sem mudanças)", unread_count)

        # Atualizar contador anterior
        app._last_unread_count = unread_count

    except Exception:
        log.exception("[Notifications] Erro ao fazer polling")

    # Reagendar para 20s (P0 #2: cancelar anterior)
    if app._notifications_poll_job_id is not None:
        try:
            app.after_cancel(app._notifications_poll_job_id)
        except Exception as cancel_exc:  # noqa: BLE001
            # Não crítico: job pode já ter sido cancelado
            log.debug("Job notifications já cancelado: %s", type(cancel_exc).__name__)
    app._notifications_poll_job_id = app.after(20000, lambda: poll_notifications(app))


# ═══════════════════════════════════════════════════════════════════════════
# ONLINE/OFFLINE STATE
# ═══════════════════════════════════════════════════════════════════════════


def apply_online_state(app: App, is_online: Optional[bool]) -> None:
    """Aplica estado de conectividade (online/offline)."""
    from src.modules.main_window.views.state_helpers import (
        ConnectivityState,
        compute_connectivity_state,
        should_show_offline_alert,
    )

    if is_online is None:
        return

    # Inicializar estado se não existir (compatibilidade com testes)
    # Usar __dict__ ao invés de hasattr para evitar recursão infinita com Tk.__getattr__
    if "_connectivity_state" not in app.__dict__:
        app._connectivity_state = ConnectivityState(is_online=True, offline_alerted=False)

    # Guardar estado anterior para detecção de transição
    was_online = app._connectivity_state.is_online

    # Calcular novo estado usando helper
    new_state = compute_connectivity_state(
        current_online=app._connectivity_state.is_online,
        new_online=bool(is_online),
        already_alerted=app._connectivity_state.offline_alerted,
    )
    app._connectivity_state = new_state

    # Atualizar UI de clientes (fallback seguro para frames que não implementam o método)
    frame = app._main_screen_frame()
    if frame:
        # P0 #3: Usar hasattr para compatibilidade com ClientesV2Frame e outros frames
        if hasattr(frame, "_update_main_buttons_state"):
            try:
                frame._update_main_buttons_state()
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Falha ao atualizar estado dos botões do frame %s: %s",
                    type(frame).__name__,
                    exc,
                )
        else:
            log.debug(
                "Frame %s não implementa _update_main_buttons_state (ok para ClientesV2)",
                type(frame).__name__,
            )

    # Verificar se deve mostrar alerta usando helper
    if should_show_offline_alert(was_online, new_state.is_online, new_state.offline_alerted):
        try:
            messagebox.showwarning(
                "Sem conexão",
                "Este aplicativo exige internet para funcionar. Verifique sua conexão e tente novamente.",
                parent=app,
            )
            # Atualizar flag de alerta mostrado
            app._connectivity_state = ConnectivityState(
                is_online=new_state.is_online,
                offline_alerted=True,
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao exibir alerta de offline: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# THEME MANAGEMENT (MICROFASE 24+: Migrado para ThemeManager)
# ═══════════════════════════════════════════════════════════════════════════


def set_theme(app: App, new_theme_or_mode: str) -> None:
    """Troca o tema/modo da aplicação.

    MICROFASE 26: CustomTkinter é obrigatório (ttkbootstrap removido).

    Args:
        app: Instância do App
        new_theme_or_mode: Modo CTk ("light"/"dark")
    """
    if HAS_CUSTOMTKINTER:
        _set_theme_ctk(app, new_theme_or_mode)
    else:
        log.warning("CustomTkinter não disponível - tema não aplicado")


def _set_theme_ctk(app: App, mode: str) -> None:
    """Aplica tema usando ThemeManager (CustomTkinter)."""
    from src.modules.main_window.views.state_helpers import validate_theme_mode
    from src.ui.theme_manager import theme_manager

    # Validar e normalizar modo (pode converter tema legado)
    validated_mode = validate_theme_mode(mode, fallback="light")

    try:
        # Aplicar modo via ThemeManager global
        theme_manager.set_mode(validated_mode)

        # Atualizar estado do app
        app.tema_atual = validated_mode

        # Notificar listener se existir
        try:
            if hasattr(app, "_theme_listener") and app._theme_listener:
                app._theme_listener(validated_mode)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao notificar theme_listener: %s", exc)

        log.info(f"Modo de tema aplicado via ThemeManager: {validated_mode}")
    except Exception:
        log.exception(f"Falha ao aplicar modo via ThemeManager: {mode}")
        messagebox.showerror(
            "Erro",
            f"Falha ao aplicar modo de tema: {mode}",
            parent=app,
        )


def _set_theme_legacy(app: App, theme: str) -> None:
    """Aplica tema usando sistema legado (ttkbootstrap).

    ⚠️ MICROFASE 26: PODE SER REMOVIDO.
    ttkbootstrap foi completamente removido do projeto.
    Mantido apenas para referência histórica.
    """
    log.warning("_set_theme_legacy chamado mas ttkbootstrap foi removido")


def patch_style_element_create(style: tb.Style) -> None:
    """
    Patching de segurança: ignora exclusivamente erros
    'Duplicate element Combobox.*' gerados pelo ttkbootstrap
    ao recriar elementos ao trocar de tema.
    """
    # try to get internal Style instance
    internal_style = getattr(style, "style", None)
    target = internal_style if internal_style is not None else style

    # evitar patch duplicado
    if getattr(target, "_rc_safe_element_create_patched", False):
        return

    original_element_create = target.element_create

    def safe_element_create(elementname: str, etype: str, *specs, **opts):
        try:
            return original_element_create(elementname, etype, *specs, **opts)
        except tk.TclError as exc:
            msg = str(exc)
            # Ignorar APENAS elementos duplicados do Combobox.* (downarrow, padding, etc.)
            if "Duplicate element" in msg and elementname.startswith("Combobox."):
                log.debug(
                    "Ignorando erro duplicado de %s em element_create: %s",
                    elementname,
                    msg,
                )
                return
            raise

    target.element_create = safe_element_create
    target._rc_safe_element_create_patched = True


# ═══════════════════════════════════════════════════════════════════════════
# CLIENTS COUNT
# ═══════════════════════════════════════════════════════════════════════════


def refresh_clients_count_async(app: App, auto_schedule: bool = True) -> None:
    """
    Atualiza a contagem de clientes do Supabase de forma assíncrona.
    Usa threading para não travar a UI.

    Args:
        auto_schedule: Se True, agenda próxima atualização automática em 30s
    """
    from src.modules.clientes import service as clientes_service

    def _work():
        try:
            total = clientes_service.count_clients()
        except Exception as e:
            # Não trata como erro crítico; count_clients já retorna last-known
            log.warning("Erro ao atualizar contagem de clientes: %s", e)
            total = 0

        # Atualizar na thread da UI
        text = "1 cliente" if total == 1 else f"{total} clientes"
        try:
            app.after(0, lambda: app.clients_count_var.set(text))
            # FASE 5A PASSO 3: Guarda contra footer=None (deferred ainda não completou)
            if hasattr(app, "footer") and app.footer is not None:
                app.after(0, lambda: app.footer.set_count(total))
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar contagem de clientes: %s", exc)

        # Auto-refresh: agenda próxima atualização em 30s
        if auto_schedule:
            try:
                app.after(
                    30000,
                    lambda: refresh_clients_count_async(app, auto_schedule=True),
                )
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao agendar auto-refresh de contagem: %s", exc)

    threading.Thread(target=_work, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════
# CLIENT STORAGE
# ═══════════════════════════════════════════════════════════════════════════


def get_current_client_storage_prefix(app: App) -> str:
    """
    Retorna o prefix (caminho da pasta) do cliente atualmente selecionado no Storage.
    Ex.: retorna '0a7c9f39-4b7d-4a88-8e77-7b88a38c66d7/7'

    Este método é chamado automaticamente pelo uploader_supabase.py quando disponível.
    A implementação usa a MESMA lógica da tela 'Ver Subpastas' / open_files_browser.
    """
    try:
        values = app._selected_main_values()
        if not values:
            return ""

        client_id = values[0]

        # Usa mesma lógica do open_client_storage_subfolders
        u = app._get_user_cached()
        if not u:
            return ""

        org_id = app._get_org_id_cached(u["id"])
        if not org_id:
            return ""

        # Formato idêntico ao open_files_browser: {org_id}/{client_id}
        return f"{org_id}/{client_id}".strip("/")
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao construir caminho de storage: %s", exc)

    return ""


# ═══════════════════════════════════════════════════════════════════════════
# TOPBAR STATE
# ═══════════════════════════════════════════════════════════════════════════


def update_topbar_state(app: App, frame_or_cls: Any) -> None:
    """Atualiza estado da topbar baseado no frame atual."""
    from src.modules.notas import HubFrame

    hub_cls = HubFrame
    is_hub = False
    try:
        # classe, instância ou callable (lambda) que retorna frame
        if isinstance(frame_or_cls, type):
            is_hub = frame_or_cls is hub_cls
        elif callable(frame_or_cls):
            # se for factory/lambda, checa o current()
            cur = app.nav.current()
            is_hub = isinstance(cur, hub_cls) if cur is not None else False
        else:
            is_hub = isinstance(frame_or_cls, hub_cls)

        # redundância segura: também checa o frame atual do controlador
        cur = app.nav.current()
        if cur is not None:
            is_hub = is_hub or isinstance(cur, hub_cls)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao verificar se é hub: %s", exc)

    # NOVO: usar screen name do router para atualizar estado dos botões
    try:
        screen_name = app._router.current_name() or "main"
        app._topbar.set_active_screen(screen_name)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao atualizar active_screen na topbar: %s", exc)
        # Fallback para método antigo
        try:
            app._topbar.set_is_hub(is_hub)
        except Exception as exc2:  # noqa: BLE001
            log.debug("Falha ao atualizar estado is_hub na topbar (fallback): %s", exc2)

    try:
        app._menu.set_is_hub(is_hub)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao atualizar estado is_hub no menu: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# CHATGPT WINDOW
# ═══════════════════════════════════════════════════════════════════════════


def open_chatgpt_window(app: App) -> None:
    """Abre ou traz para frente a janela do ChatGPT."""
    from src.modules.chatgpt.views.chatgpt_window import ChatGPTWindow

    window = getattr(app, "_chatgpt_window", None)
    try:
        if window is not None and window.winfo_exists():
            window.show()
            return
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao focar janela do ChatGPT: %s", exc)
        app._chatgpt_window = None

    # Criar nova janela com callback para limpar referência ao fechar
    try:
        parent_window = app.winfo_toplevel()
    except Exception:
        parent_window = app
    window = ChatGPTWindow(parent_window, on_close_callback=app._on_chatgpt_close)
    app._chatgpt_window = window

    try:
        # Registrar WM_DELETE_WINDOW para capturar fechamento pela barra de título
        window.protocol("WM_DELETE_WINDOW", app._close_chatgpt_window)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao registrar handler de fechamento do ChatGPT: %s", exc)

    try:
        window.bind("<Destroy>", lambda event: app._on_chatgpt_destroy(window), add="+")
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao vincular destroy do ChatGPT: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════════════════════


def on_menu_logout(app: App) -> None:
    """Handler do menu Sair: confirmação + logout + fechar app."""
    from src.infra import supabase_auth
    from src.ui import custom_dialogs

    title = "Encerrar sessão"
    message = (
        "Tem certeza que deseja encerrar a sessão atual?\n\n"
        "Você precisará informar a senha novamente ao abrir o aplicativo."
    )
    try:
        confirm = custom_dialogs.ask_ok_cancel(app, title, message)
    except Exception:
        try:
            confirm = messagebox.askyesno(title, message, parent=app)
        except Exception:
            confirm = True
    if not confirm:
        return

    try:
        supabase_auth.logout(app._client)
    except Exception:
        log.warning("Falha ao realizar logout", exc_info=True)

    try:
        app.destroy()
    except Exception as exc:  # noqa: BLE001
        log.exception("Erro ao destruir janela: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# USER STATUS
# ═══════════════════════════════════════════════════════════════════════════


def schedule_user_status_refresh(app: App) -> None:
    """DEPRECATED: Agenda refresh periódico de status de usuário.

    AVISO: Este método está deprecated desde P2-MF3C.
    Use MainWindowPollers + _refresh_status_impl() ao invés.
    Mantido apenas para compatibilidade com código legado.
    """
    from src.modules.main_window.views.constants import STATUS_REFRESH_INTERVAL

    app._update_user_status()
    try:
        txt = app.status_var_text.get() or ""
    except Exception:
        txt = ""
    if "Usuário:" not in txt:
        # P0 #2: cancelar job anterior antes de reagendar
        if app._status_refresh_job_id is not None:
            try:
                app.after_cancel(app._status_refresh_job_id)
            except Exception as cancel_exc:  # noqa: BLE001
                # Não crítico: job pode já ter sido cancelado
                log.debug("Job status_refresh já cancelado: %s", type(cancel_exc).__name__)
        try:
            app._status_refresh_job_id = app.after(STATUS_REFRESH_INTERVAL, lambda: schedule_user_status_refresh(app))
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao agendar refresh de status de usuário: %s", exc)
            app._status_refresh_job_id = None


# ═══════════════════════════════════════════════════════════════════════════
# CHANGELOG
# ═══════════════════════════════════════════════════════════════════════════


def show_changelog(app: App) -> None:
    """Exibe o changelog da aplicação."""
    from .helpers import resource_path

    try:
        with open(resource_path("runtime_docs/CHANGELOG.md"), "r", encoding="utf-8") as f:
            conteudo = f.read()
        preview = "\n".join(conteudo.splitlines()[:20])
        messagebox.showinfo("Changelog", preview, parent=app)
    except Exception:
        messagebox.showinfo(
            "Changelog",
            "Arquivo CHANGELOG.md não encontrado.",
            parent=app,
        )


# ═══════════════════════════════════════════════════════════════════════════
# CLIENTS PICKER
# ═══════════════════════════════════════════════════════════════════════════


def open_clients_picker(
    app: App,
    on_pick: Callable[[dict[str, Any]], None],
    *,
    banner_text: str | None = None,
    return_to: Callable[[], None] | None = None,
) -> None:
    """Compat helper legado. Prefira start_client_pick_mode em novos fluxos."""
    from src.modules.main_window.controller import navigate_to, start_client_pick_mode

    if return_to is None:

        def _return_to_hub() -> None:
            navigate_to(app, "hub")

        return_to = _return_to_hub
    effective_banner = banner_text or "Modo seleção: escolha um cliente para continuar"
    start_client_pick_mode(
        app,
        on_client_picked=on_pick,
        banner_text=effective_banner,
        return_to=return_to,
    )


# ═══════════════════════════════════════════════════════════════════════════
# DESTROY
# ═══════════════════════════════════════════════════════════════════════════


def destroy_window(app: App) -> None:
    """Limpeza e destruição do MainWindow.

    MICROFASE 24.1: Shutdown limpo com cancelamento de after jobs.
    """
    from src.utils.theme_manager import theme_manager

    # MICROFASE 24.1: Idempotência - evitar duplo cleanup
    if getattr(app, "_is_destroying", False):
        log.debug("destroy_window já em execução, pulando")
        return

    app._is_destroying = True  # type: ignore[attr-defined]
    log.info("Iniciando shutdown limpo do MainWindow")

    # P2-MF3C: Parar todos os pollers (notificações, health, status)
    if hasattr(app, "_pollers"):
        try:
            app._pollers.stop()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao parar pollers: %s", exc)

    if getattr(app, "_status_monitor", None):
        try:
            status_monitor = getattr(app, "_status_monitor", None)
            if status_monitor is not None:
                status_monitor.stop()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao parar StatusMonitor: %s", exc)
        finally:
            app._status_monitor = None

    if getattr(app, "_theme_listener", None):
        try:
            listener = getattr(app, "_theme_listener", None)
            if listener is not None:
                theme_manager.remove_listener(listener)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao remover theme_listener: %s", exc)

    # MICROFASE 24.1: Cancelar todos os after jobs pendentes
    try:
        from src.ui.shutdown import cancel_all_after_jobs

        cancelled = cancel_all_after_jobs(app)
        log.info("Cancelados %d after jobs pendentes", cancelled)
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao cancelar after jobs: %s", exc)

    # Chamar super().destroy() no contexto do MainWindow
    # Nota: não podemos chamar super() aqui pois estamos fora da classe
    # A função deve ser chamada pelo método destroy() do MainWindow
    log.info("Limpeza de recursos do MainWindow concluída")


# ═══════════════════════════════════════════════════════════════════════════
# USER STATUS & SESSION
# ═══════════════════════════════════════════════════════════════════════════


def user_status_suffix(app: App) -> str:
    """Retorna sufixo de status do usuário."""
    from src.modules.main_window.views.state_helpers import build_user_status_suffix

    email = ""
    role = "user"
    try:
        u = app._get_user_cached()
        if u:
            email = u.get("email") or ""
            role = app._get_role_cached(u["id"]) or "user"
    except Exception:
        try:
            from src.core import session

            fallback_user = session.get_current_user()
            if isinstance(fallback_user, str):
                email = fallback_user
            elif fallback_user:
                email = str(fallback_user)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao obter email de sessão fallback: %s", exc)
    email_str = str(email or "")
    return build_user_status_suffix(email_str, role)


def get_user_cached(app: App) -> Optional[dict[str, Any]]:
    """Retorna dados do usuário autenticado (delegado para SessionCache)."""
    user = app._session.get_user()

    # Hidratar AuthController se temos dados do usuário
    if user:
        try:
            uid = user["id"]
            org_id = app._session.get_org_id(uid)
            user_data = {
                "id": uid,
                "email": user["email"],
                "org_id": org_id,
            }
            app.auth.set_user_data(user_data)
        except Exception as e:
            log.warning("Não foi possível hidratar AuthController: %s", e)

    return user


# ═══════════════════════════════════════════════════════════════════════════
# EXIT CONFIRMATION
# ═══════════════════════════════════════════════════════════════════════════


def confirm_exit(app: App, *_) -> None:
    """Confirmação de saída da aplicação com shutdown limpo."""
    try:
        confirm = messagebox.askokcancel(
            "Sair",
            "Tem certeza de que deseja sair do RC Gestor?",
            parent=app,
            icon="question",
        )
    except Exception:
        confirm = True

    if confirm:
        try:
            # SHUTDOWN FIX: Setar flag de fechamento PRIMEIRO
            app._closing = True

            # Para lifecycle do HubScreen se existir
            if hasattr(app, "_hub_screen_instance") and app._hub_screen_instance:
                try:
                    if hasattr(app._hub_screen_instance, "_lifecycle"):
                        app._hub_screen_instance._lifecycle.stop()
                        log.debug("HubScreen lifecycle parado")
                except Exception as exc:  # noqa: BLE001
                    log.debug("Erro ao parar HubScreen lifecycle: %s", exc)

            # Para pollers do main_window se existir
            if hasattr(app, "_pollers") and app._pollers:
                try:
                    app._pollers.stop()
                    log.debug("Main window pollers parados")
                except Exception as exc:  # noqa: BLE001
                    log.debug("Erro ao parar main_window pollers: %s", exc)

            # Cancelar after jobs antes de destruir
            from src.ui.shutdown import cancel_all_after_jobs

            cancelled = cancel_all_after_jobs(app)
            log.debug("Shutdown limpo: %d after jobs cancelados", cancelled)

            # Quit e destroy
            app.quit()
            app.destroy()
        except Exception as exc:  # noqa: BLE001
            log.exception("Erro ao destruir janela: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# STATUS DOT
# ═══════════════════════════════════════════════════════════════════════════


def update_status_dot(app: App, is_online: Optional[bool]) -> None:
    """Atualiza o indicador visual de status online/offline."""
    from src.modules.main_window.views.state_helpers import compute_status_dot_style

    # Calcular estilo usando helper
    dot_style = compute_status_dot_style(is_online)

    # Aplicar símbolo
    try:
        if app.status_var_dot:
            app.status_var_dot.set(dot_style.symbol)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao definir texto do status_var_dot: %s", exc)

    # Aplicar estilo/cor
    try:
        if app.status_dot:
            app.status_dot.configure(bootstyle=dot_style.bootstyle)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao configurar bootstyle do status_dot: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# FOLDER UPLOAD
# ═══════════════════════════════════════════════════════════════════════════


def enviar_pasta_supabase(app: App) -> None:
    """Seleciona uma pasta e envia PDFs recursivamente para o Supabase."""
    from src.modules.uploads.uploader_supabase import send_folder_to_supabase

    try:
        send_folder_to_supabase(
            app,
            default_bucket=os.getenv("SUPABASE_BUCKET") or "rc-docs",
        )
    except Exception as exc:
        log.error("Erro ao enviar pasta para Supabase: %s", exc)
        messagebox.showerror(
            "Erro",
            f"Erro ao enviar pasta para Supabase:\n{exc}",
            parent=app,
        )


# ═══════════════════════════════════════════════════════════════════════════
# ORG & USER HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def get_org_id_cached_simple(app: App) -> Optional[str]:
    """Retorna org_id sem precisar de uid (para uso interno)."""
    try:
        user = app._session.get_user()
        if not user:
            return None
        uid = user.get("id")
        if not uid:
            return None
        return app._session.get_org_id(uid)
    except Exception:
        return None


def get_user_with_org(app: App) -> Optional[dict[str, Any]]:
    """Retorna dados do usuário com uid e email (para NotificationsService)."""
    try:
        user = app._session.get_user()
        if not user:
            return None

        return {
            "uid": user.get("id"),
            "email": user.get("email"),
        }
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# WINDOW MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════


def maximize_window(app: App) -> None:
    """Maximiza a janela principal. Chamado após login bem-sucedido."""
    try:
        app.state("zoomed")  # Maximiza a janela mantendo barra de título
        log.info("Janela maximizada (zoomed) após login")
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao maximizar janela com state('zoomed'): %s", exc)
        try:
            app.attributes("-zoomed", True)  # Fallback alternativo
            log.info("Janela maximizada usando attributes('-zoomed')")
        except Exception as exc2:  # noqa: BLE001
            log.debug("Falha ao maximizar janela com attributes: %s", exc2)


def close_chatgpt_window(app: App) -> None:
    """Fecha a janela do ChatGPT."""
    window = getattr(app, "_chatgpt_window", None)
    try:
        if window is not None and window.winfo_exists():
            window.destroy()
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao destruir janela do ChatGPT: %s", exc)
    finally:
        app._chatgpt_window = None


# ═══════════════════════════════════════════════════════════════════════════
# PLACEHOLDER & NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════


def show_placeholder_screen(app: App, title: str) -> Any:
    """Mostra tela placeholder (em desenvolvimento).

    Usa ScreenRouter para navegação correta (substitui frame anterior).
    O título é passado via atributo temporário app._placeholder_title.
    """
    # Armazenar título para factory acessar
    app._placeholder_title = title

    # Usar router para navegação correta
    frame = app._router.show("placeholder")

    # Side-effects: atualizar topbar
    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    # Atualizar nav._current para compatibilidade
    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# USER STATUS & POLLING
# ═══════════════════════════════════════════════════════════════════════════


def set_user_status(app: App, email: Optional[str], role: Optional[str] = None) -> None:
    """Define informações do usuário logado na StatusBar global."""
    try:
        app._user_cache = {"email": email, "id": email} if email else None
        app._role_cache = role
        app._refresh_status_display()
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao atualizar cache de usuário: %s", exc)
    app._refresh_status_display()


def poll_health_impl(app: App) -> None:
    """Implementação headless de health check (sem lógica de reagendamento)."""
    try:
        # FASE 5A PASSO 3: Guarda contra footer=None (deferred ainda não completou)
        if not hasattr(app, "footer") or app.footer is None:
            return

        from src.infra.supabase_client import get_supabase_state

        state, _ = get_supabase_state()
        app.footer.set_cloud(state)
        log.debug("Footer atualizado: cloud = %s", state)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao obter estado da nuvem no polling: %s", exc)


def refresh_current_view(app: App) -> None:
    """Recarrega a tela atual, se suportado pelo frame."""
    current = app.nav.current()
    if current is None:
        return

    if app._try_call(current, "carregar"):
        return
    app._try_call(current, "on_show")


def main_screen_frame(app: App):
    """Retorna o frame da tela principal de clientes, se disponível."""
    from src.modules.clientes.ui import ClientesV2Frame

    frame = getattr(app, "_main_frame_ref", None)
    if isinstance(frame, ClientesV2Frame):
        return frame

    # FASE 5A PASSO 3: Guarda contra nav=None (layout deferred ainda não completou)
    nav = getattr(app, "nav", None)
    if nav is None:
        return None

    current = nav.current()
    if isinstance(current, ClientesV2Frame):
        app._main_frame_ref = current
        return current
    return None
