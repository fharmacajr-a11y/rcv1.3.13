from __future__ import annotations

import tkinter as tk
from typing import Any

from src.ui.hub.constants import (
    COL_LEFT_WIDTH,
    MODULES_WEIGHT,
    NOTES_PANEL_MIN_WIDTH,
    NOTES_WEIGHT,
    PAD_INNER,
    PAD_OUTER,
    SPACER_MIN_WIDTH,
    SPACER_WEIGHT,
)


def apply_hub_notes_right(root: tk.Widget, widgets: dict[str, Any]) -> None:
    """
    Aplica layout 3 colunas (esquerda | espaço | direita) nos widgets fornecidos.
    'widgets' contém refs criadas em hub_screen.py. Aqui é só grid/weights.
    """
    # RC: hub-notes-right (posicionamento)
    modules = widgets["modules_panel"]
    spacer = widgets["spacer"]
    notes = widgets["notes_panel"]

    # Módulos à esquerda (coluna 0) - DEIXAR COMO ESTÁ
    modules.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=(PAD_OUTER, PAD_INNER),
        pady=(PAD_OUTER, PAD_OUTER),
    )

    # Centro (coluna 1) - área elástica
    spacer.grid(row=0, column=1, sticky="nsew")

    # Notas à direita (coluna 2)
    notes.grid(
        row=0,
        column=2,
        sticky="nsew",
        padx=(PAD_INNER, PAD_OUTER),
        pady=(PAD_OUTER, PAD_OUTER),
    )

    # RC: hub-notes-right (layout base - grid de 3 colunas)
    # Garante 3 colunas: apenas coluna 1 (centro) cresce
    root.grid_columnconfigure(0, weight=MODULES_WEIGHT, minsize=COL_LEFT_WIDTH)
    root.grid_columnconfigure(1, weight=SPACER_WEIGHT, minsize=SPACER_MIN_WIDTH)  # centro elástico
    root.grid_columnconfigure(2, weight=NOTES_WEIGHT, minsize=NOTES_PANEL_MIN_WIDTH)
    root.grid_rowconfigure(0, weight=1)
