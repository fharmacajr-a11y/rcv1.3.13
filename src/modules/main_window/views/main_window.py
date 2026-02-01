# -*- coding: utf-8 -*-
"""
Main Application Window (App class).

Este módulo implementa a janela principal do aplicativo Gestor de Clientes,
baseada em CustomTkinter (Microfase 24) com fallback para tkinter padrão.

ARQUITETURA DA CLASSE App:
══════════════════════════

A classe App herda de ctk.CTk (CustomTkinter) e orquestra os componentes principais:

1. INICIALIZAÇÃO (__init__)
   - Configuração de tema (CustomTkinter)
   - Configuração HiDPI para Linux/Windows
   - Criação de separadores visuais
   - TopBar com botão Home
   - Ícone da aplicação
   - MenuBar (AppMenuBar)
   - Container de conteúdo (NavigationController)
   - StatusFooter com indicadores
   - StatusMonitor para health checks
   - AuthController para autenticação
   - AppActions para delegação de ações
   - Keybindings globais

2. NAVEGAÇÃO
   - show_hub_screen(): Tela inicial (hub/notas)
   - show_main_screen(): Tela de clientes
   - show_passwords_screen(): Tela de senhas
   - show_cashflow_screen(): Tela de fluxo de caixa
   - show_placeholder_screen(): Telas vazias (em desenvolvimento)

3. AÇÕES DELEGADAS (via AppActions)
   - novo_cliente()
   - editar_cliente()
   - open_client_storage_subfolders() (alias ver_subpastas())
   - abrir_lixeira()
   - _excluir_cliente()
   - enviar_para_supabase()

4. GERENCIAMENTO DE SESSÃO (via SessionCache)
   - _get_user_cached()
   - _get_role_cached()
   - _get_org_id_cached()

5. STATUS & HEALTH CHECK
   - _handle_status_update(): Atualiza texto de status
   - _refresh_status_display(): Refresh completo do footer
   - _update_status_dot(): Atualiza indicador online/offline
   - _apply_online_state(): Aplica estado de conectividade
   - on_net_status_change(): Callback para mudanças de rede

6. TEMAS
   - _set_theme(): Troca de tema com restart
   - _handle_menu_theme_change(): Handler do menu

COMPONENTES EXTERNOS USADOS:
────────────────────────────
- TopBar: Barra superior com botão Home (src.ui.topbar)
- AppMenuBar: Menu principal (src.ui.menu_bar)
- StatusFooter: Rodapé com status (src.ui.status_footer)
- NavigationController: Gerenciador de navegação (src.core.navigation_controller)
- StatusMonitor: Monitor de health checks (src.core.status_monitor)
- AppActions: Delegação de ações (src.modules.main_window.app_actions)
- SessionCache: Cache de sessão (src.modules.main_window.session_service)

REFATORAÇÕES REALIZADAS:
────────────────────────
- QA-002 (2025-11-20): Extração de constantes e helpers para módulos separados
  * constants.py: APP_TITLE, APP_VERSION, timings, cores
  * helpers.py: resource_path, sha256_file, create_verbose_logger

TESTING:
────────
- Integração: testado via tests/test_ui_components.py
- Coverage: ~19% direto (muito código de UI)
- Smoke tests: scripts/dev_smoke.py

TODO (futuro):
──────────────
- Extrair lógica de inicialização de UI para métodos separados
- Criar tests unitários para métodos de status
- Considerar separar AppActions em múltiplos handlers (ClientActions, FileActions, etc.)
"""

# gui/main_window.py
import functools as _functools
import logging
import os
import sys
import tkinter as tk
from typing import Any, Callable, Optional

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

# Importar novo theme_manager (Microfase 24)
from src.ui.theme_manager import theme_manager as global_theme_manager

from src.infra.net_status import Status
from src.modules.main_window.views.state_helpers import (
    ConnectivityState,
    combine_status_display,
)
from src.modules.notas import HubFrame
from src.modules.clientes.ui import ClientesV2Frame
from src.modules.chatgpt.views.chatgpt_window import ChatGPTWindow
from src.modules.main_window.controller import create_frame, tk_report
from src.modules.main_window.session_service import SessionCache
from src.utils.validators import only_digits  # noqa: F401

# Imports internos do módulo main_window.views

NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

logger = logging.getLogger("app_gui")
log = logger

