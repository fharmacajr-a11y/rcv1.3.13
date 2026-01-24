"""Reusable UI components for the Auditoria module."""

from __future__ import annotations

import logging
import tkinter as tk

from typing import Callable, Literal, Optional

from src.ui.ctk_config import ctk
from src.ui.widgets import CTkTableView

logger = logging.getLogger(__name__)


class AuditoriaToolbar(ctk.CTkFrame):
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
        super().__init__(master)  # CTkFrame não aceita padding args posicionais
        for col in range(0, 8):
            self.columnconfigure(col, weight=0)
        self.columnconfigure(4, weight=1)
        self.columnconfigure(7, weight=1)

        self.search_var = search_var or tk.StringVar()
        ctk.CTkLabel(self, text="Buscar cliente:").grid(row=0, column=0, sticky="w", padx=(0, ui_gap))
        self.entry_busca = ctk.CTkEntry(self, textvariable=self.search_var, width=32)
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

        self.btn_limpar = ctk.CTkButton(self, text="Limpar", command=lambda: on_clear_filter and on_clear_filter())
        self.btn_limpar.grid(row=0, column=2, padx=(0, ui_gap))

        self.cliente_var = cliente_var or tk.StringVar()
        ctk.CTkLabel(self, text="Cliente para auditoria:").grid(row=0, column=3, sticky="e", padx=(ui_gap, ui_gap))
        self.combo_cliente = ctk.CTkComboBox(self, state="readonly", width=64)
        self.combo_cliente.grid(row=0, column=4, sticky="ew")
        self.cmb_cliente = self.combo_cliente

        ctk.CTkLabel(self, text="").grid(row=0, column=7, sticky="ew")

        def _on_select(event=None):  # type: ignore[no-untyped-def]
            if on_cliente_selected:
                on_cliente_selected()

        self.combo_cliente.bind("<<ComboboxSelected>>", _on_select)


class AuditoriaListPanel(ctk.CTkFrame):
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
        super().__init__(master)  # CTkFrame não suporta text/padding

        # Header manual (CTkFrame não suporta text)
        self.header = ctk.CTkLabel(self, text="Auditorias recentes", font=("Arial", 12, "bold"), anchor="w")
        self.header.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 2))

        # Body container
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Configurar weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(0, weight=1)
        self.body.rowconfigure(1, weight=0)

        self.tree_container = ctk.CTkFrame(self.body)
        self.tree_container.grid(row=0, column=0, sticky="nsew")
        self.tree_container.columnconfigure(0, weight=1)
        self.tree_container.rowconfigure(0, weight=1)

        self.tree = CTkTableView(
            self.tree_container,
            columns=("cliente", "status", "criado", "atualizado"),
            show="headings",
            # selectmode="extended" handled internally
            height=16,
            zebra=True,
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

        self.lbl_notfound = ctk.CTkLabel(self.body, text="", text_color="#a33")
        self.lbl_notfound.grid(row=1, column=0, sticky="w", pady=(ui_gap, 0))

        self.actions_frame = ctk.CTkFrame(self.body)
        self.actions_frame.grid(row=2, column=0, sticky="ew", pady=ui_pady)

        # Ajustar rowconfigure do body para incluir a nova linha
        self.body.rowconfigure(2, weight=0)

        self.actions_frame.columnconfigure(0, weight=1)
        for col in (1, 2, 3, 4):
            self.actions_frame.columnconfigure(col, weight=0)

        def _wrap(cb: Optional[Callable[[], None]]) -> Callable[[], None]:
            return (lambda: cb()) if cb else (lambda: None)

        self.btn_iniciar = ctk.CTkButton(
            self.actions_frame, text="Iniciar auditoria", command=_wrap(on_start_auditoria)
        )
        self.btn_subpastas = ctk.CTkButton(
            self.actions_frame,
            text="Ver subpastas",
            command=_wrap(on_view_subpastas),
            state="disabled",
        )
        self.btn_enviar = ctk.CTkButton(
            self.actions_frame,
            text="Enviar arquivos para Auditoria",
            command=_wrap(on_upload_files),
        )
        self.btn_excluir = ctk.CTkButton(
            self.actions_frame,
            text="Excluir auditoria(s)",
            command=_wrap(on_delete),
            state="disabled",
        )

        ctk.CTkLabel(self.actions_frame, text="").grid(row=0, column=0, sticky="ew")
        self.btn_iniciar.grid(row=0, column=1, padx=(0, ui_gap), sticky="e")
        self.btn_subpastas.grid(row=0, column=2, padx=(0, ui_gap), sticky="e")
        self.btn_enviar.grid(row=0, column=3, padx=(0, ui_gap), sticky="e")
        self.btn_excluir.grid(row=0, column=4, padx=(0, 0), sticky="e")
