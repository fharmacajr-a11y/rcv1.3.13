# -*- coding: utf-8 -*-
"""Main screen frame extracted from app_gui (clients list)."""

from __future__ import annotations

import logging
import re
import urllib.parse
import webbrowser
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox

import app_status
from app_utils import fmt_data
from core.search import search_clientes
from utils.text_utils import format_cnpj
from ui.components import (
    create_clients_treeview,
    create_footer_buttons,
    create_search_controls,
    create_status_bar,
)

log = logging.getLogger("app_gui")

DEFAULT_ORDER_LABEL = "Razao Social (A->Z)"
ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = {
    "Razao Social (A->Z)": ("razao_social", False),
    "CNPJ (A->Z)": ("cnpj", False),
    "Nome (A->Z)": ("nome", False),
    "Ultima Alteracao (mais recente)": ("ultima_alteracao", False),
    "Ultima Alteracao (mais antiga)": ("ultima_alteracao", True),
}

__all__ = ["MainScreenFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]


class MainScreenFrame(tb.Frame):
    """
    Frame da tela principal (lista de clientes + ações).
    Recebe callbacks do App para operações de negócio.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_new: Optional[Callable[[], None]] = None,
        on_edit: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_upload: Optional[Callable[[], None]] = None,
        on_open_subpastas: Optional[Callable[[], None]] = None,
        on_open_lixeira: Optional[Callable[[], None]] = None,
        app: Optional[Any] = None,
        order_choices: Optional[Dict[str, Tuple[Optional[str], bool]]] = None,
        default_order_label: str = DEFAULT_ORDER_LABEL,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self.app = app
        self.on_new = on_new
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_upload = on_upload
        self.on_open_subpastas = on_open_subpastas
        self.on_open_lixeira = on_open_lixeira

        self._order_choices = order_choices or ORDER_CHOICES
        self._default_order_label = default_order_label or DEFAULT_ORDER_LABEL
        self._buscar_after: Optional[str] = None

        search_controls = create_search_controls(
            self,
            order_choices=list(self._order_choices.keys()),
            default_order=self._default_order_label,
            on_search=self._buscar,
            on_clear=self._limpar_busca,
            on_order_change=self.carregar,
        )
        search_controls.frame.pack(fill="x", padx=10, pady=10)
        self.var_busca = search_controls.search_var
        self.var_ordem = search_controls.order_var

        self.client_list = create_clients_treeview(
            self,
            on_double_click=lambda _event: self._invoke(self.on_edit),
            on_select=self._update_main_buttons_state,
            on_delete=lambda _event: self._invoke(self.on_delete),
            on_click=self._on_click,
        )
        self.client_list.pack(expand=True, fill="both", padx=10, pady=5)
        try:
            self.client_list.heading(
                "Razao Social", command=lambda: self._sort_by("razao_social")
            )
            self.client_list.heading("CNPJ", command=lambda: self._sort_by("cnpj"))
            self.client_list.heading("Nome", command=lambda: self._sort_by("nome"))
            self.client_list.heading(
                "Ultima Alteracao", command=lambda: self._sort_by("updated_at")
            )
        except Exception:
            pass

        footer = create_footer_buttons(
            self,
            on_novo=lambda: self._invoke(self.on_new),
            on_editar=lambda: self._invoke(self.on_edit),
            on_subpastas=lambda: self._invoke(self.on_open_subpastas),
            on_enviar=lambda: self._invoke(self.on_upload),
            on_lixeira=lambda: self._invoke(self.on_open_lixeira),
        )
        footer.frame.pack(fill="x", padx=10, pady=10)
        self.btn_novo = footer.novo
        self.btn_editar = footer.editar
        self.btn_subpastas = footer.subpastas
        self.btn_enviar = footer.enviar
        self.btn_lixeira = footer.lixeira

        status = create_status_bar(
            self,
            count_var=getattr(self.app, "clients_count_var", None),
            status_dot_var=getattr(self.app, "status_var_dot", None),
            status_text_var=getattr(self.app, "status_var_text", None),
            default_status_text=getattr(app_status, "status_text", "LOCAL"),
        )
        status.frame.pack(fill="x", padx=10, pady=5)
        self.clients_count_var = status.count_var
        self.status_var_dot = status.status_dot_var
        self.status_var_text = status.status_text_var
        self.status_dot = status.status_dot
        self.status_lbl = status.status_label

        if self.app is not None:
            self.app.clients_count_var = self.clients_count_var
            self.app.status_var_dot = self.status_var_dot
            self.app.status_var_text = self.status_var_text
            self.app.status_dot = self.status_dot
            self.app.status_lbl = self.status_lbl
            setattr(self.app, "_main_frame_ref", self)

        self._update_main_buttons_state()

    def carregar(self) -> None:
        """Preenche a tabela de clientes."""
        order_label = self.var_ordem.get()
        search_term = self.var_busca.get().strip()
        column, reverse_after = self._resolve_order_preferences()
        log.info("Atualizando lista (busca='%s', ordem='%s')", search_term, order_label)
        try:
            clientes = search_clientes(search_term, column)
            if reverse_after:
                clientes = list(reversed(clientes))
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao carregar lista: {exc}", parent=self)
            return

        try:
            self.client_list.delete(*self.client_list.get_children())
        except Exception:
            pass

        def _get(obj: Any, key: str, *alts: str) -> Any:
            keys = (key,) + alts
            for k in keys:
                if isinstance(obj, dict):
                    if k in obj:
                        return obj.get(k)
                elif hasattr(obj, k):
                    return getattr(obj, k)
            return None

        def _format_cnpj_safe(valor: str) -> str:
            raw = (valor or "").strip()
            try:
                out = format_cnpj(raw)
                if out:
                    return out
            except Exception:
                pass
            digits = "".join(ch for ch in raw if ch.isdigit())
            if len(digits) > 14:
                digits = digits[-14:]
            if len(digits) != 14:
                return raw
            return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"

        def _format_whats_display(num: str) -> str:
            raw = str(num or "")
            digits = re.sub(r"\D+", "", raw)
            if not digits:
                return ""
            natl = digits[2:] if digits.startswith("55") else digits
            if len(natl) < 10:
                return f"+55 {natl}"
            ddd, local = natl[:2], natl[2:]
            if len(local) >= 9:
                return f"{ddd} {local[:5]}-{local[5:9]}"
            return f"{ddd} {local[:4]}-{local[4:8]}"

        for cli in clientes:
            cnpj_fmt = _format_cnpj_safe(str(_get(cli, "cnpj") or ""))
            numero_raw = str(_get(cli, "numero", "whatsapp", "telefone") or "")
            numero_disp = _format_whats_display(numero_raw)
            obs_txt = (_get(cli, "observacoes", "obs") or "").strip()

            values = (
                _get(cli, "id", "pk", "client_id"),
                _get(cli, "razao_social", "razao"),
                cnpj_fmt,
                _get(cli, "nome"),
                numero_disp,
                obs_txt,
                fmt_data(_get(cli, "updated_at", "ultima_alteracao")),
            )
            tags = ("has_obs",) if obs_txt else ()
            self.client_list.insert("", "end", values=values, tags=tags)

        count = (
            len(clientes)
            if isinstance(clientes, (list, tuple))
            else len(self.client_list.get_children())
        )
        self._set_count_text(count)
        self._update_main_buttons_state()

    def _sort_by(self, column: str) -> None:
        current = self.var_ordem.get()
        if column == "updated_at":
            new_value = (
                "Ultima Alteracao (mais antiga)"
                if current == "Ultima Alteracao (mais recente)"
                else "Ultima Alteracao (mais recente)"
            )
            self.var_ordem.set(new_value)
        elif column in ("razao_social", "cnpj", "nome"):
            mapping = {
                "razao_social": "Razao Social (A->Z)",
                "cnpj": "CNPJ (A->Z)",
                "nome": "Nome (A->Z)",
            }
            self.var_ordem.set(mapping[column])
        else:
            return
        self.carregar()

    def _get_selected_values(self) -> Optional[Sequence[Any]]:
        try:
            selection = self.client_list.selection()
        except Exception:
            return None
        if not selection:
            return None
        item_id = selection[0]
        try:
            return self.client_list.item(item_id, "values")
        except Exception:
            return None

    def _buscar(self, _event: Any | None = None) -> None:
        try:
            if self._buscar_after:
                self.after_cancel(self._buscar_after)
        except Exception:
            pass
        self._buscar_after = self.after(200, self.carregar)

    def _limpar_busca(self) -> None:
        self.var_busca.set("")
        self.carregar()

    def _on_click(self, event: Any) -> None:
        item = self.client_list.identify_row(event.y)
        col = self.client_list.identify_column(event.x)
        if not item or col != "#5":
            return
        try:
            cell = self.client_list.item(item, "values")[4] or ""
        except Exception:
            cell = ""
        digits = re.sub(r"\D+", "", str(cell))
        if not digits:
            return
        phone = digits if digits.startswith("55") else f"55{digits}"
        msg = "Olá, tudo bem?"
        webbrowser.open_new_tab(
            f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg)}"
        )

    def _update_main_buttons_state(self, *_: Any) -> None:
        try:
            has_sel = bool(self.client_list.selection())
        except Exception:
            has_sel = False
        online = (
            bool(getattr(self.app, "_net_is_online", True))
            if self.app is not None
            else True
        )
        try:
            self.btn_editar.configure(
                state=("normal" if (has_sel and online) else "disabled")
            )
            self.btn_subpastas.configure(
                state=("normal" if (has_sel and online) else "disabled")
            )
            self.btn_enviar.configure(
                state=("normal" if (has_sel and online) else "disabled")
            )
            self.btn_novo.configure(state=("normal" if online else "disabled"))
            self.btn_lixeira.configure(state=("normal" if online else "disabled"))
        except Exception:
            pass

    def _resolve_order_preferences(self) -> Tuple[Optional[str], bool]:
        label = self.var_ordem.get()
        return self._order_choices.get(label, (None, False))

    def _set_count_text(self, count: int) -> None:
        try:
            text = "1 cliente" if count == 1 else f"{count} clientes"
            self.clients_count_var.set(text)
        except Exception:
            pass

    @staticmethod
    def _invoke(callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            callback()
