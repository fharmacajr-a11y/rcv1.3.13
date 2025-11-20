# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable

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
) -> FooterButtons:
    """Create the footer buttons frame used on the main window."""
    frame = tb.Frame(parent)

    btn_novo = tb.Button(frame, text="Novo Cliente", command=on_novo, bootstyle="success")
    btn_editar = tb.Button(frame, text="Editar", command=on_editar, bootstyle="primary")
    btn_subpastas = tb.Button(frame, text="Ver Subpastas", command=on_subpastas, bootstyle="secondary")
    btn_enviar = ttk.Menubutton(frame, text="Enviar Para SupaBase")
    menu_enviar = tk.Menu(btn_enviar, tearoff=0)
    menu_enviar.add_command(label="Selecionar PDFs...", command=on_enviar)
    menu_enviar.add_command(label="Selecionar Pasta...", command=on_enviar_pasta)
    btn_enviar["menu"] = menu_enviar

    btn_novo.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    btn_editar.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    btn_subpastas.grid(row=0, column=2, padx=5, pady=5, sticky="w")
    btn_enviar.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    # Configurar pesos
    frame.columnconfigure(3, weight=1)

    if ToolTip:
        ToolTip(btn_enviar, text="Enviar arquivos ou pastas para o Supabase")

    return FooterButtons(
        frame=frame,
        novo=btn_novo,
        editar=btn_editar,
        subpastas=btn_subpastas,
        enviar=btn_enviar,
        enviar_menu=menu_enviar,
    )
