# -*- coding: utf-8 -*-
"""Mixin de construção de UI para ClientEditorDialog.

Extraído de client_editor_dialog.py (Fase 5 - refatoração incremental).
Contém: _build_ui, _build_left_panel, _build_right_panel, _build_status_row,
         _build_buttons, _set_entry_value, _activate_all_placeholders.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn
from src.ui.ui_tokens import (
    SURFACE,
    SURFACE_DARK,
    TEXT_PRIMARY,
    TEXT_MUTED,
    BORDER,
    APP_BG,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    BTN_DANGER,
    BTN_DANGER_HOVER,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    BTN_SUCCESS,
    BTN_SUCCESS_HOVER,
)
from src.modules.clientes.core.constants import STATUS_CHOICES

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import EditorDialogProto

log = logging.getLogger(__name__)


class EditorUIMixin:
    """Mixin responsável pela construção da UI do ClientEditorDialog."""

    def _build_ui(self: EditorDialogProto) -> None:
        """Constrói a interface do diálogo."""
        # TAREFA C: Background cinza claro (sem borda branca)
        self.configure(fg_color=APP_BG)

        # TAREFA C: Container principal - sem padding externo (remove borda branca)
        main_frame = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Grid com 4 linhas: conteúdo (0), status (1), separador (2), botões (3)
        main_frame.rowconfigure(0, weight=0)  # Conteúdo: altura natural do painel esquerdo
        main_frame.rowconfigure(1, weight=0)  # Status fixo (espaço extra vai para o fundo da janela)
        main_frame.rowconfigure(2, weight=0)  # Separador fixo
        main_frame.rowconfigure(3, weight=0)  # Botões fixo
        main_frame.columnconfigure(0, weight=1)  # Painel esquerdo
        main_frame.columnconfigure(1, weight=0)  # Separador vertical
        main_frame.columnconfigure(2, weight=1)  # Painel direito (50/50)

        # Divisão em duas colunas (como legado)
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        sep = ctk.CTkFrame(main_frame, width=2, fg_color=BORDER)
        sep.grid(row=0, column=1, sticky="ns", pady=10)

        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)

        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # Construir painéis
        self._build_left_panel(left_frame)
        self._build_right_panel(right_frame)

        # Status do Cliente (abaixo da área de conteúdo, coluna esquerda)
        self._build_status_row(main_frame)

        # AJUSTE 3: Separador horizontal antes dos botões
        separator_line = ctk.CTkFrame(
            main_frame,
            height=1,
            fg_color=BORDER,
        )
        separator_line.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 0))

        # Barra de botões (rodapé) - agora em row=3
        self._build_buttons(main_frame)

    def _build_left_panel(self: EditorDialogProto, parent: ctk.CTkFrame) -> None:
        """Constrói painel esquerdo com campos principais."""
        row = 0

        # Razão Social *
        ctk.CTkLabel(parent, text="Razão Social:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(5, 0)
        )
        row += 1
        self.razao_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Nome da empresa",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.razao_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # CNPJ *
        ctk.CTkLabel(parent, text="CNPJ:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.cnpj_entry = ctk.CTkEntry(
            parent,
            placeholder_text="00.000.000/0000-00",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.cnpj_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        # Bind para formatar ao sair do campo
        self.cnpj_entry.bind("<FocusOut>", self._on_cnpj_focus_out)
        row += 1

        # Nome
        ctk.CTkLabel(parent, text="Nome:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.nome_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Nome usado no dia-a-dia",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.nome_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # WhatsApp
        ctk.CTkLabel(parent, text="WhatsApp:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.whatsapp_entry = ctk.CTkEntry(
            parent,
            placeholder_text="(00) 00000-0000",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.whatsapp_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        # Bind para formatar ao sair do campo
        self.whatsapp_entry.bind("<FocusOut>", self._on_whatsapp_focus_out)
        row += 1

        # Observações
        ctk.CTkLabel(parent, text="Observações:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.obs_text = ctk.CTkTextbox(
            parent,
            height=90,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",
        )
        self.obs_text.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Contatos adicionais (movido do painel direito)
        ctk.CTkLabel(
            parent,
            text="Contatos adicionais:",
            anchor="w",
            text_color=TEXT_PRIMARY,
        ).grid(row=row, column=0, sticky="w", padx=6, pady=(0, 0))
        row += 1
        self.contatos_text = ctk.CTkTextbox(
            parent,
            height=90,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",
        )
        self.contatos_text.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 10))

    def _build_right_panel(self: EditorDialogProto, parent: ctk.CTkFrame) -> None:
        """Constrói painel direito com bloco de notas interno."""
        row = 0

        # Bloco de notas (textarea expandível com scroll interno)
        ctk.CTkLabel(
            parent,
            text="Bloco de notas:",
            anchor="w",
            text_color=TEXT_PRIMARY,
        ).grid(row=row, column=0, sticky="w", padx=6, pady=(5, 0))
        row += 1

        bloco_notas_row = row
        self.bloco_notas_text = ctk.CTkTextbox(
            parent,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",
        )
        self.bloco_notas_text.grid(row=row, column=0, sticky="nsew", padx=6, pady=(0, 10))
        parent.rowconfigure(bloco_notas_row, weight=1)
        row += 1

    def _build_status_row(self: EditorDialogProto, parent: ctk.CTkFrame) -> None:
        """Constrói a linha de status do cliente abaixo da área de conteúdo."""
        status_container = ctk.CTkFrame(parent, fg_color="transparent")
        status_container.grid(row=1, column=0, sticky="nw", padx=(16, 5), pady=(0, 6))

        ctk.CTkLabel(status_container, text="Status do Cliente:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )

        self.status_var = tk.StringVar(value="Novo Cliente")
        self.status_combo = ctk.CTkOptionMenu(
            status_container,
            variable=self.status_var,
            values=STATUS_CHOICES,
            fg_color=SURFACE,
            button_color=PRIMARY_BLUE,
            button_hover_color=PRIMARY_BLUE_HOVER,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=SURFACE_DARK,
            dropdown_text_color=TEXT_PRIMARY,
            width=160,
            height=28,
        )
        self.status_combo.grid(row=1, column=0, sticky="w", pady=0)

    def _set_entry_value(self: EditorDialogProto, entry: ctk.CTkEntry, value: str) -> None:
        """Define valor em CTkEntry preservando placeholder quando vazio.

        Args:
            entry: CTkEntry a ser preenchido
            value: Valor a ser inserido (ou vazio para ativar placeholder)
        """
        entry.delete(0, "end")
        value = (value or "").strip()
        if value:
            entry.insert(0, value)
            return

        # Campo vazio: forçar ativação do placeholder (método interno do CustomTkinter)
        # NÃO mexer em foco aqui para evitar flash durante construção da UI
        if hasattr(entry, "_activate_placeholder"):
            try:
                entry._activate_placeholder()  # pyright: ignore[reportAttributeAccessIssue]
            except Exception:
                pass

    def _activate_all_placeholders(self: EditorDialogProto) -> None:
        """Ativa placeholders em todos os CTkEntry vazios (usado no Novo Cliente)."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        entries = [
            self.razao_entry,
            self.cnpj_entry,
            self.nome_entry,
            self.whatsapp_entry,
        ]
        for entry in entries:
            self._set_entry_value(entry, "")

    def _build_buttons(self: EditorDialogProto, parent: ctk.CTkFrame) -> None:
        """Constrói barra de botões no rodapé."""
        # OBJETIVO 3: Botões dentro do container esquerdo (não atravessa divisor)
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 10))

        # Botão Salvar (verde)
        self.save_btn = make_btn(
            buttons_frame,
            text="Salvar",
            command=self._on_save_clicked,
            fg_color=BTN_SUCCESS,
            hover_color=BTN_SUCCESS_HOVER,
        )
        self.save_btn.pack(side="left", padx=(0, 5))

        # Botão Cartão CNPJ (azul)
        self.cartao_btn = make_btn(
            buttons_frame,
            text="Cartão CNPJ",
            command=self._on_cartao_cnpj,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
        )
        self.cartao_btn.pack(side="left", padx=5)

        # Botão Enviar documentos (azul)
        self.upload_btn = make_btn(
            buttons_frame,
            text="Enviar documentos",
            command=self._on_enviar_documentos,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
        )
        self.upload_btn.pack(side="left", padx=5)

        # Botão Arquivos (cinza) - imediatamente à esquerda do Cancelar
        self.arquivos_btn = make_btn(
            buttons_frame,
            text="Arquivos",
            command=self._on_arquivos,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            state="normal" if self.client_id else "disabled",
        )
        self.arquivos_btn.pack(side="left", padx=5)

        # Botão Cancelar (vermelho)
        self.cancel_btn = make_btn(
            buttons_frame,
            text="Cancelar",
            command=self._on_cancel,
            fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER,
        )
        self.cancel_btn.pack(side="left", padx=5)

        # BIND CENTRALIZADO: Enter chama handler unificado (gerencia Shift+Enter em Observações e Contatos)
        self.bind("<Return>", self._on_return_key)
        self.bind("<KP_Enter>", self._on_return_key)  # Numpad Enter
        self.bind("<Escape>", lambda e: self._on_cancel())
