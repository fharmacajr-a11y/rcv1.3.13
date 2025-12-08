# -*- coding: utf-8 -*-
"""
Constantes de layout e UI para a tela principal de Clientes.

Este módulo centraliza todas as constantes de layout, dimensões, paddings e
configurações visuais da main screen de clientes, evitando duplicação e
NameErrors em tempo de execução.
"""

# ============================================================================
# DIMENSÕES DE CONTROLES
# ============================================================================

# Altura da barra de controles de colunas (acima do treeview)
HEADER_CTRL_H = 26

# Largura padrão do grupo de controle de coluna
COLUMN_CONTROL_WIDTH = 120

# Offset Y para posicionar os controles de coluna
COLUMN_CONTROL_Y_OFFSET = 2

# Padding interno dos controles de coluna (checkbox + label)
COLUMN_CONTROL_PADDING = 4

# ============================================================================
# DIMENSÕES DE COLUNAS DA TREEVIEW
# ============================================================================

# Larguras mínimas e máximas para colunas da treeview
COLUMN_MIN_WIDTH = 70
COLUMN_MAX_WIDTH = 160

# Padding entre colunas
COLUMN_PADDING = 2

# Largura padrão do checkbox nos controles de coluna
COLUMN_CHECKBOX_WIDTH = 12

# ============================================================================
# FONTES
# ============================================================================

# Fonte do banner de pick mode
PICK_MODE_BANNER_FONT = ("", 10, "bold")

# ============================================================================
# TEXTOS DO MODO SELEÇÃO (PICK MODE)
# ============================================================================

# Mantém sincronia com main_screen.py e main_screen_ui_builder.py
PICK_MODE_BANNER_TEXT = "🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter"
PICK_MODE_CANCEL_TEXT = "✖ Cancelar"
PICK_MODE_SELECT_TEXT = "✓ Selecionar"

# ============================================================================
# PADDINGS E ESPAÇAMENTOS
# ============================================================================

# Padding horizontal padrão da toolbar
TOOLBAR_PADX = 10

# Padding vertical padrão da toolbar
TOOLBAR_PADY = 10

# Padding do separador de colunas
SEPARATOR_PADX = 10
SEPARATOR_PADY_TOP = 6
SEPARATOR_PADY_BOTTOM = 4

# ============================================================================
# ORDEM DE COLUNAS
# ============================================================================

# Ordem padrão das colunas na treeview
DEFAULT_COLUMN_ORDER = (
    "ID",
    "Razao Social",
    "CNPJ",
    "Nome",
    "WhatsApp",
    "Observacoes",
    "Status",
    "Ultima Alteracao",
)

__all__ = [
    # Dimensões de controles
    "HEADER_CTRL_H",
    "COLUMN_CONTROL_WIDTH",
    "COLUMN_CONTROL_Y_OFFSET",
    "COLUMN_CONTROL_PADDING",
    # Dimensões de colunas
    "COLUMN_MIN_WIDTH",
    "COLUMN_MAX_WIDTH",
    "COLUMN_PADDING",
    "COLUMN_CHECKBOX_WIDTH",
    # Fontes
    "PICK_MODE_BANNER_FONT",
    # Textos do modo seleção
    "PICK_MODE_BANNER_TEXT",
    "PICK_MODE_CANCEL_TEXT",
    "PICK_MODE_SELECT_TEXT",
    # Paddings
    "TOOLBAR_PADX",
    "TOOLBAR_PADY",
    "SEPARATOR_PADX",
    "SEPARATOR_PADY_TOP",
    "SEPARATOR_PADY_BOTTOM",
    # Ordem de colunas
    "DEFAULT_COLUMN_ORDER",
]
