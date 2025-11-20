# -*- coding: utf-8 -*-
"""Main application window (App class)."""

# gui/main_window.py
import functools as _functools
import hashlib
import logging
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Optional

import ttkbootstrap as tb

from infra.net_status import Status
from src import app_status
from src.modules.login.service import AuthController
from src.modules.notas import HubFrame
from src.core.keybindings import bind_global_shortcuts
from src.core.navigation_controller import NavigationController
from src.core.status_monitor import StatusMonitor
from src.modules.clientes import ClientesFrame
from src.modules.clientes import service as clientes_service
from src.modules.main_window.app_actions import AppActions
from src.modules.main_window.controller import create_frame, navigate_to, tk_report
from src.modules.main_window.session_service import SessionCache
from src.ui.menu_bar import AppMenuBar
from src.ui.topbar import TopBar
from src.ui.window_policy import apply_fit_policy
from src.ui import custom_dialogs
from src.utils import themes
from src.utils.theme_manager import theme_manager
from src.utils.validators import only_digits  # noqa: F401
from uploader_supabase import send_folder_to_supabase

# -------- Phase 1 + 4: shared helpers with safe fallbacks --------
try:
    from src.utils.resource_path import resource_path as _resource_path
except Exception:  # pragma: no cover

    def _resource_path(relative_path: str) -> str:
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base_path, relative_path)


