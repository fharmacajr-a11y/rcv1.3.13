# ui/login.py
from __future__ import annotations

import os
import sys
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
from core.auth import ensure_users_db, authenticate_user
from core import session

try:
    from ui import center_on_parent
except Exception:  # pragma: no cover
    try:
        from ui.utils import center_on_parent
    except Exception:  # pragma: no cover
        def center_on_parent(win, parent=None, pad=0):
            return win

try:
    from utils.resource_path import resource_path as _resource_path
except Exception:  # pragma: no cover
    def _resource_path(rel: str) -> str:
        base = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base, rel)

resource_path = _resource_path


class LoginDialog(tb.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Tornar modal e acima do parent
        if parent:
            try:
                self.transient(parent)
            except Exception:
                pass

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
        if sw >= 1920 and sh >= 1080:      # Full HD ou maior
            w, h = 420, 260
        elif sw >= 1366 and sh >= 768:     # HD
            w, h = 380, 230
        else:                              # telas menores
            w, h = 350, 210

        self.geometry(f"{w}x{h}")
        self.resizable(False, False)

        try:
            self.update_idletasks()
            center_on_parent(self, parent)
        except Exception:
            pass

        self.result = False

        # -------- UI --------
        frame = tb.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        tb.Label(frame, text="Usuário").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.ent_user = tb.Entry(frame, width=28)
        self.ent_user.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tb.Label(frame, text="Senha").grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.ent_pass = tb.Entry(frame, width=28, show="•")
        self.ent_pass.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        btn_login = tb.Button(frame, text="Entrar", bootstyle="success", command=self._do_login)
        btn_login.grid(row=4, column=0, sticky="e")

        btn_cancel = tb.Button(frame, text="Sair", bootstyle="danger", command=self._cancel)
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
        user = (self.ent_user.get() or "").strip()
        pwd = (self.ent_pass.get() or "").strip()

        if not user or not pwd:
            Messagebox.show_warning("Preencha e-mail e senha.", "Login", parent=self)
            self.ent_user.focus_set()
            return

        try:
            self.grab_release()
        except Exception:
            pass

        ok = authenticate_user(user, pwd)
        if ok:
            # guarda e-mail da sessão (fallback simples)
            session.set_current_user(user)
            self.result = True
            self.destroy()
            return

        # falha
        try:
            self.grab_set()
        except Exception:
            pass
        Messagebox.show_error("Usuário ou senha inválidos.", "Login", parent=self)
        self.ent_pass.focus_set()
        self.ent_pass.selection_range(0, "end")

    def _cancel(self):
        self.result = False
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
