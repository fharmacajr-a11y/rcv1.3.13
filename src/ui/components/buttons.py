# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb

try:
    from ttkbootstrap.tooltip import ToolTip  # type: ignore
except Exception:  # pragma: no cover
    ToolTip = None  # type: ignore


@dataclass(slots=True)
class FooterButtons:
    frame: tb.Frame
    novo: tb.Button
    editar: tb.Button
    subpastas: tb.Button
    enviar: ttk.Menubutton
    enviar_menu: tk.Menu
    excluir: Optional[tb.Button] = None
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
    on_enviar: Callable[[], Any],
    on_enviar_pasta: Callable[[], Any],
    on_excluir: Optional[Callable[[], Any]] = None,
    on_batch_delete: Optional[Callable[[], Any]] = None,
    on_batch_restore: Optional[Callable[[], Any]] = None,
    on_batch_export: Optional[Callable[[], Any]] = None,
) -> FooterButtons:
    """Create the footer buttons frame used on the main window."""
    frame = tb.Frame(parent)

    btn_novo = tb.Button(frame, text="Novo Cliente", command=on_novo, bootstyle="success")
    btn_editar = tb.Button(frame, text="Editar", command=on_editar, bootstyle="secondary")
    btn_subpastas = tb.Button(frame, text="Ver Subpastas", command=on_subpastas, bootstyle="info")
    menubutton_cls = getattr(tb, "Menubutton", ttk.Menubutton)
    btn_enviar = menubutton_cls(frame, text="Enviar Para SupaBase", style="info.TMenubutton")
    menu_enviar = tk.Menu(btn_enviar, tearoff=0)
    menu_enviar.add_command(label="Selecionar PDFs...", command=on_enviar)
    menu_enviar.add_command(label="Selecionar Pasta...", command=on_enviar_pasta)
    btn_enviar["menu"] = menu_enviar

    # Layout dos botões principais
    btn_novo.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    btn_editar.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    btn_subpastas.grid(row=0, column=2, padx=5, pady=5, sticky="w")
    btn_enviar.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    # Botão Excluir (vermelho) ao lado de Enviar Para SupaBase
    btn_excluir: Optional[tb.Button] = None
    if on_excluir is not None:
        btn_excluir = tb.Button(frame, text="Excluir", command=on_excluir, bootstyle="danger")
        btn_excluir.grid(row=0, column=4, padx=5, pady=5, sticky="w")

    # Botões batch (opcionais)
    btn_batch_delete: Optional[tb.Button] = None
    btn_batch_restore: Optional[tb.Button] = None
    btn_batch_export: Optional[tb.Button] = None
    next_column = 5

    if on_batch_delete is not None or on_batch_restore is not None or on_batch_export is not None:
        # Separador visual entre ações unitárias e batch
        separator = ttk.Separator(frame, orient="vertical")
        separator.grid(row=0, column=next_column, padx=10, pady=5, sticky="ns")
        next_column += 1

        if on_batch_delete is not None:
            btn_batch_delete = tb.Button(frame, text="Excluir em Lote", command=on_batch_delete, bootstyle="danger")
            btn_batch_delete.grid(row=0, column=next_column, padx=5, pady=5, sticky="w")
            next_column += 1

        if on_batch_restore is not None:
            btn_batch_restore = tb.Button(frame, text="Restaurar em Lote", command=on_batch_restore, bootstyle="info")
            btn_batch_restore.grid(row=0, column=next_column, padx=5, pady=5, sticky="w")
            next_column += 1

        if on_batch_export is not None:
            btn_batch_export = tb.Button(frame, text="Exportar em Lote", command=on_batch_export, bootstyle="secondary")
            btn_batch_export.grid(row=0, column=next_column, padx=5, pady=5, sticky="w")
            next_column += 1

    # Configurar pesos (última coluna expansível)
    frame.columnconfigure(next_column - 1, weight=1)

    if ToolTip:
        ToolTip(btn_enviar, text="Enviar arquivos ou pastas para o Supabase")

    return FooterButtons(
        frame=frame,
        novo=btn_novo,
        editar=btn_editar,
        subpastas=btn_subpastas,
        enviar=btn_enviar,
        enviar_menu=menu_enviar,
        excluir=btn_excluir,
        batch_delete=btn_batch_delete,
        batch_restore=btn_batch_restore,
        batch_export=btn_batch_export,
    )
