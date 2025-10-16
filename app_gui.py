# app_gui.py
# -*- coding: utf-8 -*-
import os
import sys
import hashlib
os.environ.setdefault('RC_NO_LOCAL_FS', '1')
try:
    import utils.helpers.rc_hotfix_no_local_fs  # ensures cloud-only paths
except Exception:
    pass

import tkinter as tk
import ttkbootstrap as tb
import webbrowser
import re
import logging
import threading
from tkinter import ttk, filedialog, messagebox
from typing import Any, Optional, Sequence
import urllib.parse

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

try:
    from ui import center_on_parent as _center_on_parent
except Exception:  # pragma: no cover
    try:
        from ui.utils import center_on_parent as _center_on_parent
    except Exception:  # pragma: no cover
        def _center_on_parent(win, parent=None, pad=0):
            return win

resource_path = _resource_path
sha256_file = _sha256
only_digits = _only_digits
center_on_parent = _center_on_parent

# -------- Loader de .env (suporta PyInstaller onefile) --------
try:
    from dotenv import load_dotenv
    load_dotenv(resource_path(".env"), override=False)              # empacotado
    load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)   # externo sobrescreve
except Exception:
    pass
# --------------------------------------------------------------

NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

from core.search import search_clientes
from app_utils import fmt_data
from utils.text_utils import format_cnpj
import app_core, app_status
from utils import themes
from utils.theme_manager import theme_manager
from ui.components import (
    create_clients_treeview,
    create_footer_buttons,
    create_menubar,
    create_search_controls,
    create_status_bar,
)

try:
    from ui.lixeira import abrir_lixeira as abrir_lixeira_ui
except Exception:
    from ui.lixeira.lixeira import abrir_lixeira as abrir_lixeira_ui

from ui.files_browser import open_files_browser
from core.services.upload_service import upload_folder_to_supabase
from infra.net_status import Status

from gui.navigation import show_frame
from gui.hub_screen import HubScreen
from gui.placeholders import ComingSoonScreen

DEFAULT_ORDER_LABEL = "Razao Social (A->Z)"
ORDER_CHOICES: dict[str, tuple[Optional[str], bool]] = {
    "Razao Social (A->Z)": ("razao_social", False),
    "CNPJ (A->Z)": ("cnpj", False),
    "Nome (A->Z)": ("nome", False),
    "Ultima Alteracao (mais recente)": ("ultima_alteracao", False),
    "Ultima Alteracao (mais antiga)": ("ultima_alteracao", True),
}

logger = logging.getLogger("app_gui")
log = logger


