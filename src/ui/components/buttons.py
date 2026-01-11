# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb

log = logging.getLogger(__name__)

# ============================================================================
# ÍCONES UNICODE PARA BOTÕES MODERNOS
# ============================================================================
# Utilizamos caracteres Unicode para ícones, garantindo compatibilidade
# sem necessidade de arquivos de imagem adicionais.

ICON_NEW = "➕"  # Novo Cliente (plus)
ICON_EDIT = "✏️"  # Editar (pencil)
ICON_DELETE = "🗑️"  # Excluir (trash)
ICON_FILES = "📁"  # Arquivos/Subpastas (folder)
ICON_OBLIGATIONS = "📋"  # Obrigações (clipboard)
ICON_BATCH_DELETE = "🗑️"  # Excluir em lote
ICON_BATCH_RESTORE = "♻️"  # Restaurar em lote
ICON_BATCH_EXPORT = "📤"  # Exportar em lote

# Espaçamento entre ícone e texto
BUTTON_ICON_SPACING = " "


@dataclass(slots=True)
class FooterButtons:
    frame: tb.Frame
    novo: tb.Button
    editar: tb.Button
    subpastas: tb.Button
    excluir: Optional[tb.Button] = None
    obrigacoes: Optional[tb.Button] = None
    batch_delete: Optional[tb.Button] = None
    batch_restore: Optional[tb.Button] = None
    batch_export: Optional[tb.Button] = None


__all__ = ["FooterButtons", "toolbar_button", "create_footer_buttons"]


def toolbar_button(parent: tk.Misc, text: str, command: Callable[[], Any]) -> ttk.Button:
    """Create a standard toolbar button and return it."""
    return ttk.Button(parent, text=text, command=command)


