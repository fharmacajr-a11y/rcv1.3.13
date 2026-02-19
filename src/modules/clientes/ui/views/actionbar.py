# -*- coding: utf-8 -*-
"""ActionBar do ClientesV2 - Padrão Hub (SURFACE_DARK, sem bordas).

TAREFA 2: UI igual ao Hub, tokens do Hub, sem widgets tk legacy.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE_DARK, TEXT_PRIMARY
from src.ui.widgets.button_factory import make_btn

log = logging.getLogger(__name__)


class ClientesV2ActionBar(ctk.CTkFrame):
    """ActionBar do ClientesV2 com botões de ação."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_new: Callable[[], None] | None = None,
        on_edit: Callable[[], None] | None = None,
        on_files: Callable[[], None] | None = None,
        on_delete: Callable[[], None] | None = None,
    ):
        """Inicializa actionbar.

        Args:
            master: Widget pai
            on_new: Callback para novo cliente
            on_edit: Callback para editar cliente
            on_files: Callback para arquivos
            on_delete: Callback para excluir cliente
        """
        # TAREFA 2: Container com SURFACE_DARK (igual Hub)
        super().__init__(master, fg_color=SURFACE_DARK, corner_radius=10, border_width=0)

        self.on_new = on_new
        self.on_edit = on_edit
        self.on_files = on_files
        self.on_delete = on_delete

        self._build_ui()

    def _build_ui(self) -> None:
        """Constrói interface da actionbar."""
        # Botão Novo Cliente (sempre habilitado)
        make_btn(
            self,
            text="Novo Cliente",
            command=self._trigger_new,
            fg_color=("#28a745", "#218838"),
            hover_color=("#218838", "#1e7e34"),
            text_color="#ffffff",
            font=("Segoe UI", 11),
        ).pack(side="left", padx=(10, 5), pady=10)

        # Botão Editar (desabilitado por padrão)
        self.edit_btn = make_btn(
            self,
            text="Editar",
            command=self._trigger_edit,
            fg_color=("#e5e7eb", "#374151"),
            hover_color=("#d1d5db", "#1f2937"),
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 11),
            state="disabled",
        )
        self.edit_btn.pack(side="left", padx=5, pady=10)

        # Botão Arquivos (desabilitado por padrão)
        self.files_btn = make_btn(
            self,
            text="Arquivos",
            command=self._trigger_files,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
            text_color="#ffffff",
            font=("Segoe UI", 11),
            state="disabled",
        )
        self.files_btn.pack(side="left", padx=5, pady=10)

        # Botão Excluir (desabilitado por padrão)
        self.delete_btn = make_btn(
            self,
            text="Excluir",
            command=self._trigger_delete,
            fg_color=("#dc3545", "#c82333"),
            hover_color=("#c82333", "#bd2130"),
            text_color="#ffffff",
            font=("Segoe UI", 11),
            state="disabled",
        )
        self.delete_btn.pack(side="left", padx=5, pady=10)

    def _trigger_new(self) -> None:
        """Dispara callback de novo cliente."""
        if self.on_new:
            self.on_new()

    def _trigger_edit(self) -> None:
        """Dispara callback de editar."""
        if self.on_edit:
            self.on_edit()

    def _trigger_files(self) -> None:
        """Dispara callback de arquivos."""
        if self.on_files:
            self.on_files()

    def _trigger_delete(self) -> None:
        """Dispara callback de excluir."""
        if self.on_delete:
            self.on_delete()

    def set_selection_state(self, has_selection: bool) -> None:
        """Habilita/desabilita botões baseado na seleção.

        Args:
            has_selection: True se há linha selecionada, False caso contrário
        """
        state = "normal" if has_selection else "disabled"
        try:
            self.edit_btn.configure(state=state)
            self.files_btn.configure(state=state)
            self.delete_btn.configure(state=state)
            log.debug(f"[ActionBar] Botões {state}")
        except Exception as e:
            log.error(f"[ActionBar] Erro ao atualizar estado dos botões: {e}")

    def refresh_theme(self) -> None:
        """Atualiza cores da actionbar quando tema muda.

        TAREFA 4: Integração de tema - tokens alternam automaticamente.
        """
        try:
            self.configure(fg_color=SURFACE_DARK)
            self.update_idletasks()
            log.debug("[ClientesV2] ActionBar tema atualizado")
        except Exception:
            log.exception("[ClientesV2] Erro ao atualizar tema da actionbar")
