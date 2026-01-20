# -*- coding: utf-8 -*-
from __future__ import annotations

from src.ui.ctk_config import ctk

import tkinter as tk
from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

if TYPE_CHECKING:
    # Para type hints sem quebrar em runtime
    ButtonType = ctk.CTkButton if HAS_CUSTOMTKINTER and ctk is not None else tk.Button
    FrameType = ctk.CTkFrame if HAS_CUSTOMTKINTER and ctk is not None else tk.Frame
else:
    ButtonType = Any
    FrameType = Any


@dataclass(slots=True)
class FooterButtons:
    frame: FrameType
    novo: ButtonType
    editar: ButtonType
    subpastas: ButtonType
    excluir: Optional[ButtonType] = None
    obrigacoes: Optional[ButtonType] = None
    batch_delete: Optional[ButtonType] = None
    batch_restore: Optional[ButtonType] = None
    batch_export: Optional[ButtonType] = None


__all__ = ["FooterButtons", "toolbar_button", "create_footer_buttons"]


def toolbar_button(parent: tk.Misc, text: str, command: Callable[[], Any]) -> ctk.CTkButton:
    """Create a standard toolbar button and return it."""
    return ctk.CTkButton(parent, text=text, command=command)


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
    """Create the footer buttons frame used on the main window."""
    if HAS_CUSTOMTKINTER and ctk is not None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
    else:
        frame = tk.Frame(parent)

    if HAS_CUSTOMTKINTER and ctk is not None:
        btn_novo = ctk.CTkButton(frame, text="Novo Cliente", command=on_novo, fg_color="#28a745", hover_color="#218838")
        btn_editar = ctk.CTkButton(frame, text="Editar", command=on_editar)
        btn_subpastas = ctk.CTkButton(frame, text="Arquivos", command=on_subpastas)
    else:
        btn_novo = tk.Button(frame, text="Novo Cliente", command=on_novo, bg="#28a745", fg="white")
        btn_editar = tk.Button(frame, text="Editar", command=on_editar)
        btn_subpastas = tk.Button(frame, text="Arquivos", command=on_subpastas)

    # Layout dos botões principais
    btn_novo.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    btn_editar.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    btn_subpastas.grid(row=0, column=2, padx=5, pady=5, sticky="w")

    # Botão Excluir (vermelho)
    btn_excluir: Optional[Any] = None
    if on_excluir is not None:
        if HAS_CUSTOMTKINTER and ctk is not None:
            btn_excluir = ctk.CTkButton(frame, text="Excluir", command=on_excluir, fg_color="#dc3545", hover_color="#c82333")
        else:
            btn_excluir = tk.Button(frame, text="Excluir", command=on_excluir, bg="#dc3545", fg="white")
        btn_excluir.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    # Botão Obrigações (REMOVIDO - funcionalidade movida para Hub)
    # HISTÓRICO: Anteriormente havia um botão "Obrigações" no módulo Clientes.
    # A partir da v1.3.61, a funcionalidade foi centralizada no Hub:
    # - Hub tem botão "+ Nova Obrigação" que abre Modo Seleção de Clientes
    # - Após selecionar cliente, abre a janela de obrigações
    # - Mantemos o campo no dataclass como None para compatibilidade
    btn_obrigacoes: Optional[Any] = None

    # Botões batch (opcionais)
    btn_batch_delete: Optional[Any] = None
    btn_batch_restore: Optional[Any] = None
    btn_batch_export: Optional[Any] = None
    next_column = 5

    if on_batch_delete is not None or on_batch_restore is not None or on_batch_export is not None:
        # Separador visual entre ações unitárias e batch
        separator = ctk.CTkFrame(frame, width=2)  # Separador vertical
        separator.grid(row=0, column=next_column, padx=10, pady=5, sticky="ns")
        next_column += 1

        if on_batch_delete is not None:
            if HAS_CUSTOMTKINTER and ctk is not None:
                btn_batch_delete = ctk.CTkButton(frame, text="Excluir em Lote", command=on_batch_delete, fg_color="#dc3545", hover_color="#c82333")
            else:
                btn_batch_delete = tk.Button(frame, text="Excluir em Lote", command=on_batch_delete, bg="#dc3545", fg="white")
            btn_batch_delete.grid(row=0, column=next_column, padx=5, pady=5, sticky="w")
            next_column += 1

        if on_batch_restore is not None:
            if HAS_CUSTOMTKINTER and ctk is not None:
                btn_batch_restore = ctk.CTkButton(frame, text="Restaurar em Lote", command=on_batch_restore)
            else:
                btn_batch_restore = tk.Button(frame, text="Restaurar em Lote", command=on_batch_restore)
            btn_batch_restore.grid(row=0, column=next_column, padx=5, pady=5, sticky="w")
            next_column += 1

        if on_batch_export is not None:
            if HAS_CUSTOMTKINTER and ctk is not None:
                btn_batch_export = ctk.CTkButton(frame, text="Exportar em Lote", command=on_batch_export)
            else:
                btn_batch_export = tk.Button(frame, text="Exportar em Lote", command=on_batch_export)
            btn_batch_export.grid(row=0, column=next_column, padx=5, pady=5, sticky="w")
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