def create_footer_buttons(
    parent: tk.Misc,
    *,
    on_novo: Callable[[], Any],
    on_editar: Callable[[], Any],
    on_subpastas: Callable[[], Any],
    on_excluir: Optional[Callable[[], Any]] = None,
    on_obrigacoes: Optional[Callable[[], Any]] = None,
    on_batch_delete: Optional[Callable[[], Any]] = None,
    on_batch_restore: Optional[Callable[[], Any]] = None,
    on_batch_export: Optional[Callable[[], Any]] = None,
) -> FooterButtons:
    """Create the footer buttons frame used on the main window.

    Melhorias de UI v1.5.41:
    - Ícones Unicode nos botões para visual moderno
    - Hierarquia visual clara:
      - "Novo Cliente" como ação primária (success/verde)
      - "Excluir" como ação perigosa (danger/vermelho)
      - "Editar", "Arquivos" como ações secundárias
    - Padding aumentado para melhor espaçamento
    """
    frame = tb.Frame(parent)

    # =========================================================================
    # BOTÃO PRINCIPAL: Novo Cliente (PRIMARY ACTION)
    # - Cor verde (success) para destaque máximo
    # - Ícone de "+" para indicar criação
    # =========================================================================
    btn_novo = tb.Button(
        frame,
        text=f"{ICON_NEW}{BUTTON_ICON_SPACING}Novo Cliente",
        command=on_novo,
        bootstyle="success",
        width=15,  # Largura fixa para consistência
    )

    # =========================================================================
    # BOTÕES SECUNDÁRIOS: Editar e Arquivos
    # - Estilos mais sutis (secondary, info)
    # - Menor peso visual que a ação principal
    # =========================================================================
    btn_editar = tb.Button(
        frame,
        text=f"{ICON_EDIT}{BUTTON_ICON_SPACING}Editar",
        command=on_editar,
        bootstyle="secondary-outline",  # Outline para menor destaque
    )

    btn_subpastas = tb.Button(
        frame,
        text=f"{ICON_FILES}{BUTTON_ICON_SPACING}Arquivos",
        command=on_subpastas,
        bootstyle="info-outline",  # Info com outline
    )

    # Layout dos botões principais com padding aumentado
    btn_novo.grid(row=0, column=0, padx=(0, 8), pady=8, sticky="w")
    btn_editar.grid(row=0, column=1, padx=8, pady=8, sticky="w")
    btn_subpastas.grid(row=0, column=2, padx=8, pady=8, sticky="w")

    # =========================================================================
    # BOTÃO DE PERIGO: Excluir (DANGER ACTION)
    # - Cor vermelha (danger) para alertar o usuário
    # - Ícone de lixeira
    # =========================================================================
    btn_excluir: Optional[tb.Button] = None
    if on_excluir is not None:
        btn_excluir = tb.Button(
            frame,
            text=f"{ICON_DELETE}{BUTTON_ICON_SPACING}Excluir",
            command=on_excluir,
            bootstyle="danger-outline",  # Danger outline - menos agressivo mas ainda alerta
        )
        btn_excluir.grid(row=0, column=3, padx=8, pady=8, sticky="w")

    # Botão Obrigações (REMOVIDO - funcionalidade movida para Hub)
    # HISTÓRICO: Anteriormente havia um botão "Obrigações" no módulo Clientes.
    # A partir da v1.3.61, a funcionalidade foi centralizada no Hub:
    # - Hub tem botão "+ Nova Obrigação" que abre Modo Seleção de Clientes
    # - Após selecionar cliente, abre a janela de obrigações
    # - Mantemos o campo no dataclass como None para compatibilidade
    btn_obrigacoes: Optional[tb.Button] = None

    # =========================================================================
    # BOTÕES DE OPERAÇÕES EM LOTE (BATCH)
    # - Separados visualmente por um separador vertical
    # - Estilos apropriados para cada ação
    # =========================================================================
    btn_batch_delete: Optional[tb.Button] = None
    btn_batch_restore: Optional[tb.Button] = None
    btn_batch_export: Optional[tb.Button] = None
    next_column = 5

    if on_batch_delete is not None or on_batch_restore is not None or on_batch_export is not None:
        # Separador visual entre ações unitárias e batch
        separator = ttk.Separator(frame, orient="vertical")
        separator.grid(row=0, column=next_column, padx=12, pady=8, sticky="ns")
        next_column += 1

        if on_batch_delete is not None:
            btn_batch_delete = tb.Button(
                frame,
                text=f"{ICON_BATCH_DELETE}{BUTTON_ICON_SPACING}Excluir em Lote",
                command=on_batch_delete,
                bootstyle="danger-outline",
            )
            btn_batch_delete.grid(row=0, column=next_column, padx=8, pady=8, sticky="w")
            next_column += 1

        if on_batch_restore is not None:
            btn_batch_restore = tb.Button(
                frame,
                text=f"{ICON_BATCH_RESTORE}{BUTTON_ICON_SPACING}Restaurar em Lote",
                command=on_batch_restore,
                bootstyle="info-outline",
            )
            btn_batch_restore.grid(row=0, column=next_column, padx=8, pady=8, sticky="w")
            next_column += 1

        if on_batch_export is not None:
            btn_batch_export = tb.Button(
                frame,
                text=f"{ICON_BATCH_EXPORT}{BUTTON_ICON_SPACING}Exportar em Lote",
                command=on_batch_export,
                bootstyle="secondary-outline",
            )
            btn_batch_export.grid(row=0, column=next_column, padx=8, pady=8, sticky="w")
            next_column += 1

    # Configurar pesos (última coluna expansível para empurrar botões à esquerda)
    frame.columnconfigure(next_column, weight=1)

    return FooterButtons(
        frame=frame,
        novo=btn_novo,
        editar=btn_editar,
        subpastas=btn_subpastas,
        excluir=btn_excluir,
        obrigacoes=btn_obrigacoes,
        batch_delete=btn_batch_delete,
        batch_restore=btn_batch_restore,
        batch_export=btn_batch_export,
    )
