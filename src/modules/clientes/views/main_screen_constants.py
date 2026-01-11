# -*- coding: utf-8 -*-
"""
Constantes de layout e UI para a tela principal de Clientes.

Este módulo centraliza todas as constantes de layout, dimensões, paddings e
configurações visuais da main screen de clientes, evitando duplicação e
NameErrors em tempo de execução.
"""

# ============================================================================
# CONFIGURAÇÕES DE TREEVIEW MODERNIZADA
# ============================================================================

# Altura das linhas do Treeview (aumentada para melhor legibilidade)
TREEVIEW_ROW_HEIGHT = 32

# Fonte da Treeview (mais legível e moderna)
TREEVIEW_FONT_FAMILY = "Segoe UI"
TREEVIEW_FONT_SIZE = 10
TREEVIEW_HEADING_FONT_SIZE = 10

# Cores de zebra striping (linhas alternadas)
ZEBRA_COLOR_ODD = "#ffffff"  # Linhas ímpares - branco
ZEBRA_COLOR_EVEN = "#f8f9fa"  # Linhas pares - cinza muito claro

# ============================================================================
# CORES DE STATUS (Tags do Treeview)
# ============================================================================

# Mapeamento de status para cores
STATUS_COLORS = {
    # Status de novos/urgentes - Verde
    "Novo cliente": {"foreground": "#198754", "background": "#d1e7dd"},
    "Follow-up hoje": {"foreground": "#198754", "background": "#d1e7dd"},
    "Follow-up amanhã": {"foreground": "#0d6efd", "background": "#cfe2ff"},
    # Status pendentes - Cinza/Laranja
    "Sem resposta": {"foreground": "#6c757d", "background": "#e9ecef"},
    "Aguardando documento": {"foreground": "#fd7e14", "background": "#fff3cd"},
    "Aguardando pagamento": {"foreground": "#fd7e14", "background": "#fff3cd"},
    # Status de análise - Azul
    "Análise da Caixa": {"foreground": "#0d6efd", "background": "#cfe2ff"},
    "Análise do Ministério": {"foreground": "#0d6efd", "background": "#cfe2ff"},
    "Em cadastro": {"foreground": "#0dcaf0", "background": "#cff4fc"},
    "Cadastro pendente": {"foreground": "#0dcaf0", "background": "#cff4fc"},
    # Status finalizados - Verde escuro
    "Finalizado": {"foreground": "#146c43", "background": "#badbcc"},
}

# Cor padrão para status não mapeados
STATUS_COLOR_DEFAULT = {"foreground": "#495057", "background": "#f8f9fa"}

# ============================================================================
# ESPAÇAMENTO E WHITESPACE
# ============================================================================

# Espaçamento entre toolbar e tabela (respiro visual)
TOOLBAR_TABLE_SPACING = 15

# Padding do container da lista de clientes
CLIENT_LIST_PADX = 12
CLIENT_LIST_PADY = 8

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
PICK_MODE_BANNER_TEXT = (
    "🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter"
)
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
    # Configurações de Treeview
    "TREEVIEW_ROW_HEIGHT",
    "TREEVIEW_FONT_FAMILY",
    "TREEVIEW_FONT_SIZE",
    "TREEVIEW_HEADING_FONT_SIZE",
    "ZEBRA_COLOR_ODD",
    "ZEBRA_COLOR_EVEN",
    # Cores de status
    "STATUS_COLORS",
    "STATUS_COLOR_DEFAULT",
    # Espaçamento
    "TOOLBAR_TABLE_SPACING",
    "CLIENT_LIST_PADX",
    "CLIENT_LIST_PADY",
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
