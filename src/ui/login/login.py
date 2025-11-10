# ui/login.py
from __future__ import annotations

import os

import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox

from src.core import session
from src.core.auth import authenticate_user, ensure_users_db, validate_credentials

try:
    from ui import center_on_parent
except Exception:  # pragma: no cover
    try:
        from src.ui.utils import center_on_parent
    except Exception:  # pragma: no cover

        def center_on_parent(win, parent=None, pad=0):
            return win


from src.utils.resource_path import resource_path


class LoginDialog(tb.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Evita aparecer desalinhado
        self.withdraw()

        # Tornar modal e acima do parent
        if parent:
            try:
                self.transient(parent)
            except Exception:
                pass

        # Sempre por cima da janela principal
        self.attributes("-topmost", True)

        # Ícone da janela de login
        try:
            ico = resource_path("rc.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)  # Windows (.ico)
        except Exception:
            # fallback opcional para PNG:
            # import tkinter as tk
            # self.iconphoto(True, tk.PhotoImage(file=resource_path("rc.png")))
            pass

        self.title("Login - Gestor de Clientes")

        # --- Geometria responsiva + centralização ---
        try:
            self.update_idletasks()  # garante métricas consistentes em algumas plataformas
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        except Exception:
            sw, sh = 1366, 768  # fallback

        # Breakpoints de tamanho da janela de login
        if sw >= 1920 and sh >= 1080:  # Full HD ou maior
            w, h = 420, 260
        elif sw >= 1366 and sh >= 768:  # HD
            w, h = 380, 230
        else:  # telas menores
            w, h = 350, 210

        self.geometry(f"{w}x{h}")
        self.resizable(False, False)

        # Centralizar sem piscar
        self.update_idletasks()
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        except Exception:
            sw, sh = 1366, 768

        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.deiconify()
        self.lift()

        self.result = False

        # -------- UI --------
        frame = tb.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        tb.Label(frame, text="E-mail").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.ent_user = tb.Entry(frame, width=28)
        self.ent_user.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tb.Label(frame, text="Senha").grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.ent_pass = tb.Entry(frame, width=28, show="•")
        self.ent_pass.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.btn_login = tb.Button(
            frame, text="Entrar", bootstyle="success", command=self._do_login
        )
        self.btn_login.grid(row=4, column=0, sticky="e")

        btn_cancel = tb.Button(
            frame, text="Sair", bootstyle="danger", command=self._cancel
        )
        btn_cancel.grid(row=4, column=1, sticky="w")

        # atalhos
        self.bind("<Return>", lambda e: self._do_login())
        self.bind("<Escape>", lambda e: self._cancel())

        for i in range(2):
            frame.columnconfigure(i, weight=1)

        # Modalidade (bloqueia a janela principal)
        try:
            self.grab_set()
        except Exception:
            pass

        self.focus_force()
        self.ent_user.focus_set()

        ensure_users_db()

        # Fechar no X chama cancel
        try:
            self.protocol("WM_DELETE_WINDOW", self._cancel)
        except Exception:
            pass

    # -------- Lógica --------
    def _do_login(self):
        email = (self.ent_user.get() or "").strip()
        password = self.ent_pass.get() or ""

        # Validação imediata de formato
        err = validate_credentials(email, password)
        if err:
            Messagebox.show_warning(err, "Atenção", parent=self)
            self.ent_user.focus_set()
            self.result = False
            return

        # Feedback visual - desabilitar botão durante autenticação
        self.btn_login.configure(state="disabled")
        self.update_idletasks()

        # Autenticar no Supabase
        ok, msg = authenticate_user(email, password)

        if ok:
            # Sucesso: guardar e-mail autenticado
            self.logged_email = msg  # e-mail retornado pelo Supabase
            session.set_current_user(msg)

            # Hidratar AuthController com dados completos do usuário
            try:
                # [finalize-notes] import seguro dentro de função
                from infra.supabase_client import get_supabase

                sb = get_supabase()
                user = sb.auth.get_user()
                if user and hasattr(user, "user"):
                    user_data = {
                        "id": user.user.id,
                        "email": user.user.email or msg,
                        "created_at": getattr(user.user, "created_at", None),
                        "user_metadata": getattr(user.user, "user_metadata", {}),
                    }

                    # Tentar obter org_id (pode vir de user_metadata ou de tabela users)
                    # Será obtido posteriormente via _get_org_id_cached no main_window

                    # Atualizar AuthController do app se disponível
                    if hasattr(self.master, "auth"):
                        self.master.auth.set_user_data(user_data)
            except Exception as e:
                # Não falhar o login se houver erro aqui
                import logging

                logging.getLogger(__name__).warning(
                    "Não foi possível hidratar dados do usuário: %s", e
                )

            self.result = True
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()
            return

        # Falha: reabilitar botão e mostrar erro
        self.btn_login.configure(state="normal")
        Messagebox.show_error(msg, "Não foi possível entrar", parent=self)
        self.result = False
        # Permanece aberto para tentar novamente
        self.focus_force()
        self.ent_user.focus_set()

    def _cancel(self):
        self.result = False
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
