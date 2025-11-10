"""Fluxo de Caixa - UI"""

from __future__ import annotations

import tkinter as tk
from tkinter import Toplevel, StringVar, ttk, messagebox
from datetime import date, timedelta
from typing import Optional

from . import repository as repo


# ------------ utilidades de centralização (sem "flash") ------------
def _place_center(win: tk.Toplevel) -> bool:
    """
    Tenta usar o helper nativo do Tk para centralizar.
    Retorna True se conseguiu.
    """
    try:
        # equivalente a: win.eval('tk::PlaceWindow <pathname> center')
        win.tk.call("tk::PlaceWindow", win._w, "center")
        return True
    except Exception:
        return False


def center_on_screen(win: tk.Toplevel) -> None:
    """Centraliza a janela calculando geometria manualmente (fallback)."""
    win.update_idletasks()
    w = win.winfo_width() or win.winfo_reqwidth()
    h = win.winfo_height() or win.winfo_reqheight()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


def _first_day_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_month(d: date) -> date:
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


class CashflowWindow(Toplevel):
    """Janela principal do Fluxo de Caixa."""

    TYPE_LABEL_TO_CODE = {"Entrada": "IN", "Saída": "OUT"}
    TYPE_CODE_TO_LABEL = {"IN": "Entrada", "OUT": "Saída"}

    def __init__(self, master):
        super().__init__(master)

        # Evita flicker: cria oculta, monta widgets, centraliza e só então mostra
        self.withdraw()

        self.title("Fluxo de Caixa")
        self.minsize(820, 480)

        # --- estado/variáveis ---
        try:
            self._org_id = (
                master._get_org_id_safe() if hasattr(master, "_get_org_id_safe") else None
            )
        except Exception:
            self._org_id = None

        today = date.today()
        self.var_from = StringVar(value=str(_first_day_month(today)))
        self.var_to = StringVar(value=str(_last_day_month(today)))
        self.var_type = StringVar(value="Todos")
        self.var_text = StringVar(value="")

        # --- topo (filtros) ---
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="De").pack(side="left")
        e1 = ttk.Entry(top, textvariable=self.var_from, width=12)
        e1.pack(side="left", padx=4)

        ttk.Label(top, text="Até").pack(side="left")
        e2 = ttk.Entry(top, textvariable=self.var_to, width=12)
        e2.pack(side="left", padx=4)

        ttk.Label(top, text="Tipo").pack(side="left")
        self.cbo_tipo = ttk.Combobox(
            top,
            textvariable=self.var_type,
            values=["Todos", "Entrada", "Saída"],
            width=10,
            state="readonly",
        )
        self.cbo_tipo.pack(side="left", padx=4)

        ttk.Label(top, text="Busca").pack(side="left")
        ttk.Entry(top, textvariable=self.var_text, width=22).pack(side="left", padx=4)

        ttk.Button(top, text="Filtrar", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(top, text="Novo", command=self.create).pack(side="right", padx=4)
        ttk.Button(top, text="Editar", command=self.edit).pack(side="right", padx=4)
        ttk.Button(top, text="Excluir", command=self.delete).pack(side="right", padx=4)

        # --- grade ---
        self.tree = ttk.Treeview(
            self,
            columns=("date", "type", "category", "description", "amount", "account"),
            show="headings",
            height=18,
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
            "type": 90,
            "category": 150,
            "description": 360,
            "amount": 120,
            "account": 120,
        }
        for col in ("date", "type", "category", "description", "amount", "account"):
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor=tk.CENTER)
            self.tree.heading(col, anchor=tk.CENTER)
        # (Se quiser a descrição à esquerda, troque anchor=tk.W nas 2 linhas acima para "description")

        # --- totais ---
        self.lbl_totals = ttk.Label(
            self, text="Receitas: 0.00 | Despesas: 0.00 | Saldo: 0.00", padding=8
        )
        self.lbl_totals.pack(fill="x")

        # --- mostrar centralizada ---
        if not _place_center(self):
            center_on_screen(self)
        self.deiconify()
        self.lift()
        self.focus_force()

        # --- protocolo de fechamento ---
        if hasattr(master, "_cashflow_window") and master._cashflow_window is self:
            self.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- primeira carga ---
        self.refresh()

    # -------- util --------
    def _on_close(self) -> None:
        try:
            m = self.master
            if hasattr(m, "_cashflow_window"):
                m._cashflow_window = None
        finally:
            self.destroy()

    def _guard_widgets(self) -> bool:
        """Evita TclError se janela/árvore foram destruídas."""
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
            # se já for código, mantém; senão mapeia rótulo -> código
            if t in self.TYPE_LABEL_TO_CODE:
                payload["type"] = self.TYPE_LABEL_TO_CODE[t]
        return payload

    # -------- ações --------
    def refresh(self) -> None:
        if not self._guard_widgets():
            return
        # datas
        try:
            dfrom = date.fromisoformat(self.var_from.get())
            dto = date.fromisoformat(self.var_to.get())
        except Exception:
            messagebox.showerror("Datas inválidas", "Use o formato YYYY-MM-DD", parent=self)
            return

        # filtro de tipo
        tfilter = None
        tsel = self.var_type.get()
        if tsel == "Entrada":
            tfilter = "IN"
        elif tsel == "Saída":
            tfilter = "OUT"

        # busca
        try:
            rows = repo.list_entries(
                dfrom, dto, tfilter, self.var_text.get().strip(), org_id=self._org_id
            )
        except Exception as e:
            messagebox.showwarning(
                "Fluxo de Caixa",
                f"{e}\n\nDica: verifique RLS e se 'org_id' está presente.",
                parent=self,
            )
            rows = []

        if not self._guard_widgets():
            return

        # rerender tabela
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for r in rows:
            tipo_label = self.TYPE_CODE_TO_LABEL.get(r.get("type"), r.get("type"))
            values = (
                r.get("date"),
                tipo_label,
                r.get("category"),
                r.get("description", ""),
                f"{self._to_float(r.get('amount')):.2f}",
                r.get("account", ""),
            )
            self.tree.insert("", "end", iid=r.get("id") or "", values=values)

        # totais
        tot = repo.totals(dfrom, dto, org_id=self._org_id)
        inc = self._to_float(tot.get("in"))
        out = self._to_float(tot.get("out"))
        net = self._to_float(tot.get("balance")) if tot.get("balance") is not None else inc - out

        if self._guard_widgets():
            self.lbl_totals.configure(
                text=f"Receitas: {inc:.2f} | Despesas: {out:.2f} | Saldo: {net:.2f}"
            )

    def _selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def create(self) -> None:
        from .dialogs import EntryDialog

        dlg = EntryDialog(self, title="Novo Lançamento")
        center_on_screen(dlg)  # centraliza o diálogo
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

        # coleta dados atuais a partir da linha da grid
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

        from .dialogs import EntryDialog

        dlg = EntryDialog(self, initial=current, title="Editar Lançamento")
        center_on_screen(dlg)
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


def open_cashflow_window(master) -> None:
    """Abre (ou traz à frente) a janela do Fluxo de Caixa evitando múltiplas instâncias."""
    win = getattr(master, "_cashflow_window", None)
    if win and getattr(win, "winfo_exists", lambda: False)():
        try:
            win.deiconify()
            win.lift()
            win.focus_force()
            return
        except Exception:
            pass

    win = CashflowWindow(master)
    setattr(master, "_cashflow_window", win)
    win.protocol("WM_DELETE_WINDOW", win._on_close)
