# -*- coding: utf-8 -*-
"""Constantes para o dashboard center do Hub.

ORG-005: Extraído de dashboard_center.py para reduzir complexidade.
Contém constantes de layout, fontes, e mensagens padrão.
"""

from __future__ import annotations

from typing import Any

# ============================================================================
# LAYOUT E PADDING
# ============================================================================

CARD_PAD_X = 10
CARD_PAD_Y = 8

# ============================================================================
# FONTES
# ============================================================================

CARD_VALUE_FONT: Any = ("Segoe UI", 24, "bold")
CARD_LABEL_FONT: tuple[str, int] = ("Segoe UI", 10)
SECTION_TITLE_FONT: Any = ("Segoe UI", 11, "bold")
SECTION_ITEM_FONT: tuple[str, int] = ("Segoe UI", 10)
SECTION_DAY_HEADER_FONT: Any = ("Segoe UI", 9, "bold")

# ============================================================================
# LIMITES DE EXIBIÇÃO
# ============================================================================

# Limite de atividades exibidas no dashboard
MAX_ACTIVITY_ITEMS_DASHBOARD = 5

# ============================================================================
# MENSAGENS PADRÃO
# ============================================================================

MSG_NO_HOT_ITEMS = "Nenhum alerta crítico por enquanto 😀"
MSG_NO_UPCOMING = "Nenhuma obrigação pendente nos próximos dias."
