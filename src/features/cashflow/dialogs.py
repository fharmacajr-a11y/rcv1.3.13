from __future__ import annotations

import logging
from datetime import date
from tkinter import DoubleVar, StringVar, messagebox
from typing import Any, Dict, Optional

# CustomTkinter: fonte única centralizada
from src.ui.ctk_config import ctk
from src.ui.window_utils import show_centered

# CTkDatePicker substituiu ttkbootstrap DateEntry
try:
    from src.ui.widgets import CTkDatePicker
except Exception:  # fallback simples (campo texto)
    CTkDatePicker = None  # type: ignore

log = logging.getLogger(__name__)

CATEGORIES_IN = ["Vendas", "Serviços", "Outros"]
CATEGORIES_OUT = ["Compra", "Impostos", "Folha", "Aluguel", "Outros"]


class EntryDialog(ctk.CTkToplevel):
    def __init__(self, master, initial: Optional[Dict[str, Any]] = None, title="Lan��amento"):
        super().__init__(master)
        self.withdraw()
        self._init_state(initial, title)
        self._build_form()
        self._finalize_modal()

    def _init_state(self, initial: Optional[Dict[str, Any]], title: str) -> None:
        self.title(title)
        self.resizable(False, False)

        self.var_type = StringVar(value=(initial or {}).get("type", "IN"))
        self.var_date = StringVar(value=(initial or {}).get("date", str(date.today())))
        self.var_category = StringVar(value=(initial or {}).get("category", ""))
        self.var_desc = StringVar(value=(initial or {}).get("description", ""))
        self.var_amount = DoubleVar(value=float((initial or {}).get("amount") or 0.0))
        self.var_account = StringVar(value=(initial or {}).get("account", ""))

        self.result = None

    def _build_form(self) -> None:
        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Tipo
        ctk.CTkLabel(frm, text="Tipo").grid(row=0, column=0, sticky="w", pady=2)
        cb_type = ctk.CTkOptionMenu(
            frm,
            variable=self.var_type,
            values=["IN", "OUT"],
            width=120,
            command=lambda _: self._update_cats(),
        )
        cb_type.grid(row=0, column=1, sticky="ew", pady=2)

        # Data
        ctk.CTkLabel(frm, text="Data").grid(row=1, column=0, sticky="w", pady=2)
        if CTkDatePicker:
            de = CTkDatePicker(frm, date_format="%Y-%m-%d")
            de.set(self.var_date.get())
            de.grid(row=1, column=1, sticky="ew", pady=2)
            # Bind para atualizar StringVar ao alterar data
            def on_date_change(event=None):
                self.var_date.set(de.get())
            de.bind("<Return>", on_date_change)
            de.bind("<FocusOut>", on_date_change)
        else:
            ctk.CTkEntry(frm, textvariable=self.var_date).grid(row=1, column=1, sticky="ew", pady=2)

        # Categoria
        ctk.CTkLabel(frm, text="Categoria").grid(row=2, column=0, sticky="w", pady=2)
        self.cb_cat = ctk.CTkOptionMenu(
            frm,
            variable=self.var_category,
            values=self._cats(),
        )
        self.cb_cat.grid(row=2, column=1, sticky="ew", pady=2)

        # Descrição
        ctk.CTkLabel(frm, text="Descrição").grid(row=3, column=0, sticky="w", pady=2)
        ctk.CTkEntry(frm, textvariable=self.var_desc).grid(row=3, column=1, sticky="ew", pady=2)

        # Valor
        ctk.CTkLabel(frm, text="Valor").grid(row=4, column=0, sticky="w", pady=2)
        ctk.CTkEntry(frm, textvariable=self.var_amount).grid(row=4, column=1, sticky="ew", pady=2)

        # Conta
        ctk.CTkLabel(frm, text="Conta").grid(row=5, column=0, sticky="w", pady=2)
        ctk.CTkEntry(frm, textvariable=self.var_account).grid(row=5, column=1, sticky="ew", pady=2)

        # Botões
        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ctk.CTkButton(btns, text="Cancelar", command=self._cancel, width=80).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Salvar", command=self._ok, width=80).pack(side="right", padx=4)

        frm.columnconfigure(1, weight=1)

    def _finalize_modal(self) -> None:
        try:
            self.update_idletasks()
            show_centered(self)
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao exibir EntryDialog: %s", exc)

    def _cats(self):
        return CATEGORIES_IN if self.var_type.get() == "IN" else CATEGORIES_OUT

    def _update_cats(self):
        # Atualizar valores do CTkOptionMenu
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
            messagebox.showerror("Valor invǭlido", "Informe um nǧmero maior que zero.")
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