class App(tb.Window):
    """Main ttkbootstrap window for the Gestor de Clientes desktop application."""

    def __init__(self, start_hidden: bool = False) -> None:
        _theme_name = themes.load_theme()
        super().__init__(themename=_theme_name)

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
        self.bind_all("<Control-q>", lambda e: self._confirm_exit())

        # Menubar
        try:
            menu_components = create_menubar(
                self,
                theme_name=_theme_name,
                on_set_theme=self._set_theme,
                on_show_changelog=self._show_changelog,
                on_exit=self._confirm_exit,
            )
            self._theme_var = menu_components.theme_var
        except Exception as exc:
            log.exception("Falha ao criar Menubar", exc_info=exc)
            self._theme_var = tk.StringVar(value=_theme_name or "flatly")

        try:
            tb.Style().theme_use(_theme_name)
        except Exception:
            pass

        def _tk_report(exc, val, tb_):
            log.exception("Excecao no Tkinter callback", exc_info=(exc, val, tb_))
        self.report_callback_exception = _tk_report

        self.title('Regularize Consultoria - v1.0.12 (BETA)')

        # --- Geometria responsiva ---
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        MIN_W, MIN_H = 1100, 600
        target_w, target_h = int(sw * 0.72), int(sh * 0.72)
        MAX_W = 1500 if sw >= 1920 else sw - 80
        MAX_H = 900  if sh >= 1080 else sh - 120
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
        self._buscar_after = None

        self._user_cache = None
        self._role_cache = None
        self._org_id_cache = None

        self._net_is_online = True
        self._offline_alerted = False

        try:
            theme_manager.register_window(self)
            self._theme_listener = lambda t: themes.apply_button_styles(self, theme=t)
            theme_manager.add_listener(self._theme_listener)
        except Exception:
            self._theme_listener = None

        log.info("App iniciado com tema: %s", self.tema_atual)

        self._content_container = tb.Frame(self)
        self._content_container.pack(fill="both", expand=True)

        self._main_frame = tb.Frame(self._content_container)
        self._main_frame._keep_alive = True  # type: ignore[attr-defined]
        self._build_main_screen(self._main_frame)

        try:
            app_status.update_net_status(self)
        except Exception:
            pass
        self._apply_env_dot(self._get_env_text())

        self._update_main_buttons_state()
        self.after(300, self._schedule_user_status_refresh)
        self.show_hub_screen()

    def _build_main_screen(self, parent: tk.Misc) -> None:
        # === UI Principal ===
        search_controls = create_search_controls(
            parent,
            order_choices=ORDER_CHOICES.keys(),
            default_order=DEFAULT_ORDER_LABEL,
            on_search=self._buscar,
            on_clear=self._limpar_busca,
            on_order_change=self.carregar,
        )
        search_controls.frame.pack(fill="x", padx=10, pady=10)
        self.var_busca = search_controls.search_var
        self.var_ordem = search_controls.order_var

        self.client_list = create_clients_treeview(
            parent,
            on_double_click=lambda _event: self.editar_cliente(),
            on_select=self._update_main_buttons_state,
            on_delete=lambda _event: self._excluir_cliente(),
            on_click=self._on_click,
        )
        self.client_list.pack(expand=True, fill="both", padx=10, pady=5)

        footer = create_footer_buttons(
            parent,
            on_novo=self.novo_cliente,
            on_editar=self.editar_cliente,
            on_subpastas=self.ver_subpastas,
            on_enviar=self.enviar_para_supabase,
            on_lixeira=self.abrir_lixeira,
        )
        footer.frame.pack(fill="x", padx=10, pady=10)
        self.btn_novo = footer.novo
        self.btn_editar = footer.editar
        self.btn_subpastas = footer.subpastas
        self.btn_enviar = footer.enviar
        self.btn_lixeira = footer.lixeira

        status = create_status_bar(
            parent,
            status_text_var=tk.StringVar(
                master=self,
                value=(getattr(app_status, "status_text", None) or "LOCAL"),
            ),
        )
        status.frame.pack(fill="x", padx=10, pady=5)
        self.clients_count_var = status.count_var
        self.status_var_dot = status.status_dot_var
        self.status_var_text = status.status_text_var
        self.status_dot = status.status_dot
        self.status_lbl = status.status_label

        self._main_loaded = False

    def show_hub_screen(self) -> None:
        show_frame(
            self._content_container,
            HubScreen,
            on_open_sifap=self.show_main_screen,
            on_open_anvisa=lambda: self.show_placeholder_screen("ANVISA"),
            on_open_passwords=lambda: self.show_placeholder_screen("senhas"),
        )

    def show_main_screen(self) -> None:
        show_frame(
            self._content_container,
            lambda parent: self._main_frame,
        )
        self._main_loaded = True
        try:
            self.carregar()
        except Exception:
            log.exception("Erro ao carregar lista na tela principal.")
        self._update_main_buttons_state()

    def show_placeholder_screen(self, title: str) -> None:
        show_frame(
            self._content_container,
            ComingSoonScreen,
            title=title,
            on_back=self.show_hub_screen,
        )

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

    # ---------- Helpers de Status ----------
    def _get_env_text(self) -> str:
        try:
            txt = (self.status_var_text.get() or "")
            base = txt.split(" | Usuario:", 1)[0].strip()
            return base or "LOCAL"
        except Exception:
            return "LOCAL"

    def _apply_env_dot(self, env: str) -> None:
        try:
            env_up = (env or "").strip().upper()
            style = "warning"
            if env_up == "ONLINE":
                style = "success"
            elif env_up == "OFFLINE":
                style = "danger"
            self.status_dot.configure(bootstyle=style)
        except Exception:
            pass

    def _merge_status_text(self, env_text: Optional[str] = None) -> None:
        env = env_text if env_text is not None else self._get_env_text()
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
        suffix = f" | Usuario: {email} ({role})" if email else ""
        self.status_var_text.set(f"{env}{suffix}")
        try:
            self._apply_env_dot(env)
        except Exception:
            pass

    def on_net_status_change(self, st: Status) -> None:
        was_online = getattr(self, "_net_is_online", True)
        self._net_is_online = (st == Status.ONLINE)
        self._update_main_buttons_state()
        if not self._net_is_online and was_online and not self._offline_alerted:
            self._offline_alerted = True
            try:
                messagebox.showwarning(
                    "Sem conexão",
                    "Este aplicativo exige internet para funcionar. Verifique sua conexão e tente novamente.",
                    parent=self
                )
            except Exception:
                pass
        if self._net_is_online:
            self._offline_alerted = False

    def _update_user_status(self) -> None:
        self._merge_status_text()

    def _schedule_user_status_refresh(self) -> None:
        self._update_user_status()
        try:
            txt = (self.status_var_text.get() or "")
        except Exception:
            txt = ""
        if "Usuario:" not in txt:
            try:
                self.after(300, self._schedule_user_status_refresh)
            except Exception:
                pass
        try:
            self.bind("<FocusIn>", lambda e: self._update_user_status(), add="+")
        except Exception:
            pass

    # ---------- Lista ----------
    def _resolve_order_preferences(self) -> tuple[Optional[str], bool]:
        label = self.var_ordem.get()
        return ORDER_CHOICES.get(label, (None, False))

    def _set_count_text(self, count: int) -> None:
        try:
            text = "1 cliente" if count == 1 else f"{count} clientes"
            self.clients_count_var.set(text)
        except Exception:
            pass

    def carregar(self) -> None:
        order_label = self.var_ordem.get()
        search_term = self.var_busca.get().strip()
        column, reverse_after = self._resolve_order_preferences()
        log.info("Atualizando lista (busca='%s', ordem='%s')", search_term, order_label)
        try:
            clientes = search_clientes(search_term, column)
            if reverse_after:
                clientes = list(reversed(clientes))
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao carregar lista: {exc}")
            return

        try:
            self.client_list.delete(*self.client_list.get_children())
        except Exception:
            pass

        def _get(obj, key, *alts):
            keys = (key,) + alts
            for k in keys:
                if isinstance(obj, dict):
                    if k in obj:
                        return obj.get(k)
                else:
                    if hasattr(obj, k):
                        return getattr(obj, k)
            return None

        def _format_cnpj_safe(valor: str) -> str:
            raw = (valor or "").strip()
            try:
                out = format_cnpj(raw)
                if out:
                    return out
            except Exception:
                pass
            s = "".join(ch for ch in raw if ch.isdigit())
            if len(s) > 14:
                s = s[-14:]
            if len(s) != 14:
                return raw
            return f"{s[0:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:14]}"

        def _format_whats_display(num: str) -> str:
            raw = str(num or "")
            digits = re.sub(r"\D+", "", raw)
            if not digits:
                return ""
            natl = digits[2:] if digits.startswith("55") else digits
            if len(natl) < 10:
                return f"+55 {natl}"
            ddd, local = natl[:2], natl[2:]
            if len(local) >= 9:
                return f"{ddd} {local[:5]}-{local[5:9]}"
            else:
                return f"{ddd} {local[:4]}-{local[4:8]}"

        for cli in clientes:
            cnpj_fmt = _format_cnpj_safe(str(_get(cli, "cnpj") or ""))
            numero_raw = str(_get(cli, "numero", "whatsapp", "telefone") or "")
            numero_disp = _format_whats_display(numero_raw)
            obs_txt = (_get(cli, "observacoes", "obs") or "").strip()

            values = (
                _get(cli, "id", "pk", "client_id"),
                _get(cli, "razao_social", "razao"),
                cnpj_fmt,
                _get(cli, "nome"),
                numero_disp,
                obs_txt,
                fmt_data(_get(cli, "updated_at", "ultima_alteracao")),
            )
            tags = ("has_obs",) if obs_txt else ()
            self.client_list.insert("", "end", values=values, tags=tags)

        count = len(clientes) if isinstance(clientes, (list, tuple)) else len(self.client_list.get_children())
        self._set_count_text(count)
        self._update_main_buttons_state()

    def _sort_by(self, column: str) -> None:
        current = self.var_ordem.get()
        if column == "updated_at":
            new_value = "Ultima Alteracao (mais antiga)" if current == "Ultima Alteracao (mais recente)" else "Ultima Alteracao (mais recente)"
            self.var_ordem.set(new_value)
        elif column in ("razao_social", "cnpj", "nome"):
            mapping = {
                "razao_social": "Razao Social (A->Z)",
                "cnpj": "CNPJ (A->Z)",
                "nome": "Nome (A->Z)",
            }
            self.var_ordem.set(mapping[column])
        else:
            return
        self.carregar()

    # ---------- Acoes ----------
    def _get_selected_values(self) -> Optional[Sequence[Any]]:
        try:
            selection = self.client_list.selection()
        except Exception:
            return None
        if not selection:
            return None
        item_id = selection[0]
        try:
            return self.client_list.item(item_id, "values")
        except Exception:
            return None

    def novo_cliente(self) -> None:
        app_core.novo_cliente(self)

    def editar_cliente(self) -> None:
        values = self._get_selected_values()
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
        values = self._get_selected_values()
        if not values:
            messagebox.showwarning("Atencao", "Selecione um cliente primeiro.")
            return
        client_id = values[0]
        razao = (values[1] or "").strip()
        cnpj  = (values[2] or "").strip()

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

    # -------- Busca / Filtros --------
    def _buscar(self, event: Any | None = None) -> None:
        try:
            if self._buscar_after:
                self.after_cancel(self._buscar_after)
        except Exception:
            pass
        self._buscar_after = self.after(200, self.carregar)

    def _limpar_busca(self) -> None:
        self.var_busca.set("")
        self.carregar()

    # -------- Clique no WhatsApp --------
    def _on_click(self, event: Any) -> None:
        item = self.client_list.identify_row(event.y)
        col = self.client_list.identify_column(event.x)
        if not item or col != "#5":
            return
        cell = self.client_list.item(item, "values")[4] or ""
        digits = re.sub(r"\D+", "", str(cell))
        if not digits:
            return
        phone = digits if digits.startswith("55") else f"55{digits}"
        msg = "Olá, tudo bem?"
        webbrowser.open_new_tab(
            f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg)}")

    # ---------- Estados dos botões ----------
    def _update_main_buttons_state(self, *_: Any) -> None:
        has_sel = bool(self.client_list.selection())
        online = bool(getattr(self, "_net_is_online", True))
        try:
            self.btn_editar.configure(state=("normal" if (has_sel and online) else "disabled"))
            self.btn_subpastas.configure(state=("normal" if (has_sel and online) else "disabled"))
            self.btn_enviar.configure(state=("normal" if (has_sel and online) else "disabled"))
            self.btn_novo.configure(state=("normal" if online else "disabled"))
            self.btn_lixeira.configure(state=("normal" if online else "disabled"))
        except Exception:
            pass

    def _excluir_cliente(self) -> None:
        values = self._get_selected_values()
        if values:
            app_core.excluir_cliente(self, values)

    # -------- Upload para Supabase (com telinha indeterminada) --------
    def enviar_para_supabase(self) -> None:
        values = self._get_selected_values()
        if not values:
            messagebox.showwarning("Atencao", "Selecione um cliente primeiro.")
            return

        client_id = values[0]
        pasta = filedialog.askdirectory(title="Escolha a pasta local para enviar ao Supabase", parent=self)
        if not pasta:
            return

        dlg = tk.Toplevel(self)
        dlg.withdraw()
        dlg.title("Aguarde…")
        try:
            dlg.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Enviando arquivos para o Supabase…").pack(anchor="w", pady=(0, 8))
        pb = ttk.Progressbar(frm, mode="indeterminate", length=300)
        pb.pack(fill="x")
        pb.start(12)

        # centraliza e mostra
        self.update_idletasks()
        w, h = 360, 120
        dlg.geometry(f"{w}x{h}")
        try:
            dlg.update_idletasks()
            center_on_parent(dlg, self)
        except Exception:
            pass
        dlg.deiconify()

        result = {"ok": None, "err": None}

        def _worker():
            try:
                resultados = upload_folder_to_supabase(pasta, int(client_id), subdir="SIFAP")
                result["ok"] = len(resultados)
            except Exception as exc:
                result["err"] = str(exc)
            finally:
                self.after(0, _finish)

        def _finish():
            try:
                pb.stop()
            except Exception:
                pass
            try:
                dlg.grab_release()
                dlg.destroy()
            except Exception:
                pass

            if result["err"] is not None:
                messagebox.showerror("Erro ao enviar", result["err"], parent=self)
            else:
                ok = result["ok"] or 0
                messagebox.showinfo("Envio concluido", f"{ok} arquivo(s) enviados para o Supabase.", parent=self)

        threading.Thread(target=_worker, daemon=True).start()

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
                return self._user_cache
        except Exception:
            pass
        return None

    def _get_role_cached(self, uid: str) -> str:
        if self._role_cache:
            return self._role_cache
        try:
            from infra.supabase_client import supabase
            res = supabase.table("memberships").select("role").eq("user_id", uid).limit(1).execute()
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
            from infra.supabase_client import supabase
            res = supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1).execute()
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
            with open(resource_path("CHANGELOG.md"), "r", encoding="utf-8") as f:
                conteudo = f.read()
            preview = "\n".join(conteudo.splitlines()[:20])
            messagebox.showinfo("Changelog", preview, parent=self)
        except Exception:
            messagebox.showinfo("Changelog", "Arquivo CHANGELOG.md nao encontrado.", parent=self)


