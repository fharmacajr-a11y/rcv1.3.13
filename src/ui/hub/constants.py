# -*- coding: utf-8 -*-
"""Constantes de layout e rótulos do Hub."""

# RC: hub-notes-right (constantes de layout)
COL_LEFT_WIDTH = 180
NOTES_PANEL_MIN_WIDTH = 360
SPACER_MIN_WIDTH = 16
PAD_OUTER = 8
PAD_INNER = 6
MODULES_WEIGHT = 0      # Módulos: sem expansão (mantém tamanho fixo)
SPACER_WEIGHT = 1       # Centro: elástico (weight=1)
NOTES_WEIGHT = 0        # Notas à direita: sem expansão

HUB_TITLE = "Anotações Compartilhadas"
MODULES_TITLE = "Módulos"
NEW_NOTE_LABEL = "Nova anotação:"

__all__ = [
    "COL_LEFT_WIDTH",
    "NOTES_PANEL_MIN_WIDTH",
    "SPACER_MIN_WIDTH",
    "PAD_OUTER",
    "PAD_INNER",
    "MODULES_WEIGHT",
    "SPACER_WEIGHT",
    "NOTES_WEIGHT",
    "HUB_TITLE",
    "MODULES_TITLE",
    "NEW_NOTE_LABEL",
]
