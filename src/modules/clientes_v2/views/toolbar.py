# -*- coding: utf-8 -*-
"""Toolbar do ClientesV2 - Padrão Hub (SURFACE_DARK, sem bordas).

TAREFA 2: UI igual ao Hub, tokens do Hub, sem widgets tk legacy.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, BORDER

log = logging.getLogger(__name__)


class ClientesV2Toolbar(ctk.CTkFrame):
    """Toolbar do ClientesV2 com busca, filtros e lixeira."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_search: Callable[[str], None] | None = None,
        on_clear: Callable[[], None] | None = None,
        on_order_change: Callable[[str], None] | None = None,
        on_status_change: Callable[[str], None] | None = None,
        on_trash: Callable[[], None] | None = None,
        on_export: Callable[[], None] | None = None,
    ):
        """Inicializa toolbar.

        Args:
            master: Widget pai
            on_search: Callback para busca
            on_clear: Callback para limpar busca
            on_order_change: Callback para mudança de ordenação
            on_status_change: Callback para mudança de status
            on_trash: Callback para abrir lixeira
            on_export: Callback para exportar dados (FASE 3.5)
        """
        # TAREFA 2: Container com SURFACE_DARK (igual Hub)
        super().__init__(master, fg_color=SURFACE_DARK, corner_radius=10, border_width=0)

        self.on_search = on_search
        self.on_clear = on_clear
        self.on_order_change = on_order_change
        self.on_status_change = on_status_change
        self.on_trash = on_trash
        self.on_export = on_export  # FASE 3.5

        # Variáveis
        self.search_var = tk.StringVar()
        self.order_var = tk.StringVar(value="Razão Social (A→Z)")
        self.status_var = tk.StringVar(value="Todos")
        self._debounce_job: str | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Constrói interface da toolbar."""
        # Label "Pesquisar:"
        ctk.CTkLabel(self, text="Pesquisar:", text_color=TEXT_PRIMARY, font=("Segoe UI", 11)).pack(
            side="left", padx=(10, 5)
        )

        # Entry de busca
        self.entry_search = ctk.CTkEntry(
            self,
            textvariable=self.search_var,
            placeholder_text="Digite para buscar...",
            fg_color=SURFACE,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            border_color=BORDER,
            width=250,
        )
        self.entry_search.pack(side="left", padx=5)
        self.entry_search.bind("<Return>", lambda e: self._trigger_search())
        # Debounce na digitação (400ms)
        self.search_var.trace_add("write", lambda *_: self._on_search_text_changed())  # type: ignore[attr-defined]

        # Botão Buscar
        ctk.CTkButton(
            self,
            text="🔍 Buscar",
            command=self._trigger_search,
            width=100,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
        ).pack(side="left", padx=5)

        # Botão Limpar
        ctk.CTkButton(
            self,
            text="❌ Limpar",
            command=self._trigger_clear,
            width=100,
            fg_color=("#6c757d", "#495057"),
            hover_color=("#5a6268", "#343a40"),
        ).pack(side="left", padx=5)

        # Ordenar
        ctk.CTkLabel(self, text="Ordenar:", text_color=TEXT_PRIMARY, font=("Segoe UI", 11)).pack(
            side="left", padx=(15, 5)
        )

        self.order_combo = ctk.CTkOptionMenu(
            self,
            variable=self.order_var,
            values=[
                "ID (↑)",
                "ID (↓)",
                "Razão Social (A→Z)",
                "Razão Social (Z→A)",
                "Última Alteração ↓",
                "Última Alteração ↑",
            ],
            command=self._trigger_order_change,
            fg_color=SURFACE,
            button_color=SURFACE,
            button_hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            width=200,
        )
        self.order_combo.pack(side="left", padx=5)

        # Status
        ctk.CTkLabel(self, text="Status:", text_color=TEXT_PRIMARY, font=("Segoe UI", 11)).pack(
            side="left", padx=(15, 5)
        )

        self.status_combo = ctk.CTkOptionMenu(
            self,
            variable=self.status_var,
            values=["Todos", "Novo Cliente", "Análise Do Ministério", "Cadastro Pendente"],
            command=self._trigger_status_change,
            fg_color=SURFACE,
            button_color=SURFACE,
            button_hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            width=180,
        )
        self.status_combo.pack(side="left", padx=5)

        # FASE 3.5: Botão Exportar
        self.export_btn = ctk.CTkButton(
            self,
            text="📊 Exportar",
            command=self._trigger_export,
            width=110,
            fg_color=("#28a745", "#218838"),
            hover_color=("#218838", "#1e7e34"),
        )
        self.export_btn.pack(side="right", padx=(5, 5))

        # Botão Lixeira
        self.trash_btn = ctk.CTkButton(
            self,
            text="🗑️ Lixeira",
            command=self._trigger_trash,
            width=100,
            fg_color=("#dc3545", "#c82333"),
            hover_color=("#c82333", "#bd2130"),
        )
        self.trash_btn.pack(side="right", padx=(5, 10))

    def _trigger_search(self) -> None:
        """Dispara callback de busca."""
        if self.on_search:
            self.on_search(self.search_var.get())

    def _trigger_clear(self) -> None:
        """Dispara callback de limpar."""
        self.search_var.set("")
        if self.on_clear:
            self.on_clear()

    def _trigger_order_change(self, value: str) -> None:
        """Dispara callback de mudança de ordenação."""
        if self.on_order_change:
            self.on_order_change(value)

    def _trigger_status_change(self, value: str) -> None:
        """Dispara callback de mudança de status."""
        if self.on_status_change:
            self.on_status_change(value)

    def _trigger_trash(self) -> None:
        """Dispara callback de lixeira."""
        if self.on_trash:
            self.on_trash()

    def _trigger_export(self) -> None:
        """Dispara callback de exportação (FASE 3.5)."""
        if self.on_export:
            self.on_export()

    def _on_search_text_changed(self) -> None:
        """Handler de debounce para entrada de texto."""
        # Cancelar job anterior
        if self._debounce_job:
            try:
                self.after_cancel(self._debounce_job)
            except Exception:
                pass

        # Agendar nova busca (400ms)
        self._debounce_job = self.after(400, self._trigger_search)

    def get_search_text(self) -> str:
        """Retorna texto atual da busca."""
        return self.search_var.get().strip()

    def get_order(self) -> str:
        """Retorna label de ordenação atual."""
        return self.order_var.get()

    def get_status(self) -> str:
        """Retorna status filtrado (ou string vazia para 'Todos')."""
        status = self.status_var.get()
        return "" if status == "Todos" else status

    def clear_search(self) -> None:
        """Limpa campo de busca."""
        self.search_var.set("")

    def refresh_theme(self) -> None:
        """Atualiza cores da toolbar quando tema muda.

        TAREFA 4: Integração de tema - tokens alternam automaticamente.
        """
        try:
            # Tokens são tuplas (light, dark) que alternam automaticamente
            # Só precisamos forçar reconfigure
            self.configure(fg_color=SURFACE_DARK)

            if hasattr(self, "entry_search"):
                self.entry_search.configure(
                    fg_color=SURFACE, text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED, border_color=BORDER
                )

            self.update_idletasks()
            log.debug("[ClientesV2] Toolbar tema atualizado")
        except Exception:
            log.exception("[ClientesV2] Erro ao atualizar tema da toolbar")

    def update_trash_mode(self, is_trash: bool) -> None:
        """Atualiza label do botão lixeira conforme modo.

        Args:
            is_trash: True se modo lixeira ativo, False se modo normal
        """
        if is_trash:
            self.trash_btn.configure(
                text="📋 Ativos", fg_color=("#28a745", "#218838"), hover_color=("#218838", "#1e7e34")
            )
        else:
            self.trash_btn.configure(
                text="🗑️ Lixeira", fg_color=("#dc3545", "#c82333"), hover_color=("#c82333", "#bd2130")
            )
