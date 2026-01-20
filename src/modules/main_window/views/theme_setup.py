# -*- coding: utf-8 -*-
"""Configuração de tema customizado para garantir cores específicas.

⚠️ DEPRECATED: ttkbootstrap foi REMOVIDO do projeto (18/01/2026).
Este módulo é mantido apenas para compatibilidade com código legado.
Funcionalidade de tema customizado agora é no-op.

NOVO CÓDIGO: Use src/ui/theme_manager.py (CustomTkinter).
"""

import logging
from typing import Any

log = logging.getLogger(__name__)

__all__ = ["ensure_info_color"]


def ensure_info_color(style: Any = None, info_hex: str = "#3498DB") -> None:
    """No-op mantido para compatibilidade.

    ttkbootstrap foi removido do projeto. Esta função não faz nada.

    Args:
        style: Ignorado
        info_hex: Ignorado
    """
    log.debug("ensure_info_color chamado mas ttkbootstrap foi removido (no-op)")