try:
    from src.utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover

    def _sha256(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()


try:
    pass
except Exception:
    pass

resource_path = _resource_path
sha256_file = _sha256

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
        except Exception:
            pass  # Silencioso se falhar

        # Criar separadores horizontais (idempotentes)
        # Separador 1: logo abaixo do menu (antes da toolbar)
        if not hasattr(self, "sep_menu_toolbar") or self.sep_menu_toolbar is None:
            self.sep_menu_toolbar = ttk.Separator(self, orient="horizontal")
            self.sep_menu_toolbar.pack(side="top", fill="x", pady=0)

        self._topbar = TopBar(self, on_home=self.show_hub_screen)
        self._topbar.pack(side="top", fill="x")

        # Separador 2: logo abaixo da toolbar (antes do conteúdo principal)
        if not hasattr(self, "sep_toolbar_main") or self.sep_toolbar_main is None:
            self.sep_toolbar_main = ttk.Separator(self, orient="horizontal")
            self.sep_toolbar_main.pack(side="top", fill="x", pady=0)

        if start_hidden:
            try:
                self.withdraw()
            except Exception:
                pass

        try:
            icon_relative = "rc.ico"
            icon_path = resource_path(icon_relative)
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
                log.warning("Ícone rc.ico não encontrado em: %s", icon_path)
        except Exception:
            log.exception("Falha ao aplicar ícone da aplicação")

        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        # Menubar com AppMenuBar
        self._menu = AppMenuBar(
            self,
            on_home=self.show_hub_screen,
            on_refresh=self.refresh_current_view,
            on_quit=self._confirm_exit,
            on_change_theme=self._handle_menu_theme_change,
        )
        self._menu.attach()
        try:
            self._menu.refresh_theme(_theme_name)
        except Exception:
            pass

        try:
            tb.Style().theme_use(_theme_name)
        except Exception:
            pass

        self.report_callback_exception = tk_report

        self.title("Regularize Consultoria - v1.2.0")

        # --- Aplicar política Fit-to-WorkArea ---
        apply_fit_policy(self)

        self.tema_atual = _theme_name
        self._restarting = False

        # Cache de sessão (user, role, org_id) delegado para SessionCache
        self._session = SessionCache()

        self._net_is_online = True
        self._offline_alerted = False

        # Cache da instância única do Hub (evita tela branca ao navegar)
        self._hub_screen_instance = None

        # Cache da instância única da tela de Senhas (evita tela branca ao navegar)
        self._passwords_screen_instance = None

        # Cliente Supabase (lazy-loaded quando necessário)
        try:
            from infra.supabase_client import supabase

            self.supabase = supabase
        except Exception:
            self.supabase = None

        self.clients_count_var = tk.StringVar(master=self, value="0 clientes")
        self.status_var_dot = tk.StringVar(master=self, value="")
        self.status_var_text = tk.StringVar(
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
            self._theme_listener = lambda t: themes.apply_button_styles(self, theme=t)
            theme_manager.add_listener(self._theme_listener)
        except Exception:
            self._theme_listener = None

        log.info("App iniciado com tema: %s", self.tema_atual)

        self._content_container = tb.Frame(self)
        self._content_container.pack(fill="both", expand=True)
        self.nav = NavigationController(self._content_container, frame_factory=self._frame_factory)

        # --- StatusBar Global (sempre visível no rodapé) ---
        from src.ui.status_footer import StatusFooter

        self.footer = StatusFooter(self, show_trash=False)
        self.footer.pack(side="bottom", fill="x")
        self.footer.set_count(0)
        self.footer.set_user(None)
        self.footer.set_cloud("UNKNOWN")

        self._status_monitor = StatusMonitor(self._handle_status_update, app_after=self.after)
        try:
            self._status_monitor.set_cloud_only(NO_FS)
        except Exception:
            pass
        self._status_monitor.start()

        # Conectar health check ao rodapé
        self._wire_session_and_health()

        # Auth
        self.auth = AuthController(on_user_change=lambda user: self._refresh_status_display())

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
                "subpastas": self.ver_subpastas,
                "hub": self.show_hub_screen,
                "find": lambda: getattr(self, "_main_frame_ref", None) and getattr(self._main_frame_ref, "_buscar", lambda: None)(),
            },
        )

        self.after(300, self._schedule_user_status_refresh)
        self.bind("<FocusIn>", lambda e: self._update_user_status(), add="+")
        self.show_hub_screen()

    def show_frame(self, frame_cls, **kwargs):
        frame = self.nav.show_frame(frame_cls, **kwargs)
        try:
            self._update_topbar_state(frame)
        except Exception:
            pass
        return frame

    def _frame_factory(self, frame_cls, options):
        return create_frame(self, frame_cls, options)

    def _update_topbar_state(self, frame_or_cls) -> None:
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
        except Exception:
            pass

        try:
            self._topbar.set_is_hub(is_hub)
        except Exception:
            pass

        try:
            self._menu.set_is_hub(is_hub)
        except Exception:
            pass

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
            except Exception:
                pass

            # Auto-refresh: agenda próxima atualização em 30s
            if auto_schedule:
                try:
                    self.after(
                        30000,
                        lambda: self.refresh_clients_count_async(auto_schedule=True),
                    )
                except Exception:
                    pass

        threading.Thread(target=_work, daemon=True).start()

    def show_hub_screen(self) -> None:
        return navigate_to(self, "hub")

    def show_main_screen(self) -> None:
        return navigate_to(self, "main")

    def show_placeholder_screen(self, title: str) -> None:
        return navigate_to(self, "placeholder", title=title)

    def show_passwords_screen(self) -> None:
        return navigate_to(self, "passwords")

    def show_cashflow_screen(self) -> None:
        return navigate_to(self, "cashflow")

    def open_clients_picker(self, on_pick):
        return navigate_to(self, "clients_picker", on_pick=on_pick)

    # ---------- Confirmação de saída ----------
    def _confirm_exit(self, *_):
        try:
            if custom_dialogs.ask_ok_cancel(self, "Sair", "Tem certeza de que deseja sair?"):
                self.destroy()
        except Exception:
            self.destroy()

    # ---------- Tema ----------
    def _set_theme(self, new_theme: str) -> None:
        if not new_theme or new_theme == self.tema_atual:
            return
        try:
            tb.Style().theme_use(new_theme)
            self.tema_atual = new_theme
            if not NO_FS:
                themes.save_theme(new_theme)
            try:
                if self._theme_listener:
                    self._theme_listener(new_theme)
            except Exception:
                pass
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao trocar tema: {exc}", parent=self)

    def _handle_menu_theme_change(self, name: str) -> None:
        """Callback do AppMenuBar para troca de tema."""
        self._set_theme(name)
        try:
            self._menu.refresh_theme(name)
        except Exception:
            pass

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
                except Exception:
                    pass
                # Reagendar polling
                try:
                    self.after(5000, poll_health)  # A cada 5 segundos
                except Exception:
                    pass

            # Iniciar polling
            self.after(1000, poll_health)

            # Tentar obter estado inicial
            try:
                # [finalize-notes] import seguro dentro de função
                from infra.supabase_client import get_supabase_state

                current, _ = get_supabase_state()
                self.footer.set_cloud(current)
            except Exception:
                pass

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
        if not base and suffix.startswith(" | "):
            display = suffix[3:]
        else:
            display = f"{base}{suffix}"
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

                email = (session.get_current_user() or "") or email
            except Exception:
                pass
        return f" | Usuário: {email} ({role})" if email else ""

    def _update_status_dot(self, is_online: Optional[bool]) -> None:
        try:
            if self.status_var_dot:
                self.status_var_dot.set("•")
        except Exception:
            pass
        try:
            if self.status_dot:
                style = "warning"
                if is_online is True:
                    style = "success"
                elif is_online is False:
                    style = "danger"
                self.status_dot.configure(bootstyle=style)
        except Exception:
            pass

    def _apply_online_state(self, is_online: Optional[bool]) -> None:
        if is_online is None:
            return
        was_online = getattr(self, "_net_is_online", True)
        self._net_is_online = bool(is_online)
        frame = self._main_screen_frame()
        if frame:
            frame._update_main_buttons_state()
        if not self._net_is_online and was_online and not self._offline_alerted:
            self._offline_alerted = True
            try:
                messagebox.showwarning(
                    "Sem conexão",
                    "Este aplicativo exige internet para funcionar. Verifique sua conexão e tente novamente.",
                    parent=self,
                )
            except Exception:
                pass
        if self._net_is_online:
            self._offline_alerted = False

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
        except Exception:
            pass

    def set_user_status(self, email: Optional[str], role: Optional[str] = None) -> None:
        """Define informações do usuário logado na StatusBar global."""
        try:
            self._user_cache = {"email": email, "id": email} if email else None
            self._role_cache = role
            self._refresh_status_display()
        except Exception:
            pass
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
                self.after(300, self._schedule_user_status_refresh)
            except Exception:
                pass

    def novo_cliente(self) -> None:
        """Delegador para AppActions.novo_cliente."""
        self._actions.novo_cliente()

    def editar_cliente(self) -> None:
        """Delegador para AppActions.editar_cliente."""
        self._actions.editar_cliente()

    def ver_subpastas(self) -> None:
        """Delegador para AppActions.ver_subpastas."""
        self._actions.ver_subpastas()

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

            # Usa mesma lógica do ver_subpastas
            u = self._get_user_cached()
            if not u:
                return ""

            org_id = self._get_org_id_cached(u["id"])
            if not org_id:
                return ""

            # Formato idêntico ao open_files_browser: {org_id}/{client_id}
            return f"{org_id}/{client_id}".strip("/")
        except Exception:
            pass

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
        os.execv(sys.executable, [sys.executable, "-m", "main"])

    def destroy(self) -> None:
        if getattr(self, "_status_monitor", None):
            try:
                status_monitor = getattr(self, "_status_monitor", None)
                if status_monitor is not None:
                    status_monitor.stop()
            except Exception:
                pass
            finally:
                self._status_monitor = None
        if getattr(self, "_theme_listener", None):
            try:
                listener = getattr(self, "_theme_listener", None)
                if listener is not None:
                    theme_manager.remove_listener(listener)
            except Exception:
                pass
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
    App.ver_subpastas = _log_call(App.ver_subpastas)
    App.enviar_para_supabase = _log_call(App.enviar_para_supabase)
except Exception:
    pass