# Define base class segura
BaseApp = ctk.CTk if (HAS_CUSTOMTKINTER and ctk is not None) else tk.Tk


class App(BaseApp):  # type: ignore[misc]
    """Main application window using CustomTkinter as primary theme system.

    MICROFASE 24: Migração para CustomTkinter como tema principal.
    - Usa ctk.CTk como base quando CustomTkinter disponível
    - Fallback para tk.Tk quando CustomTkinter não disponível
    - Remove sistema de temas legados (ttkbootstrap)
    - Usa apenas appearance mode (light/dark) + color theme (blue/dark-blue/green)
    """

    def __init__(self, start_hidden: bool = False) -> None:
        """Inicializa a janela principal do aplicativo.

        Toda a lógica de setup foi extraída para main_window_bootstrap.py
        para reduzir a complexidade do __init__.
        """
        # MICROFASE 24: Inicializar theme manager global ANTES de criar widgets
        try:
            global_theme_manager.initialize()
            log.info("Theme manager global inicializado")
        except Exception as exc:
            log.warning("Falha ao inicializar theme manager: %s", exc)

        # MICROFASE 24: Usar CustomTkinter como base principal
        if HAS_CUSTOMTKINTER and ctk is not None:
            try:
                # Inicializar com CTk (CustomTkinter)
                ctk.CTk.__init__(self)
                log.info("Janela inicializada com CustomTkinter (ctk.CTk)")
                self._using_customtkinter = True

                # MICROFASE 24.1: Definir master no theme_manager APÓS criar a janela
                try:
                    global_theme_manager.set_master(self)
                except Exception as exc:
                    log.debug("Falha ao definir master no theme_manager: %s", exc)
            except Exception as e:
                log.warning(
                    "Falha ao inicializar com CustomTkinter: %s. Fallback para tk.Tk.",
                    e,
                )
                # Fallback para tk.Tk
                tk.Tk.__init__(self)
                log.info("Janela inicializada com tk.Tk (fallback)")
                self._using_customtkinter = False
        else:
            # CustomTkinter não disponível: usar tk.Tk
            tk.Tk.__init__(self)
            log.info("CustomTkinter não disponível, usando tk.Tk")
            self._using_customtkinter = False

        # MICROFASE 31: Removido configuração Style legado (ZERO em runtime)

        # BUGFIX-UX-STARTUP-HUB-001 (B1): Ocultar janela IMEDIATAMENTE para evitar flash (0,0)
        # Deve ser feito ANTES de qualquer outra configuração
        if start_hidden:
            try:
                self.withdraw()
                # Anti-flash adicional: geometry off-screen temporária
                self.geometry("1x1+10000+10000")
                self.attributes("-alpha", 0.0)
                if os.getenv("RC_DEBUG_STARTUP_UI") == "1":
                    log.info(
                        "[UI] Janela ocultada EARLY (start_hidden=True): state=%s, viewable=%s",
                        self.state(),
                        self.winfo_viewable(),
                    )
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao ocultar janela early: %s", exc)

        # Configurar HiDPI após criação do Tk
        try:
            from src.utils.helpers import configure_hidpi_support

            configure_hidpi_support(self)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao configurar HiDPI: %s", exc)

        # MICROFASE 24: Remover configuração de tema customizado ttkbootstrap
        # Agora CustomTkinter gerencia cores automaticamente

        # Setup básico antes do bootstrap
        # P0 #5: Instalar handler global de exceções Tkinter (opcional, controlado por env)
        try:
            from src.core.tk_exception_handler import install_global_exception_handler

            install_global_exception_handler(self)
        except Exception as exc:  # noqa: BLE001
            # Fallback: usar handler simples original
            log.debug("Handler de exceção customizado indisponível, usando fallback: %s", exc)
            self.report_callback_exception = tk_report

        # MICROFASE 24: Manter tema_atual para compatibilidade com código legado
        current_mode = global_theme_manager.get_current_mode()
        self.tema_atual = current_mode  # "light" ou "dark"
        self._restarting = False
        self._start_hidden = start_hidden
        self._closing = False  # Flag para prevenir novos after() jobs durante shutdown

        # Cache de sessão (user, role, org_id) delegado para SessionCache
        self._session: SessionCache = SessionCache()

        # Estado de conectividade
        self._connectivity_state: ConnectivityState = ConnectivityState(
            is_online=True,
            offline_alerted=False,
        )

        # Cache de telas
        self._hub_screen_instance: Optional[HubFrame] = None
        self._chatgpt_window: Optional[ChatGPTWindow] = None

        # ═══════════════════════════════════════════════════════════════
        # Bootstrap: toda a inicialização foi extraída para módulo separado
        # ═══════════════════════════════════════════════════════════════
        from src.modules.main_window.views.main_window_bootstrap import bootstrap_main_window

        # BUGFIX-UX-STARTUP-HUB-001 (A2): Bind de debug para tracking de eventos de mapa
        if os.getenv("RC_DEBUG_STARTUP_UI") == "1":
            try:
                self.bind(
                    "<Map>",
                    lambda e: log.info("[UI] <Map> event: geometry=%s, state=%s", self.geometry(), self.state()),
                    add="+",
                )
                self.bind("<Visibility>", lambda e: log.info("[UI] <Visibility> event: state=%s", e.state), add="+")
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao bind debug events: %s", exc)

        bootstrap_main_window(self)

    # -------- Properties para compatibilidade com testes (delegam para pollers) --------
    @property
    def _notifications_poll_job_id(self) -> str | None:
        """Job ID de polling de notificações (compatibilidade com testes)."""
        return self._pollers.notifications_job_id if hasattr(self, "_pollers") else None

    @property
    def _status_refresh_job_id(self) -> str | None:
        """Job ID de refresh de status (compatibilidade com testes)."""
        return self._pollers.status_job_id if hasattr(self, "_pollers") else None

    @property
    def _health_poll_job_id(self) -> str | None:
        """Job ID de health check (compatibilidade com testes)."""
        return self._pollers.health_job_id if hasattr(self, "_pollers") else None

    def show_frame(self, frame_cls: Any, **kwargs: Any) -> Any:
        # FASE 5A PASSO 3: Guarda contra nav=None (deferred ainda não completou)
        if not hasattr(self, "nav") or self.nav is None:
            log.warning("show_frame chamado antes de nav estar pronto")
            return None
        
        frame = self.nav.show_frame(frame_cls, **kwargs)
        try:
            self._update_topbar_state(frame)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar estado da topbar: %s", exc)
        return frame

    def _frame_factory(self, frame_cls: Any, options: dict[str, Any]) -> Any:
        return create_frame(self, frame_cls, options)

    def set_pick_mode_active(self, active: bool) -> None:
        """Ativa/desativa elementos de menu durante modo seleção de clientes (FIX-CLIENTES-005)."""
        if hasattr(self, "_topbar") and self._topbar is not None:
            try:
                self._topbar.set_pick_mode_active(active)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao atualizar topbar pick mode: %s", exc)

    def _update_topbar_state(self, frame_or_cls: Any) -> None:
        """Atualiza estado da topbar (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.update_topbar_state(self, frame_or_cls)

    def _main_screen_frame(self) -> Optional["ClientesV2Frame"]:
        """Retorna frame da tela de clientes (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.main_screen_frame(self)

    def _selected_main_values(self) -> Optional[tuple[Any, ...]]:
        frame = self._main_screen_frame()
        if frame is None:
            return None
        values = frame._get_selected_values()
        if values is None:
            return None
        return tuple(values)

    def carregar(self) -> None:
        frame = self._main_screen_frame()
        if frame:
            frame.carregar()

    def _try_call(self, frame: Any, method: str) -> bool:
        fn = getattr(frame, method, None)
        if not callable(fn):
            return False
        try:
            fn()
            return True
        except Exception:
            log.exception("Erro ao atualizar a tela atual com %s", method)
            return False

    def refresh_current_view(self) -> None:
        """Recarrega a tela atual (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.refresh_current_view(self)

    def refresh_clients_count_async(self, auto_schedule: bool = True) -> None:
        """Atualiza contagem de clientes (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.refresh_clients_count_async(self, auto_schedule)

    def _maximize_window(self) -> None:
        """Maximiza a janela principal (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.maximize_window(self)

    def show_hub_screen(self) -> Any:
        """Mostra o hub inicial."""
        from src.modules.main_window.views.main_window_screens import show_hub_screen

        return show_hub_screen(self)

    def show_main_screen(self) -> Any:
        """Mostra a tela principal de clientes."""
        from src.modules.main_window.views.main_window_screens import show_main_screen

        return show_main_screen(self)

    def show_placeholder_screen(self, title: str) -> Any:
        """Mostra tela placeholder (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.show_placeholder_screen(self, title)

    def show_cashflow_screen(self) -> Any:
        """Mostra a tela de fluxo de caixa."""
        from src.modules.main_window.views.main_window_screens import show_cashflow_screen

        return show_cashflow_screen(self)

    def show_sites_screen(self) -> Any:
        """Mostra a tela de gerenciamento de sites."""
        from src.modules.main_window.views.main_window_screens import show_sites_screen

        return show_sites_screen(self)

    def open_clients_picker(
        self,
        on_pick: Callable[[dict[str, Any]], None],
        *,
        banner_text: str | None = None,
        return_to: Callable[[], None] | None = None,
    ) -> None:
        """Compat helper legado (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.open_clients_picker(self, on_pick, banner_text=banner_text, return_to=return_to)

    def _on_menu_logout(self) -> None:
        """Handler do menu Sair (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.on_menu_logout(self)

    # ---------- Monkey patch para Combobox.*
    @staticmethod
    def _patch_style_element_create(style: Any) -> None:
        """Patching de segurança (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.patch_style_element_create(style)

    # ---------- Confirmação de saída ----------
    def _confirm_exit(self, *_):
        """Confirmação de saída (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.confirm_exit(self, *_)

    # ---------- Tema ----------
    # MICROFASE 24: Remover _set_theme e _handle_menu_theme_change
    # Substituir por toggle simples light/dark
    def _handle_toggle_theme(self) -> None:
        """Toggle entre light e dark mode (Microfase 24)."""
        try:
            new_mode = global_theme_manager.toggle_mode()
            self.tema_atual = new_mode
            log.info(f"Tema alternado para: {new_mode}")
        except Exception as exc:
            log.exception("Falha ao alternar tema: %s", exc)
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Falha ao alternar tema: {exc}", parent=self)

    # Manter métodos legados para compatibilidade com código antigo
    def _set_theme(self, new_theme: str) -> None:
        """DEPRECATED: Mantido para compatibilidade (Microfase 24)."""
        log.warning("_set_theme() está deprecated. Use _handle_toggle_theme() para light/dark.")

    def _handle_menu_theme_change(self, name: str) -> None:
        """DEPRECATED: Mantido para compatibilidade (Microfase 24)."""
        log.warning("_handle_menu_theme_change() está deprecated. Use _handle_toggle_theme() para light/dark.")

    # ---------- Integração com Health Check e Sessão ----------
    def _wire_session_and_health(self):
        """Conecta o health check do Supabase ao rodapé para atualização automática."""
        from src.modules.main_window.views.main_window_handlers import wire_session_and_health

        return wire_session_and_health(self)

    def _on_login_success(self, session):
        """Atualiza o rodapé com o email do usuário após login bem-sucedido."""
        try:
            # FASE 5A PASSO 3: Guarda contra footer=None (deferred ainda não completou)
            if not hasattr(self, "footer") or self.footer is None:
                log.debug("Footer ainda não pronto, pulando atualização de usuário")
                return
            
            email = getattr(getattr(session, "user", None), "email", None)
            self.footer.set_user(email)
        except Exception as e:
            log.warning("Erro ao atualizar usuário no rodapé: %s", e)

    # ---------- Helpers de Status ----------
    def _handle_status_update(self, base_text: str, is_online: Optional[bool] = None) -> None:
        self._status_base_text = base_text.strip()
        self._apply_online_state(is_online)
        self._update_status_dot(is_online)
        self._refresh_status_display()

    def _refresh_status_display(self) -> None:
        base = self._status_base_text or ""
        suffix = self._user_status_suffix()
        display = combine_status_display(base, suffix)
        self.status_var_text.set(display)

    def _user_status_suffix(self) -> str:
        """Retorna sufixo de status do usuário (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.user_status_suffix(self)

    def _update_status_dot(self, is_online: Optional[bool]) -> None:
        """Atualiza indicador de status (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.update_status_dot(self, is_online)

    def _apply_online_state(self, is_online: Optional[bool]) -> None:
        """Aplica estado de conectividade (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.apply_online_state(self, is_online)

    def on_net_status_change(self, st: Status) -> None:
        is_online = st == Status.ONLINE
        self._apply_online_state(is_online)
        self._update_status_dot(is_online)

    # ---------- API pública para status ----------
    def set_cloud_status(self, online: bool) -> None:
        """Define o status da nuvem (online/offline) na StatusBar global."""
        try:
            if self._status_monitor:
                self._status_monitor.set_cloud_status(online)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao definir status da nuvem: %s", exc)

    def set_user_status(self, email: Optional[str], role: Optional[str] = None) -> None:
        """Define informações do usuário (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.set_user_status(self, email, role)

    def _update_user_status(self) -> None:
        self._refresh_status_display()

    def _schedule_user_status_refresh(self) -> None:
        """DEPRECATED: Agenda refresh (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.schedule_user_status_refresh(self)

    def novo_cliente(self) -> None:
        """Delegador para AppActions.novo_cliente."""
        self._actions.novo_cliente()

    def editar_cliente(self) -> None:
        """Delegador para AppActions.editar_cliente."""
        self._actions.editar_cliente()

    def open_client_storage_subfolders(self) -> None:
        """Delegador para AppActions.open_client_storage_subfolders."""
        self._actions.open_client_storage_subfolders()

    def ver_subpastas(self) -> None:
        """DEPRECATED: mantenha compatibilidade com o nome antigo."""
        self.open_client_storage_subfolders()

    def abrir_obrigacoes_cliente(self) -> None:
        """Delegador para AppActions.abrir_obrigacoes_cliente."""
        self._actions.abrir_obrigacoes_cliente()

    def abrir_lixeira(self) -> None:
        """Delegador para AppActions.abrir_lixeira."""
        self._actions.abrir_lixeira()

    def _excluir_cliente(self) -> None:
        """Delegador para AppActions._excluir_cliente."""
        self._actions._excluir_cliente()

    # -------- Hook para obter prefix do cliente (opcional) --------
    def get_current_client_storage_prefix(self) -> str:
        """Retorna o prefix do cliente selecionado (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.get_current_client_storage_prefix(self)

    # -------- Upload para Supabase (sistema avançado com fallback) --------
    def enviar_para_supabase(self) -> None:
        """Delegador para AppActions.enviar_para_supabase."""
        self._actions.enviar_para_supabase()

    def enviar_pasta_supabase(self) -> None:
        """Seleciona uma pasta e envia PDFs (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.enviar_pasta_supabase(self)

    def run_pdf_batch_converter(self) -> None:
        """Delegador para AppActions.run_pdf_batch_converter."""
        self._actions.run_pdf_batch_converter()

    def _open_pdf_viewer_empty(self) -> None:
        """Abre o visualizador de PDF sem arquivo inicial."""
        try:
            from src.modules.pdf_preview import open_pdf_viewer

            open_pdf_viewer(self, pdf_path=None, display_name="Visualizador de PDF")
        except Exception as exc:  # noqa: BLE001
            log.error("Erro ao abrir visualizador de PDF vazio: %s", exc)

    def open_chatgpt_window(self) -> None:
        """Abre ou traz para frente a janela do ChatGPT (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.open_chatgpt_window(self)

    def _on_chatgpt_close(self) -> None:
        """Callback chamado quando a janela do ChatGPT é fechada."""
        self._chatgpt_window = None

    def _close_chatgpt_window(self) -> None:
        """Fecha a janela do ChatGPT (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.close_chatgpt_window(self)

    def _on_chatgpt_destroy(self, window: ChatGPTWindow) -> None:
        if self._chatgpt_window is window:
            self._chatgpt_window = None

    # -------- Notificações --------
    def _poll_notifications(self) -> None:
        """DEPRECATED: Polling periódico de notificações (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.poll_notifications(self)

    def _show_notification_toast(self, count: int) -> None:
        """Mostra toast do Windows quando chegar nova notificação."""
        from src.modules.main_window.views.main_window_handlers import show_notification_toast

        return show_notification_toast(self, count)

    # -------- Implementações headless de polling (usadas por MainWindowPollers) --------
    def _poll_notifications_impl(self) -> None:
        """Implementação headless de polling de notificações (sem lógica de reagendamento)."""
        from src.modules.main_window.views.main_window_handlers import poll_notifications_impl

        return poll_notifications_impl(self)

    def _poll_health_impl(self) -> None:
        """Implementação headless de health check (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.poll_health_impl(self)

    def _refresh_status_impl(self) -> None:
        """Implementação headless de refresh de status (sem lógica de reagendamento)."""
        self._update_user_status()

    def _on_notifications_clicked(self) -> None:
        """Callback quando usuário clica no botão de notificações."""
        from src.modules.main_window.views.main_window_handlers import on_notifications_clicked

        return on_notifications_clicked(self)

    def _mark_all_notifications_read(self) -> bool:
        """Marca todas notificações como lidas."""
        from src.modules.main_window.views.main_window_handlers import mark_all_notifications_read

        return mark_all_notifications_read(self)

    def _delete_notification_for_me(self, notification_id: str) -> bool:
        """Exclui uma notificação apenas para o usuário atual (soft delete).

        Args:
            notification_id: ID da notificação a excluir

        Returns:
            True se sucesso, False caso contrário
        """
        from src.modules.main_window.views.main_window_handlers import delete_notification_for_me

        return delete_notification_for_me(self, notification_id)

    def _delete_all_notifications_for_me(self) -> bool:
        """Exclui todas notificações apenas para o usuário atual (soft delete).

        Returns:
            True se sucesso, False caso contrário
        """
        from src.modules.main_window.views.main_window_handlers import delete_all_notifications_for_me

        return delete_all_notifications_for_me(self)

    def _toggle_mute_notifications(self, muted: bool) -> None:
        """Toggle do estado de silenciar notificações.

        Args:
            muted: True para silenciar, False para permitir toasts
        """
        self._mute_notifications = muted
        status = "silenciadas" if muted else "ativadas"
        log.info("[Notifications] Notificações %s", status)

    def _get_org_id_cached_simple(self) -> Optional[str]:
        """Retorna org_id sem precisar de uid (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.get_org_id_cached_simple(self)

    def _get_user_with_org(self) -> Optional[dict[str, Any]]:
        """Retorna dados do usuário com uid e email (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.get_user_with_org(self)

    # -------- Sessao / usuario --------
    def _get_user_cached(self) -> Optional[dict[str, Any]]:
        """Retorna dados do usuário autenticado (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.get_user_cached(self)

    def _get_role_cached(self, uid: str) -> str:
        """Retorna role do usuário (delegado para SessionCache)."""
        return self._session.get_role(uid)

    def _get_org_id_cached(self, uid: str) -> Optional[str]:
        """Retorna org_id do usuário (delegado para SessionCache)."""
        return self._session.get_org_id(uid)

    # -------- Diversos --------
    def _restart_app(self) -> None:
        self._restarting = True
        self.destroy()
        os.execv(sys.executable, [sys.executable, "-m", "main"])  # nosec B606 - reinício local do app com argumentos controlados

    def destroy(self) -> None:
        """Limpeza e destruição do MainWindow.

        MICROFASE 24.1: Shutdown limpo com idempotência.
        """
        from . import main_window_actions as actions

        # Executar cleanup (com idempotência)
        actions.destroy_window(self)

        # MICROFASE 24.1: Chamar quit() antes de destroy() para parar mainloop
        try:
            self.quit()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha em quit(): %s", exc)

        # Chamar destroy do pai uma única vez
        try:
            super().destroy()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha em super().destroy(): %s", exc)

        if getattr(self, "_restarting", False):
            log.info("App reiniciado (troca de tema).")
        else:
            log.info("App fechado.")

    def _show_changelog(self) -> None:
        """Exibe o changelog (wrapper para main_window_actions)."""
        from . import main_window_actions as actions

        return actions.show_changelog(self)


# ---- Verbose logs (opcional, controlado por RC_VERBOSE=1) ----

_VERB = (os.getenv("RC_VERBOSE") or "").strip().lower() in {"1", "true", "yes", "on"}


def _log_call(fn):
    log_verb = logging.getLogger("ui.actions")

    @_functools.wraps(fn)
    def _wrap(self, *a, **kw):
        if _VERB:
            log_verb.info("CALL %s", fn.__name__)
        try:
            return fn(self, *a, **kw)
        except Exception:
            log_verb.exception("ERROR in %s", fn.__name__)
            raise

    return _wrap


try:
    App.novo_cliente = _log_call(App.novo_cliente)
    App.editar_cliente = _log_call(App.editar_cliente)
    App.open_client_storage_subfolders = _log_call(App.open_client_storage_subfolders)
    App.ver_subpastas = _log_call(App.ver_subpastas)
    App.enviar_para_supabase = _log_call(App.enviar_para_supabase)
except Exception as exc:  # noqa: BLE001
    log.debug("Falha ao aplicar decoradores de log: %s", exc)
