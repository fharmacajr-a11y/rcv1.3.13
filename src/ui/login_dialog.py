# ---------------- gui/login_dialog.py ----------------
import logging
import os
import re
import time
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, INFO

from src.db.auth_bootstrap import _get_access_token
from src.infra.healthcheck import healthcheck  # <-- ADICIONADO: health check pós-login
from src.infra.supabase_client import bind_postgrest_auth_if_any, get_supabase
from src.core.auth.auth import authenticate_user  # Import for authenticate_user
from src.core.session.session import (  # <-- importa sessão
    refresh_current_user_from_supabase,
)
from src.utils.resource_path import resource_path
from src.utils import prefs as prefs_utils

log = logging.getLogger(__name__)


class LoginDialog(tk.Toplevel):
    """Diálogo simples de login para Supabase."""

    def __init__(self, master):
        t0 = time.perf_counter()
        super().__init__(master)
        self.withdraw()
        self.title("Login - Gestor de Clientes")
        self.resizable(False, False)

        # Ícone da janela de login (mesmo rc.ico do app)
        try:
            icon_path = resource_path("rc.ico")
            if os.path.exists(icon_path):
                try:
                    self.iconbitmap(icon_path)
                except Exception:
                    try:
                        img = tk.PhotoImage(file=icon_path)
                        self.iconphoto(True, img)
                    except Exception as exc:  # noqa: BLE001
                        log.debug("Falha ao definir iconphoto em login_dialog: %s", exc)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao definir ícone em login_dialog: %s", exc)

        # Variáveis
        self.email_var = tk.StringVar(master=self)
        self.pass_var = tk.StringVar(master=self)
        self.remember_email_var = tk.BooleanVar(master=self, value=True)
        self.keep_logged_var = tk.BooleanVar(master=self, value=False)
        self.login_success = False

        # Ícones do login
        try:
            email_icon_path = resource_path("assets/login/email.png")
            senha_icon_path = resource_path("assets/login/senha.png")
        except Exception:
            email_icon_path = None
            senha_icon_path = None

        self._icon_email = None
        self._icon_senha = None

        if email_icon_path:
            try:
                self._icon_email = tk.PhotoImage(file=email_icon_path)
            except Exception:
                self._icon_email = None

        if senha_icon_path:
            try:
                self._icon_senha = tk.PhotoImage(file=senha_icon_path)
            except Exception:
                self._icon_senha = None

        # Layout
        self.email_label = ttk.Label(
            self,
            text="E-mail",
            image=self._icon_email,
            compound="left" if self._icon_email is not None else "none",
            padding=0,
            anchor="w",
        )
        self.email_label.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.email_entry = ttk.Entry(self, textvariable=self.email_var, width=36, bootstyle=INFO)
        self.email_entry.grid(row=1, column=0, padx=8, pady=(0, 8))

        self.pass_label = ttk.Label(
            self,
            text="Senha",
            image=self._icon_senha,
            compound="left" if self._icon_senha is not None else "none",
            padding=0,
            anchor="w",
        )
        self.pass_label.grid(row=2, column=0, sticky="w", padx=8, pady=(8, 2))
        self.pass_entry = ttk.Entry(self, textvariable=self.pass_var, width=36, show="•", bootstyle=INFO)
        self.pass_entry.grid(row=3, column=0, padx=8, pady=(0, 8))

        self.remember_email_check = ttk.Checkbutton(
            self,
            text="Lembrar e-mail",
            variable=self.remember_email_var,
            bootstyle=INFO,
        )
        self.remember_email_check.grid(row=4, column=0, padx=8, pady=(0, 4), sticky="w")

        self.keep_logged_check = ttk.Checkbutton(
            self,
            text="Não pedir senha por 7 dias",
            variable=self.keep_logged_var,
            bootstyle=INFO,
        )
        self.keep_logged_check.grid(row=5, column=0, padx=8, pady=(0, 4), sticky="w")

        self.separator_bottom = ttk.Separator(self, orient="horizontal")
        self.separator_bottom.grid(row=6, column=0, columnspan=2, padx=8, pady=(12, 8), sticky="ew")

        self.buttons_frame = ttk.Frame(self)
        self.buttons_frame.grid(row=7, column=0, columnspan=2, padx=8, pady=(8, 12))

        self.exit_btn = ttk.Button(
            self.buttons_frame,
            text="Sair",
            command=self._on_exit,
            bootstyle=DANGER,
        )
        self.exit_btn.pack(side="left", padx=(0, 8))

        self.login_btn = ttk.Button(
            self.buttons_frame,
            text="Entrar",
            command=self._do_login,
            bootstyle=INFO,
        )
        self.login_btn.pack(side="left")

        # Bindings
        self._bind_enter()
        self.bind("<Escape>", lambda e: self.destroy())

        # Modal + foco inicial inteligente
        try:
            login_prefs = prefs_utils.load_login_prefs()
        except Exception:
            login_prefs = {}

        # Começa assumindo os defaults atuais da UI
        remember = bool(self.remember_email_var.get())
        prefilled_email = (self.email_var.get() or "").strip()

        if login_prefs:
            # Aplica preferências salvas de login, se existirem
            remember = bool(login_prefs.get("remember_email", True))
            email = str(login_prefs.get("email", "")).strip()
            self.remember_email_var.set(remember)
            if remember and email:
                self.email_var.set(email)
                prefilled_email = email

        # Regra de UX:
        # - Se já temos um e-mail preenchido, foco direto na senha
        # - Caso contrário, foco no campo de e-mail
        target_entry = self.pass_entry if remember and prefilled_email else self.email_entry
        target_entry.focus_set()
        # Reaplica foco no ciclo seguinte para dialogos criados em sequencia
        self.after_idle(target_entry.focus_force)

        # Centralizar e exibir (UI-GLOBAL-01)
        from src.ui.window_utils import show_centered

        # FIX: Garantir que o layout seja calculado completamente antes de centralizar
        self.update_idletasks()

        # Definir tamanho mínimo explícito para evitar corte
        req_w = self.winfo_reqwidth()
        req_h = self.winfo_reqheight()
        if req_w > 1 and req_h > 1:
            self.minsize(req_w, req_h)

        show_centered(self)
        try:
            log.info("LoginDialog: inicializado em %.3fs", time.perf_counter() - t0)
        except Exception:
            log.debug("Falha ao registrar log de inicialização do LoginDialog", exc_info=True)

    def _bind_enter(self):
        self.bind("<Return>", lambda e: self._do_login())

    def _unbind_enter(self):
        self.unbind("<Return>")

    def _do_login(self):
        """Executa o login com Supabase."""
        email = self.email_var.get().strip()
        password = self.pass_var.get()

        if not email or not password:
            messagebox.showerror("Erro", "Preencha e-mail e senha.", parent=self)
            return

        client = get_supabase()

        ok, msg = authenticate_user(email, password)
        if ok:
            # Aplicar token no PostgREST
            bind_postgrest_auth_if_any(client)

            # Verificar sessão
            sess = client.auth.get_session()
            uid = getattr(sess, "user", None) and getattr(sess.user, "id", None)
            token = _get_access_token(client)

            log.info(
                "Login OK: user.id=%s | token=%s",
                uid,
                "presente" if token else "ausente",
            )

            if not token:
                messagebox.showerror(
                    "Erro",
                    "Login não gerou token. Verifique credenciais/E-mail confirmado.",
                    parent=self,
                )
                return

            # >>>>>>> ATUALIZA USUÁRIO ATUAL (carrega org_id da memberships)
            try:
                refresh_current_user_from_supabase()
            except Exception as e:
                log.warning("Falha ao atualizar sessão/org_id: %s", e)

            # >>>>>>> HEALTHCHECK PÓS-LOGIN (INSERT/DELETE em public.test_health + storage)
            try:
                hc = healthcheck()
                # Log apenas se falhar (evitar spam)
                if not hc["ok"]:
                    logging.getLogger("health").warning("HEALTH: falhou - itens=%s", hc["items"])
            except Exception as e:
                logging.getLogger("health").warning("HEALTH: falhou ao executar healthcheck: %r", e)

            try:
                remember = bool(self.remember_email_var.get())
            except Exception:
                remember = True

            try:
                prefs_utils.save_login_prefs(self.email_var.get(), remember)
            except Exception:
                # Não quebrar o login se falhar ao salvar prefs
                log.warning("Falha ao salvar preferências de login", exc_info=True)

            try:
                keep_logged = bool(self.keep_logged_var.get())
            except Exception:
                keep_logged = False

            try:
                sess_response = client.auth.get_session()
                sess_obj = getattr(sess_response, "session", None) or sess_response
                access_token = getattr(sess_obj, "access_token", "") or ""
                refresh_token = getattr(sess_obj, "refresh_token", "") or ""
                if keep_logged and access_token and refresh_token:
                    prefs_utils.save_auth_session(access_token, refresh_token, keep_logged=True)
                else:
                    prefs_utils.clear_auth_session()
            except Exception:
                log.warning("Falha ao salvar/limpar sessão persistida", exc_info=True)

            # Sucesso
            self.login_success = True
            self.destroy()
        else:
            messagebox.showerror("Erro no login", msg, parent=self)
            # Se bloqueado, disable botão por segundos
            m = re.search(r"Aguarde (\d+)s", msg)
            if m:
                seconds = int(m.group(1))
                self._disable_for(seconds)

    def _on_exit(self) -> None:
        """Fecha o diálogo de login como cancelamento."""
        self.destroy()

    def _disable_for(self, seconds: int):
        self.login_btn.config(state="disabled")
        self._unbind_enter()  # Desabilita Enter
        self.after(seconds * 1000, lambda: self._enable_btn())

    def _enable_btn(self):
        self.login_btn.config(state="normal")
        self._bind_enter()  # Re-habilita Enter
