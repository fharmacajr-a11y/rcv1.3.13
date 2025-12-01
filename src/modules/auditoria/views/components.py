"""Reusable UI components for the Auditoria module."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable, Literal, Optional

logger = logging.getLogger(__name__)


class AuditoriaToolbar(ttk.Frame):
    """Toolbar with search, client selector and quick actions."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        ui_gap: int = 6,
        ui_padx: int = 8,
        ui_pady: int = 6,
        search_var: tk.StringVar | None = None,
        cliente_var: tk.StringVar | None = None,
        on_search_change: Optional[Callable[[str], None]] = None,
        on_clear_filter: Optional[Callable[[], None]] = None,
        on_cliente_selected: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, padding=(ui_padx, ui_pady, ui_padx, ui_pady))
        for col in range(0, 8):
            self.columnconfigure(col, weight=0)
        self.columnconfigure(4, weight=1)
        self.columnconfigure(7, weight=1)

        self.search_var = search_var or tk.StringVar()
        ttk.Label(self, text="Buscar cliente:").grid(row=0, column=0, sticky="w", padx=(0, ui_gap))
        self.entry_busca = ttk.Entry(self, textvariable=self.search_var, width=32)
        self.entry_busca.grid(row=0, column=1, sticky="w", padx=(0, ui_gap))
        self.ent_busca = self.entry_busca

        self._search_after_id: str | None = None

        def _on_busca_key(event=None):  # type: ignore[no-untyped-def]
            if self._search_after_id:
                try:
                    self.after_cancel(self._search_after_id)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao cancelar debounce da busca em AuditoriaToolbar: %s", exc)

            def _dispatch() -> None:
                if on_search_change:
                    on_search_change(self.ent_busca.get())

            self._search_after_id = self.after(140, _dispatch)

        self.entry_busca.bind("<KeyRelease>", _on_busca_key)

        self.btn_limpar = ttk.Button(self, text="Limpar", command=lambda: on_clear_filter and on_clear_filter())
        self.btn_limpar.grid(row=0, column=2, padx=(0, ui_gap))

        self.cliente_var = cliente_var or tk.StringVar()
        ttk.Label(self, text="Cliente para auditoria:").grid(row=0, column=3, sticky="e", padx=(ui_gap, ui_gap))
        self.combo_cliente = ttk.Combobox(self, textvariable=self.cliente_var, state="readonly", width=64)
        self.combo_cliente.grid(row=0, column=4, sticky="ew")
        self.cmb_cliente = self.combo_cliente

        ttk.Label(self, text="").grid(row=0, column=7, sticky="ew")

        def _on_select(event=None):  # type: ignore[no-untyped-def]
            if on_cliente_selected:
                on_cliente_selected()

        self.combo_cliente.bind("<<ComboboxSelected>>", _on_select)


class AuditoriaListPanel(ttk.Labelframe):
    """List panel containing the treeview and action buttons."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        ui_gap: int = 6,
        ui_padx: int = 8,
        ui_pady: int = 6,
        on_tree_select: Optional[Callable[[tk.Event], None]] = None,
        on_open_status_menu: Optional[Callable[[tk.Event], Literal["break"] | None]] = None,
        on_start_auditoria: Optional[Callable[[], None]] = None,
        on_view_subpastas: Optional[Callable[[], None]] = None,
        on_upload_files: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, text="Auditorias recentes", padding=(6, 4, 6, 6))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.tree_container = ttk.Frame(self)
        self.tree_container.grid(row=0, column=0, sticky="nsew")
        self.tree_container.columnconfigure(0, weight=1)
        self.tree_container.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self.tree_container,
            columns=("cliente", "status", "criado", "atualizado"),
            show="headings",
            selectmode="extended",
            height=16,
        )
        for cid, title in (
            ("cliente", "Cliente"),
            ("status", "Status"),
            ("criado", "Criado em"),
            ("atualizado", "Atualizado em"),
        ):
            self.tree.heading(cid, text=title, anchor="center")
            self.tree.column(cid, anchor="center", stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")

        if on_tree_select:
            self.tree.bind("<<TreeviewSelect>>", on_tree_select)
        if on_open_status_menu:
            self.tree.bind("<Button-3>", on_open_status_menu)

        scrollbar = ttk.Scrollbar(self.tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.lbl_notfound = ttk.Label(self, text="", foreground="#a33")
        self.lbl_notfound.grid(row=1, column=0, sticky="w", pady=(ui_gap, 0))

        self.actions_frame = ttk.Frame(self, padding=(ui_padx, ui_pady, ui_padx, ui_pady))
        self.actions_frame.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)

        self.actions_frame.columnconfigure(0, weight=1)
        for col in (1, 2, 3, 4):
            self.actions_frame.columnconfigure(col, weight=0)

        def _wrap(cb: Optional[Callable[[], None]]) -> Callable[[], None]:
            return (lambda: cb()) if cb else (lambda: None)

        self.btn_iniciar = ttk.Button(self.actions_frame, text="Iniciar auditoria", command=_wrap(on_start_auditoria))
        self.btn_subpastas = ttk.Button(
            self.actions_frame,
            text="Ver subpastas",
            command=_wrap(on_view_subpastas),
            state="disabled",
        )
        self.btn_enviar = ttk.Button(
            self.actions_frame,
            text="Enviar arquivos para Auditoria",
            command=_wrap(on_upload_files),
        )
        self.btn_excluir = ttk.Button(
            self.actions_frame,
            text="Excluir auditoria(s)",
            command=_wrap(on_delete),
            state="disabled",
        )

        ttk.Label(self.actions_frame, text="").grid(row=0, column=0, sticky="ew")
        self.btn_iniciar.grid(row=0, column=1, padx=(0, ui_gap), sticky="e")
        self.btn_subpastas.grid(row=0, column=2, padx=(0, ui_gap), sticky="e")
        self.btn_enviar.grid(row=0, column=3, padx=(0, ui_gap), sticky="e")
        self.btn_excluir.grid(row=0, column=4, padx=(0, 0), sticky="e")
