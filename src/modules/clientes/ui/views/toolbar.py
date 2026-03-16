# -*- coding: utf-8 -*-
"""Toolbar do ClientesV2 - Padrão Hub (SURFACE_DARK, sem bordas).

TAREFA 2: UI igual ao Hub, tokens do Hub, sem widgets tk legacy.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    SURFACE,
    SURFACE_DARK,
    TEXT_PRIMARY,
    TEXT_MUTED,
    BORDER,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    BTN_DANGER,
    BTN_DANGER_HOVER,
    BTN_SUCCESS,
    BTN_SUCCESS_HOVER,
)
from src.ui.widgets.button_factory import make_btn

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
        self._status_values: list[str] = []  # Lista de status disponíveis (preenchida dinamicamente)

        self._build_ui()

    def _build_ui(self) -> None:
        """Constrói interface da toolbar."""
        # Label "Pesquisar:"
        ctk.CTkLabel(self, text="Pesquisar:", text_color=TEXT_PRIMARY, font=("Segoe UI", 11)).pack(
            side="left", padx=(10, 5), pady=10
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
        self.entry_search.pack(side="left", padx=5, pady=10)
        self.entry_search.bind("<Return>", lambda e: self._trigger_search())
        # Debounce na digitação (400ms)
        self.search_var.trace_add("write", lambda *_: self._on_search_text_changed())  # type: ignore[attr-defined]

        # Botão Buscar
        make_btn(
            self,
            text="Buscar",
            command=self._trigger_search,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
        ).pack(side="left", padx=5, pady=10)

        # Botão Limpar
        make_btn(
            self,
            text="Limpar",
            command=self._trigger_clear,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
        ).pack(side="left", padx=5, pady=10)

        # Ordenar
        ctk.CTkLabel(self, text="Ordenar por:", text_color=TEXT_PRIMARY, font=("Segoe UI", 11)).pack(
            side="left", padx=(15, 5), pady=10
        )

        self.order_combo = ctk.CTkOptionMenu(
            self,
            variable=self.order_var,
            values=[
                "Última Alteração (+)",
                "Última Alteração (-)",
                "ID (1-9)",
                "ID (9-1)",
                "Razão Social (A→Z)",
                "Razão Social (Z→A)",
                "Nome (A→Z)",
                "Nome (Z→A)",
                "WhatsApp (DDD - → +)",
                "WhatsApp (DDD + → -)",
            ],
            command=self._trigger_order_change,
            fg_color=SURFACE,
            bg_color=SURFACE_DARK,
            button_color=PRIMARY_BLUE,
            button_hover_color=PRIMARY_BLUE_HOVER,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=SURFACE_DARK,
            dropdown_text_color=TEXT_PRIMARY,
            width=200,
            height=28,
        )
        self.order_combo.pack(side="left", padx=5, pady=10)

        # Status principal (inclui opções especiais agregadas FP / Anvisa)
        ctk.CTkLabel(self, text="Status Geral:", text_color=TEXT_PRIMARY, font=("Segoe UI", 11)).pack(
            side="left", padx=(15, 5), pady=10
        )
        from src.modules.clientes.core.constants import STATUS_CHOICES

        _principals = [s for s in STATUS_CHOICES if s.strip() and s.strip() != "---"]
        self._status_values = ["Todos"] + _principals + ["Farmácia Popular", "Anvisa"]
        self.status_combo = ctk.CTkOptionMenu(
            self,
            variable=self.status_var,
            values=self._status_values,
            command=self._trigger_status_change,
            fg_color=SURFACE,
            bg_color=SURFACE_DARK,
            button_color=PRIMARY_BLUE,
            button_hover_color=PRIMARY_BLUE_HOVER,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=SURFACE_DARK,
            dropdown_text_color=TEXT_PRIMARY,
            width=185,
            height=28,
        )
        self.status_combo.pack(side="left", padx=5, pady=10)

        # FASE 3.5: Botão Exportar
        # Botão Lixeira (pack side=right primeiro → fica mais à direita)
        self.trash_btn = make_btn(
            self,
            text="Lixeira",
            command=self._trigger_trash,
            fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER,
        )
        self.trash_btn.pack(side="right", padx=(0, 10), pady=10)

        # FASE 3.5: Botão Exportar (ao lado esquerdo do Lixeira, 5px entre eles)
        self.export_btn = make_btn(
            self,
            text="Exportar",
            command=self._trigger_export,
            fg_color=BTN_SUCCESS,
            hover_color=BTN_SUCCESS_HOVER,
        )
        self.export_btn.pack(side="right", padx=(0, 5), pady=10)

    def _trigger_search(self) -> None:
        """Dispara callback de busca."""
        if self.on_search:
            self.on_search(self.search_var.get())

    def _trigger_clear(self) -> None:
        """Dispara callback de limpar."""
        self.search_var.set("")
        self.status_var.set("Todos")
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
        """Retorna status filtrado (string vazia para 'Todos')."""
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

            if hasattr(self, "order_combo"):
                self.order_combo.configure(
                    fg_color=SURFACE,
                    button_color=PRIMARY_BLUE,
                    button_hover_color=PRIMARY_BLUE_HOVER,
                    text_color=TEXT_PRIMARY,
                    dropdown_fg_color=SURFACE_DARK,
                    dropdown_text_color=TEXT_PRIMARY,
                )

            if hasattr(self, "status_combo"):
                self.status_combo.configure(
                    fg_color=SURFACE,
                    button_color=PRIMARY_BLUE,
                    button_hover_color=PRIMARY_BLUE_HOVER,
                    text_color=TEXT_PRIMARY,
                    dropdown_fg_color=SURFACE_DARK,
                    dropdown_text_color=TEXT_PRIMARY,
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
            self.trash_btn.configure(text="📋 Ativos", fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER)
        else:
            self.trash_btn.configure(text="🗑️ Lixeira", fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER)

    def update_status_values(self, extra_statuses: list[str] | None = None) -> None:
        """Atualiza lista de status disponíveis no dropdown principal."""
        from src.modules.clientes.core.constants import STATUS_CHOICES

        principals = [s for s in STATUS_CHOICES if s.strip() and s.strip() != "---"]

        if extra_statuses:
            known = {s.lower() for s in principals}
            for s in extra_statuses:
                sc = s.strip()
                if sc and sc.lower() not in known and sc != "---":
                    principals.append(sc)

        # Opções especiais agregadas sempre ao final
        _special = ["Farmácia Popular", "Anvisa"]
        known_lower = {p.lower() for p in principals}
        all_values = ["Todos"] + principals + [s for s in _special if s.lower() not in known_lower]

        self._status_values = all_values
        current_value = self.status_var.get()
        self.status_combo.configure(values=self._status_values)

        if current_value not in self._status_values:
            self.status_var.set("Todos")
            log.info(f"[Toolbar] Status '{current_value}' não encontrado, resetado para 'Todos'")
