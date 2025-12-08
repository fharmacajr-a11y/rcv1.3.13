# -*- coding: utf-8 -*-
"""
Main Application Window (App class).

Este módulo implementa a janela principal do aplicativo Gestor de Clientes,
baseada em ttkbootstrap (tema moderno do Tkinter).

ARQUITETURA DA CLASSE App:
══════════════════════════

A classe App herda de tb.Window e orquestra os componentes principais:

1. INICIALIZAÇÃO (__init__)
   - Configuração de tema (ttkbootstrap com fallback para ttk padrão)
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
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb

from infra import supabase_auth
from infra.net_status import Status
from src import app_status
from src.modules.main_window.views.state_helpers import (
    ConnectivityState,
    build_app_title,
    build_user_status_suffix,
    combine_status_display,
    compute_connectivity_state,
    compute_status_dot_style,
    compute_theme_config,
    format_version_string,
    should_show_offline_alert,
)
from src.modules.login.service import AuthController
from src.modules.notas import HubFrame
from src.core.keybindings import bind_global_shortcuts
from src.core.navigation_controller import NavigationController
from src.core.status_monitor import StatusMonitor
from src.modules.clientes import ClientesFrame
from src.modules.clientes import service as clientes_service
from src.modules.chatgpt.views.chatgpt_window import ChatGPTWindow
from src.modules.main_window.app_actions import AppActions
from src.modules.main_window.controller import create_frame, navigate_to, start_client_pick_mode, tk_report
from src.modules.main_window.session_service import SessionCache
from src.ui.menu_bar import AppMenuBar
from src.ui.topbar import TopBar
from src.ui.window_policy import apply_fit_policy
from src.ui import custom_dialogs
from src.utils import themes
from src.utils.themes import apply_combobox_style
from src.utils.theme_manager import theme_manager
from src.utils.validators import only_digits  # noqa: F401
from src.modules.uploads.uploader_supabase import send_folder_to_supabase

# Imports internos do módulo main_window.views
from .constants import (
    APP_ICON_PATH,
    APP_TITLE,
    APP_VERSION,
    HEALTH_POLL_INTERVAL,
    INITIAL_STATUS_DELAY,
    STATUS_REFRESH_INTERVAL,
)
from .helpers import resource_path

NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

logger = logging.getLogger("app_gui")
log = logger


class App(tb.Window):
    """Main ttkbootstrap window for the Gestor de Clientes desktop application."""

    def __init__(self, start_hidden: bool = False) -> None:
        _theme_name = themes.load_theme()

        # Try to initialize with ttkbootstrap theme, fallback to standard ttk
        try:
            super().__init__(themename=_theme_name)
        except Exception as e:
            log.warning(
                "Falha ao aplicar tema '%s': %s. Fallback ttk padrão.",
                _theme_name,
                e,
            )
            # Fallback to standard tk.Tk if ttkbootstrap fails
            try:
                tk.Tk.__init__(self)
                # Initialize standard ttk Style (not ttkbootstrap)
                style = ttk.Style()
                # Use a valid ttk theme
                available_themes = style.theme_names()
                if "clam" in available_themes:
                    style.theme_use("clam")
                elif available_themes:
                    style.theme_use(available_themes[0])
                log.info("Initialized with standard Tk/ttk (theme: %s)", style.theme_use())
            except Exception as fallback_error:
                log.error("Critical: Failed to initialize GUI: %s", fallback_error)
                raise

        # Configurar HiDPI após criação do Tk (Linux) ou antes (Windows já foi no app_gui)
        # No Linux, ttkbootstrap Window já vem com hdpi=True por padrão em versões recentes
        # Mas vamos garantir configuração explícita se necessário
        try:
            from src.utils.helpers import configure_hidpi_support

            configure_hidpi_support(self)  # Linux: aplica scaling
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao configurar HiDPI: %s", exc)

        # Criar separadores horizontais (idempotentes)
        # Separador 1: logo abaixo do menu (antes da toolbar)
        if not hasattr(self, "sep_menu_toolbar") or self.sep_menu_toolbar is None:
            self.sep_menu_toolbar = ttk.Separator(self, orient="horizontal")
            self.sep_menu_toolbar.pack(side="top", fill="x", pady=0)

        self._topbar: TopBar = TopBar(
            self,
            on_home=self.show_hub_screen,
            on_pdf_converter=self.run_pdf_batch_converter,
            on_pdf_viewer=self._open_pdf_viewer_empty,
            on_chatgpt=self.open_chatgpt_window,
            on_sites=self.show_sites_screen,
        )
        self._topbar.pack(side="top", fill="x")
        self._pdf_viewer_window = None
        self._pdf_viewer_signature: Optional[str] = None

        # Separador 2: logo abaixo da toolbar (antes do conteúdo principal)
        if not hasattr(self, "sep_toolbar_main") or self.sep_toolbar_main is None:
            self.sep_toolbar_main = ttk.Separator(self, orient="horizontal")
            self.sep_toolbar_main.pack(side="top", fill="x", pady=0)

        if start_hidden:
            try:
                self.withdraw()
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao ocultar janela: %s", exc)

        try:
            icon_path = resource_path(APP_ICON_PATH)
            log.info("Tentando aplicar ícone da aplicação: %s", icon_path)
            if os.path.exists(icon_path):
                try:
                    self.iconbitmap(icon_path)
                    log.info("iconbitmap aplicado com sucesso: %s", icon_path)
                except Exception:
                    log.warning("iconbitmap falhou, tentando iconphoto para %s", icon_path, exc_info=True)
                    try:
                        img = tk.PhotoImage(file=icon_path)
                        self.iconphoto(True, img)
                        log.info("iconphoto aplicado com sucesso: %s", icon_path)
                    except Exception:
                        log.error("iconphoto também falhou ao aplicar ícone: %s", icon_path, exc_info=True)
            else:
                log.warning("Ícone %s não encontrado em: %s", APP_ICON_PATH, icon_path)
        except Exception:
            log.exception("Falha ao aplicar ícone da aplicação")

        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        # Menubar com AppMenuBar
        self._menu: AppMenuBar = AppMenuBar(
            self,
            on_home=self.show_hub_screen,
            on_refresh=self.refresh_current_view,
            on_quit=self._on_menu_logout,
            on_change_theme=self._handle_menu_theme_change,
        )
        self._menu.attach()
        try:
            self._menu.refresh_theme(_theme_name)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar tema do menu: %s", exc)

        try:
            # Criar UMA ÚNICA instância de Style para o app
            app_style = tb.Style()
            app_style.theme_use(_theme_name)
            # Passar a MESMA instância para apply_combobox_style
            apply_combobox_style(app_style)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao aplicar tema via Style: %s", exc)

        self.report_callback_exception = tk_report

        # Usar helper para construir título
        version_str = format_version_string(APP_VERSION)
        window_title = build_app_title(APP_TITLE, version_str)
        self.title(window_title)

        # --- Aplicar política Fit-to-WorkArea ---
        apply_fit_policy(self)

        # --- Maximização adiada para _maximize_window() (chamado após login) ---
        # NOTA: Não maximizar aqui durante __init__ para evitar mostrar a janela
        # antes do splash/login terminarem. A maximização é feita em _maximize_window().

        self.tema_atual = _theme_name
        self._restarting = False

        # Cache de sessão (user, role, org_id) delegado para SessionCache
        self._session: SessionCache = SessionCache()

        # Estado de conectividade usando helper
        self._connectivity_state: ConnectivityState = ConnectivityState(
            is_online=True,
            offline_alerted=False,
        )

        # Cache da instância única do Hub (evita tela branca ao navegar)
        self._hub_screen_instance: Optional[HubFrame] = None

        # Cache da instância única da tela de Senhas (evita tela branca ao navegar)
        self._passwords_screen_instance: Optional[Any] = None
        self._chatgpt_window: Optional[ChatGPTWindow] = None

        # Cliente Supabase (lazy-loaded quando necessário)
        try:
            from infra.supabase_client import supabase

            self.supabase: Any = supabase
        except Exception:
            self.supabase = None
        self._client: Any = getattr(self, "supabase", None)

        self.clients_count_var: tk.StringVar = tk.StringVar(master=self, value="0 clientes")
        self.status_var_dot: tk.StringVar = tk.StringVar(master=self, value="")
        self.status_var_text: tk.StringVar = tk.StringVar(
            master=self,
            value=(getattr(app_status, "status_text", None) or "LOCAL"),
        )
        self.status_dot = None  # type: ignore[assignment]
        self.status_lbl = None  # type: ignore[assignment]

        self._status_base_text = self.status_var_text.get() or ""
        self._status_monitor: Optional[StatusMonitor] = None
        self._main_frame_ref: Optional[ClientesFrame] = None
        self._main_loaded = False

        try:
            theme_manager.register_window(self)
            self._theme_listener: Optional[Callable[[str], None]] = lambda t: themes.apply_button_styles(self, theme=t)
            theme_manager.add_listener(self._theme_listener)
        except Exception:
            self._theme_listener = None

        log.info("App iniciado com tema: %s", self.tema_atual)

        self._content_container: tb.Frame = tb.Frame(self)
        self._content_container.pack(fill="both", expand=True)
        self.nav: NavigationController = NavigationController(
            self._content_container, frame_factory=self._frame_factory
        )

        # --- StatusBar Global (sempre visível no rodapé) ---
        from src.ui.status_footer import StatusFooter

        self.footer: StatusFooter = StatusFooter(self, show_trash=False)
        self.footer.pack(side="bottom", fill="x")
        self.footer.set_count(0)
        self.footer.set_user(None)
        self.footer.set_cloud("UNKNOWN")

        self._status_monitor = StatusMonitor(self._handle_status_update, app_after=self.after)
        try:
            self._status_monitor.set_cloud_only(NO_FS)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao configurar cloud_only no StatusMonitor: %s", exc)
        self._status_monitor.start()

        # Conectar health check ao rodapé
        self._wire_session_and_health()

        # Auth
        self.auth = AuthController(on_user_change=lambda username: self._refresh_status_display())

        # Actions helper (Fase 3: delegação de ações de clientes, lixeira, etc.)
        self._actions = AppActions(self, logger=log)

        # Keybindings
        bind_global_shortcuts(
            self,
            {
                "quit": self.destroy,
                "refresh": self.refresh_current_view,
                "new": self.novo_cliente,
                "edit": self.editar_cliente,
                "delete": self._excluir_cliente,
                "upload": self.enviar_para_supabase,
                "lixeira": self.abrir_lixeira,
                "subpastas": self.open_client_storage_subfolders,
                "hub": self.show_hub_screen,
                "find": lambda: getattr(self, "_main_frame_ref", None)
                and getattr(self._main_frame_ref, "_buscar", lambda: None)(),
            },
        )

        self.after(INITIAL_STATUS_DELAY, self._schedule_user_status_refresh)
        self.bind("<FocusIn>", lambda e: self._update_user_status(), add="+")
        # REMOVIDO: self.show_hub_screen() - agora é chamado em app_gui.py APÓS login bem-sucedido

    def show_frame(self, frame_cls: Any, **kwargs: Any) -> Any:
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
        hub_cls = HubFrame
        is_hub = False
        try:
            # classe, instância ou callable (lambda) que retorna frame
            if isinstance(frame_or_cls, type):
                is_hub = frame_or_cls is hub_cls
            elif callable(frame_or_cls):
                # se for factory/lambda, checa o current()
                cur = self.nav.current()
                is_hub = isinstance(cur, hub_cls) if cur is not None else False
            else:
                is_hub = isinstance(frame_or_cls, hub_cls)

            # redundância segura: também checa o frame atual do controlador
            cur = self.nav.current()
            if cur is not None:
                is_hub = is_hub or isinstance(cur, hub_cls)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao verificar se é hub: %s", exc)

        try:
            self._topbar.set_is_hub(is_hub)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar estado is_hub na topbar: %s", exc)

        try:
            self._menu.set_is_hub(is_hub)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar estado is_hub no menu: %s", exc)

    def _main_screen_frame(self) -> Optional[ClientesFrame]:
        frame = getattr(self, "_main_frame_ref", None)
        if isinstance(frame, ClientesFrame):
            return frame
        current = self.nav.current()
        if isinstance(current, ClientesFrame):
            self._main_frame_ref = current
            return current
        return None

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
        """Recarrega a tela atual, se suportado pelo frame."""
        current = self.nav.current()
        if current is None:
            return

        if self._try_call(current, "carregar"):
            return
        if self._try_call(current, "reload_passwords"):
            return
        self._try_call(current, "on_show")

    def refresh_clients_count_async(self, auto_schedule: bool = True) -> None:
        """
        Atualiza a contagem de clientes do Supabase de forma assíncrona.
        Usa threading para não travar a UI.

        Args:
            auto_schedule: Se True, agenda próxima atualização automática em 30s
        """

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
                self.after(0, lambda: self.clients_count_var.set(text))
                self.after(0, lambda: self.footer.set_count(total))
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao atualizar contagem de clientes: %s", exc)

            # Auto-refresh: agenda próxima atualização em 30s
            if auto_schedule:
                try:
                    self.after(
                        30000,
                        lambda: self.refresh_clients_count_async(auto_schedule=True),
                    )
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao agendar auto-refresh de contagem: %s", exc)

        threading.Thread(target=_work, daemon=True).start()

    def _maximize_window(self) -> None:
        """Maximiza a janela principal. Chamado após login bem-sucedido."""
        try:
            self.state("zoomed")  # Maximiza a janela mantendo barra de título
            log.info("Janela maximizada (zoomed) após login")
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao maximizar janela com state('zoomed'): %s", exc)
            try:
                self.attributes("-zoomed", True)  # Fallback alternativo
                log.info("Janela maximizada usando attributes('-zoomed')")
            except Exception as exc2:  # noqa: BLE001
                log.debug("Falha ao maximizar janela com attributes: %s", exc2)

    def show_hub_screen(self) -> Any:
        """Mostra o hub inicial.

        A centralização da janela principal é feita apenas por apply_fit_policy()
        no __init__, que usa a API nativa de janela. Aqui só navegamos para o hub.
        """
        return navigate_to(self, "hub")

    def show_main_screen(self) -> Any:
        return navigate_to(self, "main")

    def show_placeholder_screen(self, title: str) -> Any:
        return navigate_to(self, "placeholder", title=title)

    def show_passwords_screen(self) -> Any:
        return navigate_to(self, "passwords")

    def show_cashflow_screen(self) -> Any:
        return navigate_to(self, "cashflow")

    def show_sites_screen(self) -> Any:
        return navigate_to(self, "sites")

    def open_clients_picker(
        self,
        on_pick: Callable[[dict[str, Any]], None],
        *,
        banner_text: str | None = None,
        return_to: Callable[[], None] | None = None,
    ) -> None:
        """Compat helper legado. Prefira start_client_pick_mode em novos fluxos."""
        if return_to is None:

            def _return_to_passwords() -> None:
                navigate_to(self, "passwords")

            return_to = _return_to_passwords
        effective_banner = banner_text or "Modo seleção: escolha um cliente para continuar"
        start_client_pick_mode(
            self,
            on_client_picked=on_pick,
            banner_text=effective_banner,
            return_to=return_to,
        )

    def _on_menu_logout(self) -> None:
        """Handler do menu Sair: confirmação + logout + fechar app."""
        title = "Encerrar sessão"
        message = (
            "Tem certeza que deseja encerrar a sessão atual?\n\n"
            "Você precisará informar a senha novamente ao abrir o aplicativo."
        )
        try:
            confirm = custom_dialogs.ask_ok_cancel(self, title, message)
        except Exception:
            try:
                confirm = messagebox.askyesno(title, message, parent=self)
            except Exception:
                confirm = True
        if not confirm:
            return

        try:
            supabase_auth.logout(self._client)
        except Exception:
            log.warning("Falha ao realizar logout", exc_info=True)

        try:
            self.destroy()
        except Exception as exc:  # noqa: BLE001
            log.exception("Erro ao destruir janela: %s", exc)

    # ---------- Monkey patch para Combobox.*
    @staticmethod
    def _patch_style_element_create(style: tb.Style) -> None:
        """
        Patching de segurança: ignora exclusivamente erros
        'Duplicate element Combobox.*' gerados pelo ttkbootstrap
        ao recriar elementos ao trocar de tema.
        """
        # try to get internal ttk.Style
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

    # ---------- Confirmação de saída ----------
    def _confirm_exit(self, *_):
        try:
            confirm = messagebox.askokcancel(
                "Sair",
                "Tem certeza de que deseja sair do RC Gestor?",
                parent=self,
                icon="question",
            )
        except Exception:
            confirm = True

        if confirm:
            try:
                self.destroy()
            except Exception as exc:  # noqa: BLE001
                log.exception("Erro ao destruir janela: %s", exc)

    # ---------- Tema ----------
    def _set_theme(self, new_theme: str) -> None:
        # Usar helper para calcular configuração de tema
        config = compute_theme_config(
            new_theme,  # requested_theme
            self.tema_atual,  # current_theme
            allow_persistence=not NO_FS,
        )

        if config is None:
            return  # Sem mudança necessária

        # Obter instância única de Style (reutilizar para evitar recriar)
        # Usar __dict__ ao invés de hasattr para evitar recursão infinita com Tk.__getattr__
        if "_style" not in self.__dict__:
            self._style = tb.Style()
        app_style = self._style

        # Aplicar monkey patch no element_create UMA vez
        self._patch_style_element_create(app_style)

        try:
            app_style.theme_use(config.name)
            # Re-aplicar ajustes de combobox
            apply_combobox_style(app_style)
            self.tema_atual = config.name
            if config.should_persist:
                themes.save_theme(config.name)
            try:
                if self._theme_listener:
                    self._theme_listener(config.name)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao notificar theme_listener: %s", exc)
        except Exception as exc:
            msg = str(exc)
            if "Duplicate element" in msg and "Combobox" in msg:
                log.debug("Ignorando erro duplicado de Combobox em theme_use: %s", msg)
                return
            log.exception("Falha ao trocar tema: %s", exc)
            messagebox.showerror("Erro", f"Falha ao trocar tema: {exc}", parent=self)

    def _handle_menu_theme_change(self, name: str) -> None:
        """Callback do AppMenuBar para troca de tema."""
        self._set_theme(name)
        try:
            self._menu.refresh_theme(name)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar tema do menu após mudança: %s", exc)

    # ---------- Integração com Health Check e Sessão ----------
    def _wire_session_and_health(self):
        """Conecta o health check do Supabase ao rodapé para atualização automática."""
        # [finalize-notes] import seguro dentro de função

        try:
            # Criar polling manual do estado do health check
            def poll_health():
                try:
                    # [finalize-notes] import seguro dentro de função aninhada
                    from infra.supabase_client import get_supabase_state

                    state, _ = get_supabase_state()
                    self.footer.set_cloud(state)
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao obter estado da nuvem no polling: %s", exc)
                # Reagendar polling
                try:
                    self.after(HEALTH_POLL_INTERVAL, poll_health)
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao reagendar polling de health: %s", exc)

            # Iniciar polling
            self.after(1000, poll_health)

            # Tentar obter estado inicial
            try:
                # [finalize-notes] import seguro dentro de função
                from infra.supabase_client import get_supabase_state

                current, _ = get_supabase_state()
                self.footer.set_cloud(current)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao definir estado inicial da nuvem: %s", exc)

        except Exception as e:
            log.warning("Erro ao conectar health check: %s", e)

    def _on_login_success(self, session):
        """Atualiza o rodapé com o email do usuário após login bem-sucedido."""
        try:
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
        email = ""
        role = "user"
        try:
            u = self._get_user_cached()
            if u:
                email = u.get("email") or ""
                role = self._get_role_cached(u["id"]) or "user"
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

    def _update_status_dot(self, is_online: Optional[bool]) -> None:
        # Calcular estilo usando helper
        dot_style = compute_status_dot_style(is_online)

        # Aplicar símbolo
        try:
            if self.status_var_dot:
                self.status_var_dot.set(dot_style.symbol)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao definir texto do status_var_dot: %s", exc)

        # Aplicar estilo/cor
        try:
            if self.status_dot:
                self.status_dot.configure(bootstyle=dot_style.bootstyle)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao configurar bootstyle do status_dot: %s", exc)

    def _apply_online_state(self, is_online: Optional[bool]) -> None:
        if is_online is None:
            return

        # Inicializar estado se não existir (compatibilidade com testes)
        # Usar __dict__ ao invés de hasattr para evitar recursão infinita com Tk.__getattr__
        if "_connectivity_state" not in self.__dict__:
            self._connectivity_state = ConnectivityState(is_online=True, offline_alerted=False)

        # Guardar estado anterior para detecção de transição
        was_online = self._connectivity_state.is_online

        # Calcular novo estado usando helper
        new_state = compute_connectivity_state(
            current_online=self._connectivity_state.is_online,
            new_online=bool(is_online),
            already_alerted=self._connectivity_state.offline_alerted,
        )
        self._connectivity_state = new_state

        # Atualizar UI de clientes
        frame = self._main_screen_frame()
        if frame:
            frame._update_main_buttons_state()

        # Verificar se deve mostrar alerta usando helper
        if should_show_offline_alert(was_online, new_state.is_online, new_state.offline_alerted):
            try:
                messagebox.showwarning(
                    "Sem conexão",
                    "Este aplicativo exige internet para funcionar. Verifique sua conexão e tente novamente.",
                    parent=self,
                )
                # Atualizar flag de alerta mostrado
                self._connectivity_state = ConnectivityState(
                    is_online=new_state.is_online,
                    offline_alerted=True,
                )
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao exibir alerta de offline: %s", exc)

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
        """Define informações do usuário logado na StatusBar global."""
        try:
            self._user_cache = {"email": email, "id": email} if email else None
            self._role_cache = role
            self._refresh_status_display()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar cache de usuário: %s", exc)
        self._refresh_status_display()

    def _update_user_status(self) -> None:
        self._refresh_status_display()

    def _schedule_user_status_refresh(self) -> None:
        self._update_user_status()
        try:
            txt = self.status_var_text.get() or ""
        except Exception:
            txt = ""
        if "Usuário:" not in txt:
            try:
                self.after(STATUS_REFRESH_INTERVAL, self._schedule_user_status_refresh)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao agendar refresh de status de usuário: %s", exc)

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
        """
        Retorna o prefix (caminho da pasta) do cliente atualmente selecionado no Storage.
        Ex.: retorna '0a7c9f39-4b7d-4a88-8e77-7b88a38c66d7/7'

        Este método é chamado automaticamente pelo uploader_supabase.py quando disponível.
        A implementação usa a MESMA lógica da tela 'Ver Subpastas' / open_files_browser.
        """
        try:
            values = self._selected_main_values()
            if not values:
                return ""

            client_id = values[0]

            # Usa mesma lógica do open_client_storage_subfolders
            u = self._get_user_cached()
            if not u:
                return ""

            org_id = self._get_org_id_cached(u["id"])
            if not org_id:
                return ""

            # Formato idêntico ao open_files_browser: {org_id}/{client_id}
            return f"{org_id}/{client_id}".strip("/")
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao construir caminho de storage: %s", exc)

        return ""

    # -------- Upload para Supabase (sistema avançado com fallback) --------
    def enviar_para_supabase(self) -> None:
        """Delegador para AppActions.enviar_para_supabase."""
        self._actions.enviar_para_supabase()

    def enviar_pasta_supabase(self) -> None:
        """Seleciona uma pasta e envia PDFs recursivamente para o Supabase."""
        try:
            send_folder_to_supabase(
                self,
                default_bucket=os.getenv("SUPABASE_BUCKET") or "rc-docs",
            )
        except Exception as exc:
            log.error("Erro ao enviar pasta para Supabase: %s", exc)
            messagebox.showerror(
                "Erro",
                f"Erro ao enviar pasta para Supabase:\n{exc}",
                parent=self,
            )

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
        """Abre ou traz para frente a janela do ChatGPT."""
        window = getattr(self, "_chatgpt_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.show()
                return
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao focar janela do ChatGPT: %s", exc)
            self._chatgpt_window = None

        # Criar nova janela com callback para limpar referência ao fechar
        try:
            parent_window = self.winfo_toplevel()
        except Exception:
            parent_window = self
        window = ChatGPTWindow(parent_window, on_close_callback=self._on_chatgpt_close)
        self._chatgpt_window = window

        try:
            # Registrar WM_DELETE_WINDOW para capturar fechamento pela barra de título
            window.protocol("WM_DELETE_WINDOW", self._close_chatgpt_window)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao registrar handler de fechamento do ChatGPT: %s", exc)

        try:
            window.bind("<Destroy>", lambda event: self._on_chatgpt_destroy(window), add="+")
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao vincular destroy do ChatGPT: %s", exc)

    def _on_chatgpt_close(self) -> None:
        """Callback chamado quando a janela do ChatGPT é fechada."""
        self._chatgpt_window = None

    def _close_chatgpt_window(self) -> None:
        """Fecha a janela do ChatGPT."""
        window = getattr(self, "_chatgpt_window", None)
        try:
            if window is not None and window.winfo_exists():
                window.destroy()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao destruir janela do ChatGPT: %s", exc)
        finally:
            self._chatgpt_window = None

    def _on_chatgpt_destroy(self, window: ChatGPTWindow) -> None:
        if self._chatgpt_window is window:
            self._chatgpt_window = None

    # -------- Sessao / usuario --------
    def _get_user_cached(self) -> Optional[dict[str, Any]]:
        """Retorna dados do usuário autenticado (delegado para SessionCache)."""
        user = self._session.get_user()

        # Hidratar AuthController se temos dados do usuário
        if user:
            try:
                uid = user["id"]
                org_id = self._session.get_org_id(uid)
                user_data = {
                    "id": uid,
                    "email": user["email"],
                    "org_id": org_id,
                }
                self.auth.set_user_data(user_data)
            except Exception as e:
                log.warning("Não foi possível hidratar AuthController: %s", e)

        return user

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
        if getattr(self, "_status_monitor", None):
            try:
                status_monitor = getattr(self, "_status_monitor", None)
                if status_monitor is not None:
                    status_monitor.stop()
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao parar StatusMonitor: %s", exc)
            finally:
                self._status_monitor = None
        if getattr(self, "_theme_listener", None):
            try:
                listener = getattr(self, "_theme_listener", None)
                if listener is not None:
                    theme_manager.remove_listener(listener)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao remover theme_listener: %s", exc)
        super().destroy()
        if getattr(self, "_restarting", False):
            log.info("App reiniciado (troca de tema).")
        else:
            log.info("App fechado.")

    def _show_changelog(self) -> None:
        try:
            with open(resource_path("runtime_docs/CHANGELOG.md"), "r", encoding="utf-8") as f:
                conteudo = f.read()
            preview = "\n".join(conteudo.splitlines()[:20])
            messagebox.showinfo("Changelog", preview, parent=self)
        except Exception:
            messagebox.showinfo(
                "Changelog",
                "Arquivo CHANGELOG.md não encontrado.",
                parent=self,
            )


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
