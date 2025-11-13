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
from src import app_core, app_status
from src.core.auth_controller import AuthController
from src.core.keybindings import bind_global_shortcuts
from src.core.navigation_controller import NavigationController
from src.core.status_monitor import StatusMonitor
from src.ui.files_browser import open_files_browser
from src.ui.main_screen import MainScreenFrame
from src.ui.main_window.frame_factory import create_frame
from src.ui.main_window.router import navigate_to
from src.ui.main_window.tk_report import tk_report
from src.ui.menu_bar import AppMenuBar
from src.ui.topbar import TopBar
from src.ui.window_policy import apply_fit_policy
from src.utils import themes
from src.utils.theme_manager import theme_manager
from uploader_supabase import send_folder_to_supabase, send_to_supabase_interactive

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
    from src.utils.validators import only_digits as _only_digits
except Exception:  # pragma: no cover

    def _only_digits(s: str | None) -> str:
        return "".join(ch for ch in str(s or "") if ch.isdigit())


try:
    from src.ui.lixeira import abrir_lixeira as abrir_lixeira_ui
except Exception:
    from src.ui.lixeira.lixeira import abrir_lixeira as abrir_lixeira_ui

resource_path = _resource_path
sha256_file = _sha256
only_digits = _only_digits

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
            self.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        # Menubar com AppMenuBar
        self._menu = AppMenuBar(
            self,
            on_home=self.show_hub_screen,
            on_open_subpastas=self.ver_subpastas,
            on_open_lixeira=self.abrir_lixeira,
            on_upload=self.enviar_para_supabase,
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

        self.title("Regularize Consultoria - v1.1.0")

        # --- Aplicar política Fit-to-WorkArea ---
        apply_fit_policy(self)

        self.tema_atual = _theme_name
        self._restarting = False

        self._user_cache = None
        self._role_cache = None
        self._org_id_cache = None

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
        self._main_frame_ref: Optional[MainScreenFrame] = None
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

        # Keybindings
        bind_global_shortcuts(
            self,
            {
                "quit": self.destroy,
                "refresh": self.carregar,
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
        try:
            from src.ui.hub_screen import HubScreen
        except Exception:
            HubScreen = None

        is_hub = False
        try:
            if HubScreen:
                # classe, instância ou callable (lambda) que retorna frame
                if isinstance(frame_or_cls, type):
                    is_hub = frame_or_cls is HubScreen
                elif callable(frame_or_cls):
                    # se for factory/lambda, checa o current()
                    cur = self.nav.current()
                    is_hub = isinstance(cur, HubScreen) if cur is not None else False
                else:
                    is_hub = isinstance(frame_or_cls, HubScreen)

                # redundância segura: também checa o frame atual do controlador
                cur = self.nav.current()
                if cur is not None:
                    is_hub = is_hub or isinstance(cur, HubScreen)
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

    def _main_screen_frame(self) -> Optional[MainScreenFrame]:
        frame = getattr(self, "_main_frame_ref", None)
        if isinstance(frame, MainScreenFrame):
            return frame
        current = self.nav.current()
        if isinstance(current, MainScreenFrame):
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

    def refresh_clients_count_async(self, auto_schedule: bool = True) -> None:
        """
        Atualiza a contagem de clientes do Supabase de forma assíncrona.
        Usa threading para não travar a UI.

        Args:
            auto_schedule: Se True, agenda próxima atualização automática em 30s
        """

        def _work():
            try:
                from src.core.services.clientes_service import count_clients

                total = count_clients()
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

    def open_clients_picker(self, on_pick):
        return navigate_to(self, "clients_picker", on_pick=on_pick)

    # ---------- Confirmação de saída ----------
    def _confirm_exit(self, *_):
        try:
            if messagebox.askokcancel("Sair", "Tem certeza de que deseja sair?", parent=self):
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
            messagebox.showerror("Erro", f"Falha ao trocar tema: {exc}")

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
        return f" | Usuario: {email} ({role})" if email else ""

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
                    "Sem conexao",
                    "Este aplicativo exige internet para funcionar. Verifique sua conexao e tente novamente.",
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
        if "Usuario:" not in txt:
            try:
                self.after(300, self._schedule_user_status_refresh)
            except Exception:
                pass

    def novo_cliente(self) -> None:
        app_core.novo_cliente(self)

    def editar_cliente(self) -> None:
        values = self._selected_main_values()
        if not values:
            messagebox.showwarning("Atencao", "Selecione um cliente para editar.")
            return
        try:
            pk = int(values[0])
        except Exception:
            messagebox.showerror("Erro", "ID invalido.")
            return
        app_core.editar_cliente(self, pk)

    def ver_subpastas(self) -> None:
        values = self._selected_main_values()
        if not values:
            messagebox.showwarning("Atencao", "Selecione um cliente primeiro.")
            return
        client_id = values[0]
        razao = (values[1] or "").strip()
        cnpj = (values[2] or "").strip()

        u = self._get_user_cached()
        if not u:
            messagebox.showerror("Erro", "Usuario nao autenticado.")
            return
        org_id = self._get_org_id_cached(u["id"])
        if not org_id:
            messagebox.showerror("Erro", "Organizacao nao encontrado para o usuario.")
            return

        open_files_browser(self, org_id=org_id, client_id=client_id, razao=razao, cnpj=cnpj)

    def abrir_lixeira(self) -> None:
        abrir_lixeira_ui(self)

    def _excluir_cliente(self) -> None:
        values = self._selected_main_values()
        if values:
            app_core.excluir_cliente(self, values)

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
        """
        Upload avançado para Supabase Storage.
        Permite escolher arquivos, múltiplos arquivos ou pasta inteira,
        com seleção de bucket/pasta de destino e barra de progresso.
        Inclui fallback quando list_buckets() não funciona (RLS).
        Upload padrão: cliente/GERAL
        """
        try:
            import os

            # Obtém base do cliente (ORG_UID/CLIENT_ID)
            base = self.get_current_client_storage_prefix()

            send_to_supabase_interactive(
                self,
                default_bucket=os.getenv("SUPABASE_BUCKET") or "rc-docs",
                base_prefix=base,  # força cair dentro do cliente
                default_subprefix="GERAL",  # padrão: enviar para GERAL
            )
        except Exception as e:
            log.error("Erro ao enviar para Supabase: %s", e)
            messagebox.showerror("Erro", f"Erro ao enviar para Supabase:\n{str(e)}", parent=self)

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
        if self._user_cache:
            return self._user_cache
        try:
            from infra.supabase_client import supabase

            resp = supabase.auth.get_user()
            u = getattr(resp, "user", None) or resp
            uid = getattr(u, "id", None)
            email = getattr(u, "email", "") or ""
            if uid:
                self._user_cache = {"id": uid, "email": email}

                # Hidratar AuthController com dados completos
                try:
                    org_id = self._get_org_id_cached(uid)
                    user_data = {
                        "id": uid,
                        "email": email,
                        "org_id": org_id,
                    }
                    self.auth.set_user_data(user_data)
                except Exception as e:
                    log.warning("Não foi possível hidratar AuthController: %s", e)

                return self._user_cache
        except Exception:
            pass
        return None

    def _get_role_cached(self, uid: str) -> str:
        if self._role_cache:
            return self._role_cache
        try:
            from infra.supabase_client import exec_postgrest, supabase

            res = exec_postgrest(supabase.table("memberships").select("role").eq("user_id", uid).limit(1))
            if getattr(res, "data", None):
                self._role_cache = (res.data[0].get("role") or "user").lower()
            else:
                self._role_cache = "user"
        except Exception:
            self._role_cache = "user"
        return self._role_cache

    def _get_org_id_cached(self, uid: str) -> Optional[str]:
        if self._org_id_cache:
            return self._org_id_cache
        try:
            from infra.supabase_client import exec_postgrest, supabase

            res = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1))
            if getattr(res, "data", None) and res.data[0].get("org_id"):
                self._org_id_cache = res.data[0]["org_id"]
                return self._org_id_cache
        except Exception:
            pass
        return None

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
                "Arquivo CHANGELOG.md nao encontrado.",
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
