from __future__ import annotations

from tkinter import Toplevel, StringVar, DoubleVar, ttk, messagebox
from datetime import date
from typing import Optional, Dict, Any

# ttkbootstrap DateEntry
try:
    from ttkbootstrap.widgets import DateEntry  # type: ignore
except Exception:  # fallback simples (campo texto)
    DateEntry = None  # type: ignore

CATEGORIES_IN = ["Vendas", "Serviços", "Outros"]
CATEGORIES_OUT = ["Compra", "Impostos", "Folha", "Aluguel", "Outros"]


class EntryDialog(Toplevel):
    def __init__(self, master, initial: Optional[Dict[str, Any]] = None, title="Lançamento"):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()

        self.var_type = StringVar(value=(initial or {}).get("type", "IN"))
        self.var_date = StringVar(value=(initial or {}).get("date", str(date.today())))
        self.var_category = StringVar(value=(initial or {}).get("category", ""))
        self.var_desc = StringVar(value=(initial or {}).get("description", ""))
        self.var_amount = DoubleVar(value=float((initial or {}).get("amount") or 0.0))
        self.var_account = StringVar(value=(initial or {}).get("account", ""))

        frm = ttk.Frame(self, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Tipo").grid(row=0, column=0, sticky="w")
        cb_type = ttk.Combobox(
            frm, textvariable=self.var_type, values=["IN", "OUT"], state="readonly", width=10
        )
        cb_type.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frm, text="Data").grid(row=1, column=0, sticky="w")
        if DateEntry:
            de = DateEntry(frm, dateformat="%Y-%m-%d")
            de.entry.delete(0, "end")
            de.entry.insert(0, self.var_date.get())
            de.entry.configure(textvariable=self.var_date)
            de.grid(row=1, column=1, sticky="ew", pady=2)
        else:
            ttk.Entry(frm, textvariable=self.var_date).grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frm, text="Categoria").grid(row=2, column=0, sticky="w")
        self.cb_cat = ttk.Combobox(frm, textvariable=self.var_category, values=self._cats(), width=22)
        self.cb_cat.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frm, text="Descrição").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_desc).grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(frm, text="Valor").grid(row=4, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_amount).grid(row=4, column=1, sticky="ew", pady=2)

        ttk.Label(frm, text="Conta").grid(row=5, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_account).grid(row=5, column=1, sticky="ew", pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(btns, text="Cancelar", command=self._cancel, bootstyle="secondary").pack(
            side="right", padx=4
        )
        ttk.Button(btns, text="Salvar", command=self._ok, bootstyle="success").pack(
            side="right", padx=4
        )

        frm.columnconfigure(1, weight=1)
        cb_type.bind("<<ComboboxSelected>>", lambda e: self._update_cats())

        self.result = None

    def _cats(self):
        return CATEGORIES_IN if self.var_type.get() == "IN" else CATEGORIES_OUT

    def _update_cats(self):
        self.cb_cat.configure(values=self._cats())

    def _cancel(self):
        self.result = None
        self.destroy()

    def _ok(self):
        try:
            amt = float(self.var_amount.get())
            if amt <= 0:
                raise ValueError("Valor deve ser > 0")
        except Exception:
            messagebox.showerror("Valor inválido", "Informe um número maior que zero.")
            return
        self.result = {
            "type": self.var_type.get(),
            "date": self.var_date.get(),
            "category": self.var_category.get() or "Outros",
            "description": self.var_desc.get(),
            "amount": amt,
            "account": self.var_account.get(),
        }
        self.destroy()