# -------- Splash: barra indeterminada antes do Login --------
def show_splash(root: tk.Misc, min_ms: int = 1200) -> tb.Toplevel:
    splash = tb.Toplevel(root)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash.lift()

    frame = tb.Frame(splash, padding=16)
    frame.pack(fill="both", expand=True)
    tb.Label(frame, text="Carregando…").pack(pady=(0, 8))
    pb = tb.Progressbar(frame, mode="indeterminate", length=220)
    pb.pack()
    splash.after(10, pb.start)

    splash.update_idletasks()
    w, h = 260, 96
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    splash.update()

    def _close():
        if splash.winfo_exists():
            try:
                splash.attributes("-topmost", False)
            except Exception:
                pass
            splash.destroy()
    splash.after(min_ms, _close)
    return splash


# ---- Verbose logs (opcional, controlado por RC_VERBOSE=1) ----
import os as _os, functools as _functools, logging as _logging

_VERB = (_os.getenv("RC_VERBOSE") or "").strip().lower() in {"1", "true", "yes", "on"}


def _log_call(fn):
    log = _logging.getLogger("ui.actions")

    @_functools.wraps(fn)
    def _wrap(self, *a, **kw):
        if _VERB:
            log.info("CALL %s", fn.__name__)
        try:
            return fn(self, *a, **kw)
        except Exception:
            log.exception("ERROR in %s", fn.__name__)
            raise

    return _wrap


try:
    App.novo_cliente = _log_call(App.novo_cliente)
    App.editar_cliente = _log_call(App.editar_cliente)
    App.ver_subpastas = _log_call(App.ver_subpastas)
    App.enviar_para_supabase = _log_call(App.enviar_para_supabase)
    App._buscar = _log_call(App._buscar)
    App._on_click = _log_call(App._on_click)
except Exception:
    pass


if __name__ == "__main__":
    import logging
    from ui.login import LoginDialog

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("startup")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app = App(start_hidden=True)

    splash = show_splash(app, min_ms=1200)

    def _open_login_after_splash():
        try:
            if splash.winfo_exists():
                splash.destroy()
        except Exception:
            pass

        dlg = LoginDialog(app)
        app.wait_window(dlg)

        if getattr(dlg, "result", None):
            app.deiconify()
            try:
                app._update_user_status()
                app.show_hub_screen()
            except Exception as e:
                log.error("Erro ao carregar UI: %s", e)
        else:
            app.destroy()

    app.after(1250, _open_login_after_splash)
    app.mainloop()
