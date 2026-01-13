# -*- coding: utf-8 -*-
"""Configuração de tema customizado para garantir cores específicas."""

import logging
from typing import Any

import ttkbootstrap as tb
from ttkbootstrap.style import Colors, ThemeDefinition

log = logging.getLogger(__name__)

__all__ = ["ensure_info_color"]


def ensure_info_color(style: tb.Style, info_hex: str = "#3498DB") -> None:
    """Garante que a cor 'info' do tema atual seja info_hex criando um tema derivado.

    Feito pelo caminho oficial: ThemeDefinition + register_theme + theme_use.

    Args:
        style: Instância do Style do ttkbootstrap
        info_hex: Cor hexadecimal desejada para 'info' (padrão: #3498DB)
    """
    try:
        current_theme = style.theme.name
        derived_theme = f"{current_theme}_rc_info"

        # Se tema derivado já existe, apenas aplicar
        if derived_theme in style.theme_names():
            style.theme_use(derived_theme)
            log.debug("Tema derivado '%s' já existe, aplicado", derived_theme)
            return

        # Monta dict completo usando Colors.label_iter() (inclui 'active')
        colors: dict[str, Any] = {label: style.colors.get(label) for label in Colors.label_iter()}

        # Trocar apenas a cor 'info'
        colors["info"] = info_hex

        # Fallback robusto: garantir que 'active' existe
        if not colors.get("active"):
            colors["active"] = colors.get("info", info_hex)

        theme_def = ThemeDefinition(
            name=derived_theme,
            colors=colors,
            themetype=style.theme.type,
        )
        style.register_theme(theme_def)
        style.theme_use(derived_theme)
        log.info("Tema customizado '%s' criado com info=%s", derived_theme, info_hex)

    except Exception as exc:
        log.warning("Falha ao configurar tema customizado: %s", exc, exc_info=True)
