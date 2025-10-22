# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb


@dataclass(slots=True)
class SearchControls:
    frame: tb.Frame
    search_var: tk.StringVar
    order_var: tk.StringVar
    entry: tb.Entry
    search_button: tb.Button
    clear_button: tb.Button
    order_combobox: tb.Combobox


__all__ = ["SearchControls", "labeled_entry", "create_search_controls"]


def labeled_entry(parent: tk.Misc, label_text: str) -> tuple[ttk.Label, ttk.Entry]:
    """Return a label/entry pair for uniform forms."""
    label = ttk.Label(parent, text=label_text)
    entry = ttk.Entry(parent, width=50)
    return label, entry


def create_search_controls(
    parent: tk.Misc,
    *,
    order_choices: Iterable[str],
    default_order: str,
    on_search: Callable[[Any | None], Any] | None,
    on_clear: Callable[[], Any] | None,
    on_order_change: Callable[[], Any] | None,
    search_var: tk.StringVar | None = None,
    order_var: tk.StringVar | None = None,
    entry_width: int = 40,
) -> SearchControls:
    """Build the search + ordering toolbar."""
    frame = tb.Frame(parent)

    search_var = search_var or tk.StringVar(master=parent)
    order_var = order_var or tk.StringVar(master=parent, value=default_order)

    tb.Label(frame, text="Pesquisar:").pack(side="left", padx=5)

    def _trigger_search(event: Any | None = None) -> None:
        if on_search:
            on_search(event)

    entry = tb.Entry(frame, textvariable=search_var, width=entry_width)
    entry.pack(side="left", padx=5)
    entry.bind("<KeyRelease>", _trigger_search, add="+")

    search_button = tb.Button(frame, text="Buscar", command=_trigger_search)
    search_button.pack(side="left", padx=5)

    clear_button = tb.Button(
        frame,
        text="Limpar",
        command=lambda: on_clear() if on_clear else None,
    )
    clear_button.pack(side="left", padx=5)

    tb.Label(frame, text="Ordenar por:").pack(side="left", padx=5)

    def _order_changed(_event: Any | None = None) -> None:
        if on_order_change:
            on_order_change()

    order_combobox = tb.Combobox(
        frame,
        textvariable=order_var,
        values=list(order_choices),
        state="readonly",
        width=28,
    )
    order_combobox.pack(side="left", padx=5)
    order_combobox.bind("<<ComboboxSelected>>", _order_changed, add="+")

    return SearchControls(
        frame=frame,
        search_var=search_var,
        order_var=order_var,
        entry=entry,
        search_button=search_button,
        clear_button=clear_button,
        order_combobox=order_combobox,
    )
