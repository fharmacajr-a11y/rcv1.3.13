# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb


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


def toolbar_button(
    parent: tk.Misc, text: str, command: Callable[[], Any]
) -> ttk.Button:
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

    Hierarquia visual dos botões:
    - "Novo Cliente": Primário (success) - ação principal mais proeminente
    - "Editar": Secundário (outline) - ação comum mas não principal
    - "Arquivos": Info (outline) - ação auxiliar
    - "Excluir": Perigo (danger) - ação destrutiva

    Todos os botões incluem ícones para modernidade visual.
    """
    frame = tb.Frame(parent)

    # ========================================================================
    # BOTÃO PRINCIPAL - NOVO CLIENTE (mais proeminente)
    # ========================================================================
    btn_novo = tb.Button(
        frame,
        text="➕ Novo Cliente",
        command=on_novo,
        bootstyle="success",
        width=14,
    )

    # ========================================================================
    # BOTÕES SECUNDÁRIOS
    # ========================================================================
    btn_editar = tb.Button(
        frame,
        text="✏️ Editar",
        command=on_editar,
        bootstyle="secondary-outline",
        width=10,
    )
    btn_subpastas = tb.Button(
        frame,
        text="📁 Arquivos",
        command=on_subpastas,
        bootstyle="info-outline",
        width=10,
    )

    # Layout dos botões principais com espaçamento adequado
    btn_novo.grid(row=0, column=0, padx=(0, 8), pady=5, sticky="w")
    btn_editar.grid(row=0, column=1, padx=4, pady=5, sticky="w")
    btn_subpastas.grid(row=0, column=2, padx=4, pady=5, sticky="w")

    # ========================================================================
    # BOTÃO EXCLUIR (estilo perigo)
    # ========================================================================
    btn_excluir: Optional[tb.Button] = None
    if on_excluir is not None:
        btn_excluir = tb.Button(
            frame,
            text="🗑️ Excluir",
            command=on_excluir,
            bootstyle="danger-outline",
            width=10,
        )
        btn_excluir.grid(row=0, column=3, padx=4, pady=5, sticky="w")

    # Botão Obrigações (REMOVIDO - funcionalidade movida para Hub)
    # HISTÓRICO: Anteriormente havia um botão "Obrigações" no módulo Clientes.
    # A partir da v1.3.61, a funcionalidade foi centralizada no Hub:
    # - Hub tem botão "+ Nova Obrigação" que abre Modo Seleção de Clientes
    # - Após selecionar cliente, abre a janela de obrigações
    # - Mantemos o campo no dataclass como None para compatibilidade
    btn_obrigacoes: Optional[tb.Button] = None

    # ========================================================================
    # BOTÕES BATCH (opcionais)
    # ========================================================================
    btn_batch_delete: Optional[tb.Button] = None
    btn_batch_restore: Optional[tb.Button] = None
    btn_batch_export: Optional[tb.Button] = None
    next_column = 5

    if (
        on_batch_delete is not None
        or on_batch_restore is not None
        or on_batch_export is not None
    ):
        # Separador visual entre ações unitárias e batch
        separator = ttk.Separator(frame, orient="vertical")
        separator.grid(row=0, column=next_column, padx=12, pady=5, sticky="ns")
        next_column += 1

        if on_batch_delete is not None:
            btn_batch_delete = tb.Button(
                frame,
                text="🗑️ Excluir em Lote",
                command=on_batch_delete,
                bootstyle="danger-outline",
            )
            btn_batch_delete.grid(row=0, column=next_column, padx=4, pady=5, sticky="w")
            next_column += 1

        if on_batch_restore is not None:
            btn_batch_restore = tb.Button(
                frame,
                text="♻️ Restaurar em Lote",
                command=on_batch_restore,
                bootstyle="info-outline",
            )
            btn_batch_restore.grid(
                row=0, column=next_column, padx=4, pady=5, sticky="w"
            )
            next_column += 1

        if on_batch_export is not None:
            btn_batch_export = tb.Button(
                frame,
                text="📤 Exportar em Lote",
                command=on_batch_export,
                bootstyle="secondary-outline",
            )
            btn_batch_export.grid(row=0, column=next_column, padx=4, pady=5, sticky="w")
            next_column += 1

    # Configurar pesos (última coluna expansível)
    frame.columnconfigure(next_column - 1, weight=1)

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
