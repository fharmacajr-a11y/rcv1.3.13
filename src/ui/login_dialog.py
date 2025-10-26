# ---------------- gui/login_dialog.py ----------------
import tkinter as tk
from tkinter import ttk, messagebox
import re
import logging
from infra.supabase_client import get_supabase, bind_postgrest_auth_if_any
from data.auth_bootstrap import _get_access_token
from src.core.auth.auth import authenticate_user  # Import for authenticate_user
from src.core.session.session import refresh_current_user_from_supabase  # <-- importa sessão
from infra.healthcheck import healthcheck  # <-- ADICIONADO: health check pós-login

log = logging.getLogger(__name__)


class LoginDialog(tk.Toplevel):
    """Diálogo simples de login para Supabase."""
    
    def __init__(self, master):
        super().__init__(master)
        self.title("Entrar")
        self.resizable(False, False)
        
        # Variáveis
        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.login_success = False
        
        # Layout
        ttk.Label(self, text="E-mail").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.email_entry = ttk.Entry(self, textvariable=self.email_var, width=36)
        self.email_entry.grid(row=1, column=0, padx=8, pady=(0, 8))
        
        ttk.Label(self, text="Senha").grid(row=2, column=0, sticky="w", padx=8, pady=(8, 2))
        self.pass_entry = ttk.Entry(self, textvariable=self.pass_var, width=36, show="•")
        self.pass_entry.grid(row=3, column=0, padx=8, pady=(0, 8))
        
        self.login_btn = ttk.Button(self, text="Entrar", command=self._do_login)
        self.login_btn.grid(row=4, column=0, padx=8, pady=8, sticky="e")
        
        # Bindings
        self._bind_enter()
        self.bind("<Escape>", lambda e: self.destroy())
        
        # Modal
        self.grab_set()
        self.email_entry.focus_set()
        
        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

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
            
            log.info("Login OK: user.id=%s | token=%s", uid, "presente" if token else "ausente")
            
            if not token:
                messagebox.showerror(
                    "Erro",
                    "Login não gerou token. Verifique credenciais/Email confirmado.",
                    parent=self
                )
                return

            # >>>>>>> ATUALIZA USUÁRIO ATUAL (carrega org_id da memberships)
            try:
                refresh_current_user_from_supabase()
            except Exception as e:
                log.warning("Falha ao atualizar sessão/org_id: %s", e)

            # >>>>>>> HEALTHCHECK PÓS-LOGIN (INSERT/DELETE em public.test_health + storage + tesseract)
            try:
                hc = healthcheck()
                logging.getLogger("health").info("HEALTH: ok=%s | itens=%s", hc["ok"], hc["items"])
            except Exception as e:
                logging.getLogger("health").warning("HEALTH: falhou ao executar healthcheck: %r", e)

            # Sucesso
            self.login_success = True
            self.destroy()
        else:
            messagebox.showerror("Erro no login", msg, parent=self)
            # Se bloqueado, disable botão por segundos
            m = re.search(r'Aguarde (\d+)s', msg)
            if m:
                seconds = int(m.group(1))
                self._disable_for(seconds)

    def _disable_for(self, seconds: int):
        self.login_btn.config(state="disabled")
        self._unbind_enter()  # Desabilita Enter
        self.after(seconds * 1000, lambda: self._enable_btn())

    def _enable_btn(self):
        self.login_btn.config(state="normal")
        self._bind_enter()  # Re-habilita Enter
