# -*- coding: utf-8 -*-
"""Constantes de layout e rótulos do Hub."""

# RC: hub-notes-right (constantes de layout)
COL_LEFT_WIDTH = 180
NOTES_PANEL_MIN_WIDTH = 360
SPACER_MIN_WIDTH = 16
PAD_OUTER = 8
PAD_INNER = 6
MODULES_WEIGHT = 0  # Módulos: sem expansão (mantém tamanho fixo)
SPACER_WEIGHT = 1  # Centro: elástico (weight=1)
NOTES_WEIGHT = 0  # Notas à direita: sem expansão

HUB_TITLE = "Anotações Compartilhadas"
MODULES_TITLE = "Módulos"
NEW_NOTE_LABEL = "Nova anotação:"

# Estilos de botões da coluna "Módulos" do Hub
HUB_BTN_STYLE_CLIENTES = "info"  # azul claro
HUB_BTN_STYLE_AUDITORIA = "info"  # azul claro
HUB_BTN_STYLE_FLUXO_CAIXA = "secondary"  # cinza

# Largura mínima da coluna de módulos (para caber 2 botões lado a lado)
MODULES_COL_MINSIZE = 260

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
    "HUB_BTN_STYLE_CLIENTES",
    "HUB_BTN_STYLE_FLUXO_CAIXA",
    "MODULES_COL_MINSIZE",
]
