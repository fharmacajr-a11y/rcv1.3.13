# -*- coding: utf-8 -*-
"""Módulo de compatibilidade legado (DEPRECATED).

MICROFASE 31: Este módulo foi REMOVIDO completamente.
Não há mais widgets legados no projeto (ZERO em runtime).

Mantido apenas como stub vazio para evitar quebrar imports legados.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

__all__: list[str] = []


# Stub funções legadas (não fazem nada)
def apply_ttk_treeview_theme(*args: Any, **kwargs: Any) -> None:
    """Stub legado - não faz nada (widgets legados removidos)."""
    log.warning("apply_ttk_treeview_theme chamado mas widgets legados foram removidos (MICROFASE 31)")


def apply_ttk_widgets_theme(*args: Any, **kwargs: Any) -> None:
    """Stub legado - não faz nada (widgets legados removidos)."""
    log.warning("apply_ttk_widgets_theme chamado mas widgets legados foram removidos (MICROFASE 31)")
