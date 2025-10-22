# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb


@dataclass(slots=True)
class FooterButtons:
    frame: tb.Frame
    novo: tb.Button
    editar: tb.Button
    subpastas: tb.Button
    enviar: tb.Button
    lixeira: tb.Button


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
    on_enviar: Callable[[], Any],
    on_lixeira: Callable[[], Any],
) -> FooterButtons:
    """Create the footer buttons frame used on the main window."""
    frame = tb.Frame(parent)

    btn_novo = tb.Button(
        frame, text="Novo Cliente", command=on_novo, bootstyle="success"
    )
    btn_editar = tb.Button(frame, text="Editar", command=on_editar, bootstyle="primary")
    btn_subpastas = tb.Button(
        frame, text="Ver Subpastas", command=on_subpastas, bootstyle="secondary"
    )
    btn_enviar = tb.Button(
        frame, text="Enviar Para SupaBase", command=on_enviar, bootstyle="success"
    )
    btn_lixeira = tb.Button(
        frame, text="Lixeira", command=on_lixeira, bootstyle="warning"
    )

    btn_novo.pack(side="left", padx=5)
    btn_editar.pack(side="left", padx=5)
    btn_subpastas.pack(side="left", padx=5)
    btn_enviar.pack(side="left", padx=5)
    btn_lixeira.pack(side="right", padx=5)

    return FooterButtons(
        frame=frame,
        novo=btn_novo,
        editar=btn_editar,
        subpastas=btn_subpastas,
        enviar=btn_enviar,
        lixeira=btn_lixeira,
    )
