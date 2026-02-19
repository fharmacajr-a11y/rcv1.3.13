# -*- coding: utf-8 -*-
"""Tokens de UI padronizados para CustomTkinter.

MICROFASE 35: Define cores e espaçamentos consistentes para toda a aplicação.

Conceito-chave do CustomTkinter:
- fg_color: cor de preenchimento do widget
- bg_color: cor que aparece ATRÁS dos cantos arredondados (corner_radius > 0)
  → Sempre defina bg_color = cor do pai onde o widget está "assentado"

Uso:
    from src.ui.ui_tokens import APP_BG, SURFACE, BORDER, SEP

    # Frame com cantos arredondados sobre fundo APP_BG
    card = ctk.CTkFrame(
        parent,
        fg_color=SURFACE,
        bg_color=APP_BG,  # IMPORTANTE: evita "vazamento" nos cantos
        corner_radius=10,
        border_width=1,
        border_color=BORDER,
    )
"""

from __future__ import annotations

# =============================================================================
# CORES BASE (tupla: light, dark)
# =============================================================================

# Fundo geral da aplicação - BRANCO no light (destaca cards cinza)
APP_BG = ("#ffffff", "#0b0b0b")

# Superfície interna (conteúdo branco/escuro)
SURFACE = ("#ffffff", "#141414")

# Superfície mais escura para cards específicos
SURFACE_DARK = ("#dadada", "#121212")

# Superfície interna (textboxes/listas) - branco no light para contraste
INNER_SURFACE = ("#ffffff", "#1a1a1a")

# Variação leve de superfície (para hover ou destaque sutil)
SURFACE_2 = ("#e8e8e8", "#1a1a1a")

# Cor de borda visível - suave
BORDER = ("#d6d6d6", "#2a2a2a")

# Separadores finos e claros
SEP = ("#dcdcdc", "#333333")

# Texto principal
TEXT_PRIMARY = ("#111111", "#f2f2f2")

# Texto secundário/muted
TEXT_MUTED = ("#555555", "#bdbdbd")

# =============================================================================
# CORES DE DESTAQUE (KPI cards)
# =============================================================================

# Azul (Clientes)
KPI_BLUE = ("#3b82f6", "#2563eb")
KPI_BLUE_HOVER = ("#2563eb", "#1d4ed8")

# Vermelho (Pendências)
KPI_RED = ("#ef4444", "#dc2626")
KPI_RED_HOVER = ("#dc2626", "#b91c1c")

# Laranja (Tarefas)
KPI_ORANGE = ("#f97316", "#ea580c")
KPI_ORANGE_HOVER = ("#ea580c", "#c2410c")

# Verde (Sucesso/OK)
KPI_GREEN = ("#22c55e", "#16a34a")

# Amarelo (Warning)
KPI_YELLOW = ("#eab308", "#ca8a04")

# Cinza (Desativado)
KPI_GRAY = ("#9ca3af", "#6b7280")

# =============================================================================
# TIPOGRAFIA (fontes CTk)
# =============================================================================

# Fontes padronizadas para uniformidade
BODY_FONT = ("Segoe UI", 11)
TITLE_FONT = ("Segoe UI", 12, "bold")

# Título principal
FONT_TITLE = ("Segoe UI", 13, "bold")

# Títulos de seção
FONT_SECTION = ("Segoe UI", 12, "bold")

# Corpo de texto
FONT_BODY = ("Segoe UI", 11)

# Texto pequeno
FONT_BODY_SM = ("Segoe UI", 10)

# KPI cards - valor grande
FONT_KPI_VALUE = ("Segoe UI", 26, "bold")

# KPI cards - legenda
FONT_KPI_LABEL = ("Segoe UI", 11)

# =============================================================================
# ESPAÇAMENTOS
# =============================================================================

# Corner radius padrão para cards
CARD_RADIUS = 12

# Corner radius para KPI cards
KPI_RADIUS = 12

# Border width padrão
BORDER_WIDTH = 1

# Padding interno de cards
CARD_PADDING = 12

# Padding entre seções
SECTION_GAP = 16

# =============================================================================
# BOTÕES (padronização de tamanho e estilo)
# =============================================================================

# Largura padrão dos botões de ação (ajustada para caber "Visualizador PDF")
BUTTON_W = 140

# Altura padrão dos botões de ação
BUTTON_H = 32

# Corner radius dos botões (menor que cards)
BUTTON_RADIUS = 10

# Border spacing interno dos botões
BUTTON_BORDER_SPACING = 2

# --- Variantes compactas (widgets densos: DatePicker, Autocomplete, toolbar densa) ---

# Botão pequeno (cabe em barras compactas)
BUTTON_SM_W = 110
BUTTON_SM_H = 28

# Botão ícone (quadrado, ex.: ⟳, 🔔)
BUTTON_ICON = 32
