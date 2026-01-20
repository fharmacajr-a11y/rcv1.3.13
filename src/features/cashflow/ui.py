"""Fluxo de Caixa - UI (MICROFASE 27: 100% CustomTkinter)"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from tkinter import StringVar, messagebox
from typing import Optional

from src.ui.ctk_config import ctk
from src.ui.widgets import CTkTableView
from src.ui.window_utils import show_centered

from . import repository as repo

logger = logging.getLogger(__name__)


def _first_day_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_month(d: date) -> date:
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


class CashflowWindow(ctk.CTkToplevel):
    """Janela principal do Fluxo de Caixa (CustomTkinter)."""

    TYPE_LABEL_TO_CODE = {"Entrada": "IN", "Saída": "OUT"}
    TYPE_CODE_TO_LABEL = {"IN": "Entrada", "OUT": "Saída"}

    def __init__(self, master):
        super().__init__(master)
        self.withdraw()

        self._init_base_window(master)
        self._build_filters_row()
        self._build_tree()
        self._build_totals_label()
        self._finalize_window(master)

    def _init_base_window(self, master) -> None:
        # Evita flicker: cria oculta, monta widgets, centraliza e so entao mostra
        self.title("Fluxo de Caixa")
        self.minsize(820, 480)

        try:
            self._org_id = master._get_org_id_safe() if hasattr(master, "_get_org_id_safe") else None
        except Exception:
            self._org_id = None

        today = date.today()
        self.var_from = StringVar(value=str(_first_day_month(today)))
        self.var_to = StringVar(value=str(_last_day_month(today)))
        self.var_type = StringVar(value="Todos")
        self.var_text = StringVar(value="")
        self._row_ids: list[str] = []  # Guardar IDs das linhas

    def _build_filters_row(self) -> None:
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=8, pady=8)

        # Linha de filtros
        ctk.CTkLabel(top, text="De").pack(side="left", padx=(0, 4))
        e1 = ctk.CTkEntry(top, textvariable=self.var_from, width=120)
        e1.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Até").pack(side="left", padx=(8, 4))
        e2 = ctk.CTkEntry(top, textvariable=self.var_to, width=120)
        e2.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Tipo").pack(side="left", padx=(8, 4))
        self.cbo_tipo = ctk.CTkOptionMenu(
            top,
            variable=self.var_type,
            values=["Todos", "Entrada", "Saída"],
            width=100,
        )
        self.cbo_tipo.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Busca").pack(side="left", padx=(8, 4))
        ctk.CTkEntry(top, textvariable=self.var_text, width=200).pack(side="left", padx=4)

        ctk.CTkButton(top, text="Filtrar", command=self.refresh, width=80).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Novo", command=self.create, width=70).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Editar", command=self.edit, width=70).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Excluir", command=self.delete, width=70).pack(side="right", padx=4)

    def _build_tree(self) -> None:
        # Usar CTkTableView ao invés de Treeview
        self.tree = CTkTableView(
            self,
            columns=["date", "type", "category", "description", "amount", "account"],
            show="headings",
            height=18,
        )
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

        # Definir headers
        headers = ["DATA", "TIPO", "CATEGORIA", "DESCRIÇÃO", "VALOR", "CONTA"]
        self.tree.set_columns(headers)

    def _build_totals_label(self) -> None:
        self.lbl_totals = ctk.CTkLabel(
            self,
            text="Receitas: 0.00 | Despesas: 0.00 | Saldo: 0.00",
        )
        self.lbl_totals.pack(fill="x", padx=8, pady=8)

    def _finalize_window(self, master) -> None:
        self.update_idletasks()
        show_centered(self)

        if hasattr(master, "_cashflow_window") and master._cashflow_window is self:
            self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.refresh()

    def _parse_date_range(self):
        try:
            dfrom = date.fromisoformat(self.var_from.get())
            dto = date.fromisoformat(self.var_to.get())
            return dfrom, dto
        except Exception:
            messagebox.showerror("Datas inv?lidas", "Use o formato YYYY-MM-DD", parent=self)
            return None

    def _get_type_filter(self) -> Optional[str]:
        tfilter = None
        tsel = self.var_type.get()
        if tsel == "Entrada":
            tfilter = "IN"
        elif tsel == "Sa??da":
            tfilter = "OUT"
        return tfilter

    def _fetch_rows(self, dfrom: date, dto: date, tfilter: Optional[str]) -> list[dict]:
        try:
            return repo.list_entries(dfrom, dto, tfilter, self.var_text.get().strip(), org_id=self._org_id)
        except Exception as e:
            messagebox.showwarning(
                "Fluxo de Caixa",
                f"{e}\n\nDica: verifique RLS e se 'org_id' está presente.",
                parent=self,
            )
            return []

    def _reload_tree(self, rows: list[dict]) -> None:
        if not self._guard_widgets():
            return
        
        # Limpar tabela
        self.tree.clear()
        
        # Adicionar linhas
        table_rows = []
        for r in rows:
            tipo_raw = r.get("type")
            if tipo_raw is None:
                tipo_raw = ""  # fallback para tipo ausente
            tipo_label = self.TYPE_CODE_TO_LABEL.get(tipo_raw, tipo_raw)
            
            row_data = [
                r.get("date") or "",
                tipo_label,
                r.get("category") or "",
                r.get("description", ""),
                f"{self._to_float(r.get('amount')):.2f}",
                r.get("account", ""),
            ]
            table_rows.append(row_data)
            
            # Guardar ID na linha para uso em edit/delete
            # (CTkTableView não tem conceito de IID, usar índice)
        
        self.tree.set_rows(table_rows)
        self._row_ids = [r.get("id") or "" for r in rows]  # Guardar IDs separadamente

    def _update_totals(self, dfrom: date, dto: date) -> None:
        tot = repo.totals(dfrom, dto, org_id=self._org_id)
        inc = self._to_float(tot.get("in"))
        out = self._to_float(tot.get("out"))
        net = self._to_float(tot.get("balance")) if tot.get("balance") is not None else inc - out

        if self._guard_widgets():
            self.lbl_totals.configure(text=f"Receitas: {inc:.2f} | Despesas: {out:.2f} | Saldo: {net:.2f}")

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
        date_range = self._parse_date_range()
        if date_range is None:
            return
        dfrom, dto = date_range

        tfilter = self._get_type_filter()
        rows = self._fetch_rows(dfrom, dto, tfilter)

        self._reload_tree(rows)
        self._update_totals(dfrom, dto)

    def _selected_id(self) -> Optional[str]:
        idx = self.tree.get_selected_row_index()
        if idx is not None and 0 <= idx < len(self._row_ids):
            return self._row_ids[idx]
        return None

    def create(self) -> None:
        from .dialogs import EntryDialog

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

        # Pegar dados da linha selecionada
        item = self.tree.get_selected_row()
        if not item:
            return
        
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
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao focar janela do fluxo de caixa existente: %s", exc)

    win = CashflowWindow(master)
    setattr(master, "_cashflow_window", win)
    win.protocol("WM_DELETE_WINDOW", win._on_close)
