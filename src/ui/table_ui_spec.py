# -*- coding: utf-8 -*-
"""Especificação de UI padronizada para tabelas (Treeview + CTkTableView).

Define constantes visuais consistentes aplicadas em todo o app.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableUISpec:
    """Especificação visual padronizada para tabelas."""

    # FONTE
    font_family: str = "Segoe UI"  # Font padrão do Windows 10+
    font_size: int = 10  # Tamanho legível
    heading_font_size: int = 10  # Header igual ao body (consistência)
    heading_font_weight: str = "bold"  # Header em negrito para destacar

    # DIMENSÕES
    row_height: int = 28  # Altura confortável (24 era muito apertado)
    header_height: int = 32  # Header um pouco mais alto
    cell_padding_x: int = 8  # Padding horizontal nas células
    cell_padding_y: int = 4  # Padding vertical nas células

    # BORDAS
    border_width: int = 0  # Sem borda (flat design)
    relief: str = "flat"  # Relief flat (moderno)

    # HEADING STYLE
    heading_relief: str = "flat"  # Header flat
    heading_border_width: int = 0  # Sem borda no header
    heading_anchor: str = "center"  # Headers centralizados por padrão

    # ZEBRA (linhas alternadas)
    zebra_enabled: bool = True  # Zebra ativo por padrão
    zebra_contrast: float = 0.03  # 3% de contraste (sutil mas visível)

    # SELEÇÃO
    selection_contrast: float = 1.0  # Seleção bem destacada
    selection_border: int = 0  # Sem borda na seleção

    # HOVER (quando aplicável)
    hover_enabled: bool = True  # Hover visual ativo
    hover_contrast: float = 0.05  # 5% de contraste no hover


# Instância singleton do spec
TABLE_UI_SPEC = TableUISpec()


def get_table_font(heading: bool = False) -> tuple[str, int, str]:
    """Retorna tripla (family, size, weight) para uso em tkinter.

    Args:
        heading: Se True, retorna fonte do heading (bold)

    Returns:
        Tupla (family, size, weight) ex: ("Segoe UI", 10, "bold")
    """
    spec = TABLE_UI_SPEC
    if heading:
        return (spec.font_family, spec.heading_font_size, spec.heading_font_weight)
    return (spec.font_family, spec.font_size, "normal")


def get_ctk_font_string(heading: bool = False) -> str:
    """Retorna string de fonte para CustomTkinter.

    Args:
        heading: Se True, retorna fonte do heading

    Returns:
        String formatada ex: "Segoe UI 10 bold"
    """
    family, size, weight = get_table_font(heading)
    return f"{family} {size} {weight}"


__all__ = ["TableUISpec", "TABLE_UI_SPEC", "get_table_font", "get_ctk_font_string"]
