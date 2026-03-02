# -*- coding: utf-8 -*-
"""Mixin de construção de UI para ClientEditorDialog.

Extraído de client_editor_dialog.py (Fase 5 - refatoração incremental).
Contém: _build_ui, _build_left_panel, _build_right_panel, _build_buttons,
         _sync_right_spacer_height, _set_entry_value, _activate_all_placeholders.
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

        # Grid com 3 linhas: conteúdo (0), separador (1), botões (2)
        main_frame.rowconfigure(0, weight=1)  # Conteúdo expande
        main_frame.rowconfigure(1, weight=0)  # Separador fixo
        main_frame.rowconfigure(2, weight=0)  # Botões fixo
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=0)
        main_frame.columnconfigure(
            2, weight=4, minsize=440
        )  # Aumentado weight e minsize para dar mais espaço ao painel direito

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

        # AJUSTE 3: Separador horizontal antes dos botões
        separator_line = ctk.CTkFrame(
            main_frame,
            height=1,
            fg_color=BORDER,
        )
        separator_line.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 0))

        # Barra de botões (rodapé) - agora em row=2
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

        # Observações (grande)
        ctk.CTkLabel(parent, text="Observações:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        obs_row = row
        self.obs_text = ctk.CTkTextbox(
            parent,
            height=150,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",  # Wrap por palavra para melhor legibilidade
        )
        self.obs_text.grid(row=row, column=0, sticky="nsew", padx=6, pady=(0, 10))
        parent.rowconfigure(obs_row, weight=1)
        row += 1

        # OBJETIVO 2: Status do Cliente + botão Senhas (colados)
        status_container = ctk.CTkFrame(parent, fg_color="transparent")
        status_container.grid(row=row, column=0, sticky="w", padx=6, pady=(0, 6))
        status_container.columnconfigure(0, weight=0)  # Sem expansão
        status_container.columnconfigure(1, weight=0)  # Sem expansão
        status_container.columnconfigure(2, weight=0)  # Arquivos

        # Salvar referência para usar no painel direito (igualar alturas)
        self._status_container = status_container

        # Bind para sincronizar altura do spacer direito em tempo real
        status_container.bind("<Configure>", lambda e: self._sync_right_spacer_height())

        ctk.CTkLabel(status_container, text="Status do Cliente:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 2)
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
        self.status_combo.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=0)

        # Botão Senhas colado ao Status
        self.senhas_btn = make_btn(
            status_container,
            text="Senhas",
            command=self._on_senhas,
            fg_color="gray",
            hover_color="darkgray",
            width=70,
            height=28,
            state="normal" if self.client_id else "disabled",
        )
        self.senhas_btn.grid(row=1, column=1, sticky="w", padx=(0, 0), pady=0)

        # Botão Arquivos colado ao Senhas
        self.arquivos_btn = make_btn(
            status_container,
            text="Arquivos",
            command=self._on_arquivos,
            fg_color="gray",
            hover_color="darkgray",
            width=85,
            height=28,
            state="normal" if self.client_id else "disabled",
        )
        self.arquivos_btn.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=0)

    def _build_right_panel(self: EditorDialogProto, parent: ctk.CTkFrame) -> None:
        """Constrói painel direito com campos internos."""
        row = 0

        # Endereço (interno)
        ctk.CTkLabel(parent, text="Endereço (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(5, 0)
        )
        row += 1
        self.endereco_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Endereço da empresa",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.endereco_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Bairro (interno)
        ctk.CTkLabel(parent, text="Bairro (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.bairro_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Bairro",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.bairro_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Cidade (interno)
        ctk.CTkLabel(parent, text="Cidade (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.cidade_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Cidade",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.cidade_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # CEP (interno)
        ctk.CTkLabel(parent, text="CEP (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.cep_entry = ctk.CTkEntry(
            parent,
            placeholder_text="00000-000",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.cep_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Contatos adicionais (textbox grande, mesmo padrão visual dos outros campos)
        ctk.CTkLabel(
            parent,
            text="Contatos adicionais:",
            anchor="w",
            text_color=TEXT_PRIMARY,
        ).grid(row=row, column=0, sticky="w", padx=6, pady=(0, 0))
        row += 1

        # Textbox para contatos adicionais (mesmas cores de Observações)
        contatos_row = row
        self.contatos_text = ctk.CTkTextbox(
            parent,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",
        )
        self.contatos_text.grid(row=row, column=0, sticky="nsew", padx=6, pady=(0, 10))
        parent.rowconfigure(contatos_row, weight=1)  # Expande para ocupar espaço disponível
        row += 1

        # Spacer para igualar altura com Observações (compensar o bloco Status do painel esquerdo)
        # A altura será sincronizada dinamicamente pelo método _sync_right_spacer_height()
        spacer_height = 70  # Fallback inicial (será atualizado após renderização)
        self._right_spacer = ctk.CTkFrame(parent, fg_color="transparent", height=spacer_height)
        self._right_spacer.grid(row=row, column=0, sticky="ew", padx=6, pady=0)
        self._right_spacer.grid_propagate(False)  # Manter altura configurada
        row += 1

    def _sync_right_spacer_height(self: EditorDialogProto) -> None:
        """Sincroniza altura do spacer direito com o bloco Status esquerdo (pixel-perfect).

        Este método garante que o textbox "Contatos adicionais" termine exatamente
        na mesma linha que o textbox "Observações", compensando a altura do bloco
        "Status do Cliente" no painel esquerdo.
        """
        try:
            # Forçar atualização de geometria
            self.update_idletasks()

            # Obter altura real do status_container
            h = self._status_container.winfo_height()
            if h <= 1:
                # Widget ainda não renderizado, usar altura requisitada
                h = self._status_container.winfo_reqheight()

            # Obter padding vertical do grid do status_container
            gi = self._status_container.grid_info()
            pady = gi.get("pady", 0)

            # Calcular padding extra
            extra = 0
            if isinstance(pady, (tuple, list)):
                extra = sum(int(p) for p in pady)
            else:
                extra = int(pady) if pady else 0

            # Altura alvo para o spacer (altura do container + padding)
            target = h + extra

            # Aplicar no spacer (mínimo 50px para evitar valores negativos/zero)
            if target > 0:
                self._right_spacer.configure(height=max(target, 50))

        except Exception as e:
            # Silenciar erros durante destruição de widgets
            log.debug(f"[ClientEditor] Erro ao sincronizar spacer: {e}")

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
            self.endereco_entry,
            self.bairro_entry,
            self.cidade_entry,
            self.cep_entry,
        ]
        for entry in entries:
            self._set_entry_value(entry, "")

    def _build_buttons(self: EditorDialogProto, parent: ctk.CTkFrame) -> None:
        """Constrói barra de botões no rodapé."""
        # OBJETIVO 3: Botões dentro do container esquerdo (não atravessa divisor)
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, sticky="w", padx=10, pady=(8, 10))

        # Botão Salvar (verde)
        self.save_btn = make_btn(
            buttons_frame,
            text="Salvar",
            command=self._on_save_clicked,
            fg_color="#28a745",
            hover_color="#218838",
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

        # Botão Cancelar (vermelho)
        self.cancel_btn = make_btn(
            buttons_frame,
            text="Cancelar",
            command=self._on_cancel,
            fg_color="#dc3545",
            hover_color="#c82333",
        )
        self.cancel_btn.pack(side="left", padx=5)

        # BIND CENTRALIZADO: Enter chama handler unificado (gerencia Shift+Enter em Observações e Contatos)
        self.bind("<Return>", self._on_return_key)
        self.bind("<KP_Enter>", self._on_return_key)  # Numpad Enter
        self.bind("<Escape>", lambda e: self._on_cancel())
