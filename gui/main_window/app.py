# gui/main_window.py
# -*- coding: utf-8 -*-
"""Main application window (App class)."""
import os
import sys
import hashlib

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import logging
import threading
from tkinter import filedialog, messagebox
from typing import Any, Optional

# -------- Phase 1 + 4: shared helpers with safe fallbacks --------
try:
    from utils.resource_path import resource_path as _resource_path
except Exception:  # pragma: no cover

    def _resource_path(relative_path: str) -> str:
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base_path, relative_path)


try:
    from utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover

    def _sha256(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()


try:
    from utils.validators import only_digits as _only_digits
except Exception:  # pragma: no cover

    def _only_digits(value) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())


resource_path = _resource_path
sha256_file = _sha256
only_digits = _only_digits

NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

import app_core
import app_status
from utils import themes
from utils.theme_manager import theme_manager

try:
    from ui.lixeira import abrir_lixeira as abrir_lixeira_ui
except Exception:
    from ui.lixeira.lixeira import abrir_lixeira as abrir_lixeira_ui

from ui.files_browser import open_files_browser
from ui.topbar import TopBar
from infra.net_status import Status

from application.navigation_controller import NavigationController
from application.status_monitor import StatusMonitor
from application.auth_controller import AuthController
from application.keybindings import bind_global_shortcuts
from gui.main_window.frame_factory import create_frame
from gui.main_window.router import navigate_to
from gui.main_window.tk_report import tk_report
from gui.hub_screen import HubScreen
from gui.menu_bar import AppMenuBar
from gui.placeholders import ComingSoonScreen
from gui.main_screen import MainScreenFrame, DEFAULT_ORDER_LABEL, ORDER_CHOICES

logger = logging.getLogger("app_gui")
log = logger


class App(tb.Window):
    """Main ttkbootstrap window for the Gestor de Clientes desktop application."""

    def __init__(self, start_hidden: bool = False) -> None:
        _theme_name = themes.load_theme()
        super().__init__(themename=_theme_name)

        # Configurar HiDPI após criação do Tk (Linux) ou antes (Windows já foi no app_gui)
        # No Linux, ttkbootstrap Window já vem com hdpi=True por padrão em versões recentes
        # Mas vamos garantir configuração explícita se necessário
        try:
            from utils.helpers import configure_hidpi_support

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

        self.title("Regularize Consultoria - v1.0.49")

        # --- Geometria responsiva ---
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        MIN_W, MIN_H = 1100, 600
        target_w, target_h = int(sw * 0.72), int(sh * 0.72)
        MAX_W = 1500 if sw >= 1920 else sw - 80
        MAX_H = 900 if sh >= 1080 else sh - 120
        win_w = max(MIN_W, min(target_w, MAX_W))
        win_h = max(MIN_H, min(target_h, MAX_H))
        if sw <= 1280 or sh <= 720:
            win_w = max(MIN_W, int(sw * 0.90))
            win_h = max(MIN_H, int(sh * 0.88))
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(MIN_W, MIN_H)

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
        self.nav = NavigationController(
            self._content_container, frame_factory=self._frame_factory
        )

        # --- StatusBar Global (sempre visível no rodapé) ---
        from gui.status_footer import StatusFooter
        self.footer = StatusFooter(self, show_trash=False)
        self.footer.pack(side="bottom", fill="x")
        self.footer.set_count(0)
        self.footer.set_user(None)
        self.footer.set_cloud("UNKNOWN")

        self._status_monitor = StatusMonitor(
            self._handle_status_update, app_after=self.after
        )
        try:
            self._status_monitor.set_cloud_only(NO_FS)
        except Exception:
            pass
        self._status_monitor.start()
        
        # Conectar health check ao rodapé
        self._wire_session_and_health()

        # Auth
        self.auth = AuthController(
            on_user_change=lambda user: self._refresh_status_display()
        )

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
                "find": lambda: getattr(self, "_main_frame_ref", None)
                and getattr(self._main_frame_ref, "_buscar", lambda: None)(),
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
            from gui.hub_screen import HubScreen
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
                from core.services.clientes_service import count_clients
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
                    self.after(30000, lambda: self.refresh_clients_count_async(auto_schedule=True))
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
            if messagebox.askokcancel(
                "Sair", "Tem certeza de que deseja sair?", parent=self
            ):
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
        from infra.supabase_client import get_supabase
        
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
    def _handle_status_update(
        self, base_text: str, is_online: Optional[bool] = None
    ) -> None:
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
                from core import session

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

        open_files_browser(
            self, org_id=org_id, client_id=client_id, razao=razao, cnpj=cnpj
        )

    def abrir_lixeira(self) -> None:
        abrir_lixeira_ui(self)

    def _excluir_cliente(self) -> None:
        values = self._selected_main_values()
        if values:
            app_core.excluir_cliente(self, values)

    # -------- Upload para Supabase (com telinha indeterminada) --------
    def enviar_para_supabase(self) -> None:
        values = self._selected_main_values()
        if not values:
            messagebox.showwarning("Atencao", "Selecione um cliente primeiro.")
            return

        client_id = values[0]
        pasta = filedialog.askdirectory(
            title="Escolha a pasta local para enviar ao Supabase", parent=self
        )
        if not pasta:
            return

        from ui.dialogs.upload_progress import show_upload_progress

        show_upload_progress(self, pasta, int(client_id), subdir="SIFAP")

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

            res = exec_postgrest(
                supabase.table("memberships")
                .select("role")
                .eq("user_id", uid)
                .limit(1)
            )
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

            res = exec_postgrest(
                supabase.table("memberships")
                .select("org_id")
                .eq("user_id", uid)
                .limit(1)
            )
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
                self._status_monitor.stop()
            except Exception:
                pass
            finally:
                self._status_monitor = None
        if getattr(self, "_theme_listener", None):
            try:
                theme_manager.remove_listener(self._theme_listener)
            except Exception:
                pass
        super().destroy()
        if getattr(self, "_restarting", False):
            log.info("App reiniciado (troca de tema).")
        else:
            log.info("App fechado.")

    def _show_changelog(self) -> None:
        try:
            with open(
                resource_path("runtime_docs/CHANGELOG.md"), "r", encoding="utf-8"
            ) as f:
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
import functools as _functools

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
