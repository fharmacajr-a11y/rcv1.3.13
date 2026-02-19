from __future__ import annotations

import logging
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox
from typing import Any, Optional

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn
from src.ui.widgets import CTkTableView

from src.features.cashflow import repository as repo

logger = logging.getLogger(__name__)


def _first_day_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_month(d: date) -> date:
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


class CashflowFrame(ctk.CTkFrame):
    """Tela principal do Fluxo de Caixa integrada à área central da App."""

    TYPE_LABEL_TO_CODE = {"Entrada": "IN", "Saída": "OUT"}
    TYPE_CODE_TO_LABEL = {"IN": "Entrada", "OUT": "Saída"}

    def __init__(self, master: tk.Widget, app: Any | None = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.app = app

        self._org_id: Optional[str] = None
        self._resolve_org_id()

        today = date.today()
        self.var_from = tk.StringVar(value=str(_first_day_month(today)))
        self.var_to = tk.StringVar(value=str(_last_day_month(today)))
        self.var_type = tk.StringVar(value="Todos")
        self.var_text = tk.StringVar(value="")

        # --- topo (filtros) ---
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(top, text="De").pack(side="left", padx=4)
        e1 = ctk.CTkEntry(top, textvariable=self.var_from, width=100)
        e1.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Até").pack(side="left", padx=4)
        e2 = ctk.CTkEntry(top, textvariable=self.var_to, width=100)
        e2.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Tipo").pack(side="left", padx=4)
        self.cbo_tipo = ctk.CTkComboBox(
            top,
            variable=self.var_type,
            values=["Todos", "Entrada", "Saída"],
            width=100,
            state="readonly",
        )
        self.cbo_tipo.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Busca").pack(side="left", padx=4)
        ctk.CTkEntry(top, textvariable=self.var_text, width=180).pack(side="left", padx=4)

        make_btn(top, text="Filtrar", command=self.refresh).pack(side="left", padx=6)
        make_btn(top, text="Novo", command=self.create).pack(side="right", padx=4)
        make_btn(top, text="Editar", command=self.edit).pack(side="right", padx=4)
        make_btn(top, text="Excluir", command=self.delete).pack(side="right", padx=4)

        # --- grade ---
        self.tree = CTkTableView(
            self,
            columns=("date", "type", "category", "description", "amount", "account"),
            show="headings",
            height=18,
            zebra=True,
        )

        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

        headers = {
            "date": "DATA",
            "type": "TIPO",
            "category": "CATEGORIA",
            "description": "DESCRIÇÃO",
            "amount": "VALOR",
            "account": "CONTA",
        }
        widths = {
            "date": 100,
            "type": 80,
            "category": 160,
            "description": 260,
            "amount": 120,
            "account": 180,
        }

        for col, text in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=widths.get(col, 100), anchor="w")
        self.tree.column("amount", anchor="e")

        # --- rodapé totais ---
        self.lbl_totals = ctk.CTkLabel(self, text="Receitas: 0.00 | Despesas: 0.00 | Saldo: 0.00", anchor="w")
        self.lbl_totals.pack(fill="x", padx=8, pady=(0, 6))

        # --- primeira carga ---
        self.refresh()

    # -------- util --------
    def _resolve_org_id(self) -> None:
        if self._org_id:
            return
        try:
            if self.app and hasattr(self.app, "_get_user_cached"):
                user = self.app._get_user_cached()
                if user and "id" in user:
                    org = getattr(self.app, "_get_org_id_cached", lambda uid: None)(user["id"])
                    if org:
                        self._org_id = org
                        return
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao resolver org_id a partir do app em CashflowFrame: %s", exc)
        try:
            master = self.master
            if hasattr(master, "_get_org_id_safe"):
                self._org_id = master._get_org_id_safe()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao resolver org_id via master em CashflowFrame: %s", exc)

    def _guard_widgets(self) -> bool:
        """Evita TclError se árvore/labels foram destruídas."""
        try:
            return self.winfo_exists() and self.tree and self.tree.winfo_exists()
        except Exception:
            return False

    @staticmethod
    def _to_float(x) -> float:
        try:
            return float(x) if x is not None else 0.0
        except Exception:
            return 0.0

    def _normalize_type_in_payload(self, payload: dict) -> dict:
        """Garante que payload['type'] seja 'IN'/'OUT' mesmo se vier 'Entrada'/'Saída'."""
        if not isinstance(payload, dict):
            return payload
        t = payload.get("type")
        if isinstance(t, str):
            if t in self.TYPE_LABEL_TO_CODE:
                payload["type"] = self.TYPE_LABEL_TO_CODE[t]
        return payload

    # -------- ações --------
    def carregar(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if not self._guard_widgets():
            return
        self._resolve_org_id()
        dfrom = self.var_from.get().strip()
        dto = self.var_to.get().strip()
        tfilter = self.var_type.get()
        if tfilter in self.TYPE_LABEL_TO_CODE:
            tfilter = self.TYPE_LABEL_TO_CODE[tfilter]

        try:
            rows = repo.list_entries(dfrom, dto, tfilter, self.var_text.get().strip(), org_id=self._org_id)
        except Exception as e:
            messagebox.showwarning(
                "Fluxo de Caixa",
                f"{e}\n\nDica: verifique RLS e se 'org_id' está presente.",
                parent=self,
            )
            rows = []

        if not self._guard_widgets():
            return

        self.tree.clear()

        for r in rows:
            tipo_raw = r.get("type") or ""
            tipo_label = self.TYPE_CODE_TO_LABEL.get(tipo_raw, tipo_raw)
            values = [
                r.get("date"),
                tipo_label,
                r.get("category"),
                r.get("description", ""),
                f"{self._to_float(r.get('amount')):.2f}",
                r.get("account", ""),
            ]
            self.tree.insert("", "end", iid=r.get("id") or "", values=values)

        tot = repo.totals(dfrom, dto, org_id=self._org_id)
        inc = self._to_float(tot.get("in"))
        out = self._to_float(tot.get("out"))
        net = self._to_float(tot.get("balance")) if tot.get("balance") is not None else inc - out

        if self._guard_widgets():
            self.lbl_totals.configure(text=f"Receitas: {inc:.2f} | Despesas: {out:.2f} | Saldo: {net:.2f}")

    def _selected_id(self) -> Optional[str]:
        return self.tree.get_selected_iid()

    def create(self) -> None:
        from src.features.cashflow.dialogs import EntryDialog

        dlg = EntryDialog(self, title="Novo Lançamento")
        self.wait_window(dlg)

        if dlg.result:
            try:
                payload = self._normalize_type_in_payload(dict(dlg.result))
                repo.create_entry(payload, org_id=self._org_id)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Fluxo de Caixa", str(e), parent=self)

    def edit(self) -> None:
        iid = self._selected_id()
        if not iid:
            messagebox.showinfo("Selecione", "Escolha um lançamento para editar.", parent=self)
            return

        item = self.tree.item(iid)["values"]
        current = {
            "id": iid,
            "date": item[0],
            "type": self.TYPE_LABEL_TO_CODE.get(item[1], item[1]),  # garante IN/OUT
            "category": item[2],
            "description": item[3],
            "amount": self._to_float(item[4]),
            "account": item[5],
        }

        from src.features.cashflow.dialogs import EntryDialog

        dlg = EntryDialog(self, initial=current, title="Editar Lançamento")
        self.wait_window(dlg)

        if dlg.result:
            try:
                payload = self._normalize_type_in_payload(dict(dlg.result))
                repo.update_entry(iid, payload)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Fluxo de Caixa", str(e), parent=self)

    def delete(self) -> None:
        iid = self._selected_id()
        if not iid:
            messagebox.showinfo("Selecione", "Escolha um lançamento para excluir.", parent=self)
            return
        if messagebox.askyesno("Confirma", "Excluir este lançamento?", parent=self):
            try:
                repo.delete_entry(iid)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Fluxo de Caixa", str(e), parent=self)
