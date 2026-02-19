# ui/users/users.py — gerenciador com políticas de admin + layout clássico
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
import sqlite3
import logging
from datetime import datetime

from core.auth.auth import ensure_users_db, create_user, _pbkdf2_hash
from core.logs.audit import last_action_of_user
from config.paths import USERS_DB_PATH
from utils.file_utils import format_datetime
from ui.utils import center_window  # <<< novo import centralizado

log = logging.getLogger("ui.users")

ADMIN_ID = 1  # considera id 1 como admin raiz
ADMIN_NAME = "admin"


class UserManagerDialog(tk.Toplevel):
    def __init__(self, master=None, current_role="admin"):
        super().__init__(master)
        self.title("Gerenciar Usuários")
        self.geometry("520x360")
        self.transient(master)
        self.grab_set()

        self._mini_form = None

        try:
            ensure_users_db()
        except Exception as e:
            log.exception("ensure_users_db falhou: %s", e)

        cols = ("id", "username", "last")
        self.tree = tb.Treeview(self, columns=cols, show="headings", height=10, bootstyle="dark")
        self.tree.heading("id", text="ID", anchor="center")
        self.tree.heading("username", text="Usuário", anchor="w")
        self.tree.heading("last", text="Última ação", anchor="w")
        self.tree.column("id", width=60, anchor="center", stretch=False)
        self.tree.column("username", width=200, anchor="w", stretch=True)
        self.tree.column("last", width=220, anchor="w", stretch=True)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Rodapé ---
        footer = tb.Frame(self)
        footer.pack(fill="x", padx=10, pady=(0, 10))

        # Esquerda: CRUD (somente se for admin)
        is_admin = (current_role or "").lower() == "admin"
        if is_admin:
            tb.Button(footer, text="Adicionar", bootstyle="success", command=self.add_user).pack(side="left", padx=5)
            tb.Button(footer, text="Editar", bootstyle="info", command=self.edit_user).pack(side="left", padx=5)
            tb.Button(footer, text="Excluir", bootstyle="danger", command=self.delete_user).pack(side="left", padx=5)

        # Direita: ↻ (ícone) e Fechar
        tb.Button(footer, text="Fechar", bootstyle="secondary", command=self.destroy).pack(side="right", padx=5)
        tb.Button(footer, text="↻", width=3, bootstyle="secondary", command=self.load_users).pack(side="right", padx=5)

        self.load_users()
        center_window(self, 520, 360)  # <<< centralização padrão
        # Atalho: F5 para recarregar
        self.bind("<F5>", lambda e: (self.load_users(), "break"))

    # ---------------- utils ----------------
    def _conn(self):
        USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(USERS_DB_PATH))

    # ---------------- CRUD ----------------
    def load_users(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        rows = []
        try:
            ensure_users_db()
            with self._conn() as con:
                cur = con.cursor()
                try:
                    cur.execute("SELECT id, username FROM users WHERE is_active=1 ORDER BY id")
                    rows = cur.fetchall()
                    if not rows:
                        raise Exception("sem_ativos")
                except Exception:
                    cur.execute("SELECT id, username FROM users ORDER BY id")
                    rows = cur.fetchall()
        except Exception as e:
            log.exception("Erro ao carregar usuários: %s", e)

        if not rows:
            try:
                from core.session.session import get_current_user

                uname = get_current_user() or ADMIN_NAME
            except Exception:
                uname = ADMIN_NAME
            self.tree.insert("", "end", values=("-", uname, "-"))
            return

        for uid, uname in rows:
            try:
                raw_last = last_action_of_user(uid)
            except Exception:
                raw_last = None
            last = format_datetime(raw_last) if raw_last else "-"
            self.tree.insert("", "end", values=(uid, uname, last))

    def add_user(self):
        self._user_form(title="Novo Usuário")

    def edit_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Editar", "Selecione um usuário.")
            return
        vals = self.tree.item(sel[0], "values")
        try:
            user_id = int(vals[0]) if vals and vals[0] not in ("-", "") else None
        except Exception:
            user_id = None
        username = vals[1] if len(vals) > 1 else ""
        self._user_form(title="Editar Usuário", user_id=user_id, username=username)

    def delete_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Excluir", "Selecione um usuário.")
            return
        vals = self.tree.item(sel[0], "values")
        try:
            user_id = int(vals[0])
        except Exception:
            messagebox.showwarning("Excluir", "Este registro não pode ser excluído.")
            return
        if user_id == ADMIN_ID:
            messagebox.showwarning("Excluir", "O usuário 'admin' não pode ser excluído.")
            return

        if messagebox.askyesno("Excluir", "Deseja realmente excluir/desativar este usuário?"):
            try:
                with self._conn() as con:
                    cur = con.cursor()
                    try:
                        cur.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
                        if cur.rowcount == 0:
                            raise Exception("sem_coluna")
                        con.commit()
                    except Exception:
                        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
                        con.commit()
                self.load_users()
            except Exception as e:
                log.exception("Erro ao excluir usuário: %s", e)
                messagebox.showerror("Excluir", f"Erro ao excluir: {e}")

    # ---------------- Formulário clássico ----------------
    def _user_form(self, title: str, user_id=None, username: str = ""):
        if self._mini_form is not None:
            try:
                self._mini_form.lift()
                return
            except Exception:
                self._mini_form = None

        top = tb.Toplevel(self)
        self._mini_form = top

        def _close():
            self._mini_form = None
            top.destroy()

        top.title(title)
        top.transient(self)
        top.grab_set()
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", _close)

        frm = tb.Frame(top, padding=14)
        frm.pack(fill="both", expand=True)

        # Usuário
        tb.Label(frm, text="Usuário").grid(row=0, column=0, sticky="w")
        ent_user = tb.Entry(frm, width=34)
        ent_user.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ent_user.insert(0, username or "")

        if user_id == ADMIN_ID or (username or "").lower() == ADMIN_NAME:
            try:
                ent_user.configure(state="disabled")
            except Exception:
                pass

        # Senha + confirmar
        tb.Label(frm, text="Senha").grid(row=2, column=0, sticky="w")
        ent_pwd = tb.Entry(frm, show="*", width=34)
        ent_pwd.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        tb.Label(frm, text="Confirmar senha").grid(row=4, column=0, sticky="w")
        ent_pwd2 = tb.Entry(frm, show="*", width=34)
        ent_pwd2.grid(row=5, column=0, sticky="ew")

        frm.columnconfigure(0, weight=1)

        def _save():
            uname = ent_user.get().strip()
            pwd = ent_pwd.get()
            pwd2 = ent_pwd2.get()

            if not uname and not (user_id == ADMIN_ID):
                messagebox.showwarning(title, "Informe o usuário.")
                return

            if (user_id is None and not pwd) or (pwd or pwd2):
                if pwd != pwd2:
                    messagebox.showwarning(title, "As senhas não coincidem.")
                    return

            try:
                with self._conn() as con:
                    cur = con.cursor()
                    if user_id is None:
                        create_user(uname or ADMIN_NAME, pwd or "admin123")
                    else:
                        if user_id == ADMIN_ID:
                            if pwd:
                                senha_hash = _pbkdf2_hash(pwd)
                                cur.execute(
                                    "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
                                    (senha_hash, datetime.utcnow().isoformat(), user_id),
                                )
                            con.commit()
                        else:
                            cur.execute(
                                "UPDATE users SET username=?, updated_at=? WHERE id=?",
                                (uname, datetime.utcnow().isoformat(), user_id),
                            )
                            if pwd:
                                senha_hash = _pbkdf2_hash(pwd)
                                cur.execute(
                                    "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
                                    (senha_hash, datetime.utcnow().isoformat(), user_id),
                                )
                            con.commit()
                self.load_users()
                _close()
            except Exception as e:
                log.exception("Falha ao salvar usuário: %s", e)
                messagebox.showerror(title, f"Erro ao salvar: {e}")

        btns = tb.Frame(frm)
        btns.grid(row=6, column=0, pady=(12, 0), sticky="e")
        tb.Button(btns, text="Cancelar", bootstyle="secondary", command=_close).pack(side="right", padx=4)
        tb.Button(btns, text="Salvar", bootstyle="success", command=_save).pack(side="right")

        # centraliza usando helper
        center_window(top, 400, 260)
