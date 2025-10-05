import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
from core.auth import ensure_users_db, authenticate_user
from core import session

class LoginDialog(tb.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # NADA de tb.Style() aqui. O login herda o tema do App (root único).
        # Se quiser muito o login sempre claro, dá pra por:
        # if hasattr(self, "set_theme"): self.set_theme("flatly")

        self.title("Login - Gestor de Clientes")
        self.geometry(
            "360x220+{}+{}".format(
                self.winfo_screenwidth() // 2 - 180,
                self.winfo_screenheight() // 2 - 110,
            )
        )
        self.resizable(False, False)
        self.result = False

        frame = tb.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        tb.Label(frame, text="Usuário").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.ent_user = tb.Entry(frame, width=28)
        self.ent_user.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.ent_user.focus_set()

        tb.Label(frame, text="Senha").grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.ent_pass = tb.Entry(frame, width=28, show="•")
        self.ent_pass.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        btn_login = tb.Button(frame, text="Entrar", bootstyle="success", command=self._do_login)
        btn_login.grid(row=4, column=0, sticky="e")

        btn_cancel = tb.Button(frame, text="Sair", bootstyle="danger", command=self._cancel)
        btn_cancel.grid(row=4, column=1, sticky="w")

        self.bind("<Return>", lambda e: self._do_login())
        self.bind("<Escape>", lambda e: self._cancel())

        for i in range(2):
            frame.columnconfigure(i, weight=1)

        ensure_users_db()
        self.grab_set()
        self.focus_force()

    def _do_login(self):
        user = self.ent_user.get().strip()
        pwd = self.ent_pass.get()
        if not user or not pwd:
            self.grab_release()
            Messagebox.show_warning("Informe usuário e senha.", "Login", parent=self)
            self.grab_set()
            return
        if authenticate_user(user, pwd):
            session.set_current_user(user)
            self.result = True
            self.destroy()
        else:
            self.grab_release()
            Messagebox.show_error("Usuário ou senha inválidos.", "Login", parent=self)
            self.grab_set()

    def _cancel(self):
        self.result = False
        self.destroy()
