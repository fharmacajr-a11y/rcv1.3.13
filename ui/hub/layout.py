from __future__ import annotations

from typing import Any

import tkinter as tk

from ui.hub.constants import (
    COL_LEFT_WIDTH,
    NOTES_PANEL_MIN_WIDTH,
    PAD_INNER,
    PAD_OUTER,
    SPACER_MIN_WIDTH,
    MODULES_WEIGHT,
    SPACER_WEIGHT,
    NOTES_WEIGHT,
)


def apply_hub_notes_right(root: tk.Widget, widgets: dict[str, Any]) -> None:
    """
    Aplica layout 3 colunas (esquerda | espaço | direita) nos widgets fornecidos.
    'widgets' contém refs criadas em hub_screen.py. Aqui é só grid/weights.
    """
    modules = widgets["modules_panel"]
    spacer = widgets["spacer"]
    notes = widgets["notes_panel"]

    modules.grid(row=0, column=0, sticky="nsew", padx=(PAD_OUTER, PAD_INNER), pady=(PAD_OUTER, PAD_OUTER))
    spacer.grid(row=0, column=1, sticky="nsew")
    notes.grid(row=0, column=2, sticky="nsew", padx=(PAD_INNER, PAD_OUTER), pady=(PAD_OUTER, PAD_OUTER))

    root.grid_columnconfigure(0, weight=MODULES_WEIGHT, minsize=COL_LEFT_WIDTH)
    root.grid_columnconfigure(1, weight=SPACER_WEIGHT, minsize=SPACER_MIN_WIDTH)
    root.grid_columnconfigure(2, weight=NOTES_WEIGHT, minsize=NOTES_PANEL_MIN_WIDTH)
    root.grid_rowconfigure(0, weight=1)
