# -*- coding: utf-8 -*-
"""
Constantes e configurações do File Browser.

Este módulo centraliza valores constantes usados pelo file browser,
facilitando ajustes futuros e manutenção.
"""

# Espaçamento e padding da UI
UI_GAP = 6
UI_PADX = 8
UI_PADY = 6

# Status de pastas (sistema de marcação)
FOLDER_STATUS_NEUTRAL = "neutral"
FOLDER_STATUS_READY = "ready"
FOLDER_STATUS_NOTREADY = "notready"

STATUS_GLYPHS = {
    FOLDER_STATUS_NEUTRAL: "•",
    FOLDER_STATUS_READY: "✓",
    FOLDER_STATUS_NOTREADY: "✗",
}

# Tags da Treeview
PLACEHOLDER_TAG = "async-placeholder"
EMPTY_TAG = "async-empty"

# Paginação (PERF-003)
DEFAULT_PAGE_SIZE = 200  # Número de itens carregados por página
