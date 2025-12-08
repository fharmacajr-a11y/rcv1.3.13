# -*- coding: utf-8 -*-
# pyright: strict

"""Column Controls Layout Manager - MS-23.

Encapsula a lógica de cálculo de posicionamento dos controles de coluna
(labels/checkboxes) que ficam sobre o header da Treeview.

Responsabilidades:
- Calcular geometria das colunas (left, right, width) a partir de widths acumuladas.
- Computar placements (x, width) dos controles respeitando limites e centralizando.
- Manter a matemática de layout separada da manipulação Tk (place_configure).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ColumnGeometry:
    """Geometria de uma coluna: posições horizontais e largura."""

    left: int
    right: int
    width: int


@dataclass(frozen=True)
class ControlPlacement:
    """Posicionamento horizontal de um controle de coluna."""

    x: int
    width: int


class ColumnControlsLayout:
    """Gerencia cálculo de layout dos controles de coluna (headless)."""

    def compute_column_geometries(
        self,
        col_order: Sequence[str],
        column_widths: Mapping[str, int],
    ) -> dict[str, ColumnGeometry]:
        """Calcula geometria de cada coluna a partir das larguras.

        Args:
            col_order: Ordem das colunas.
            column_widths: Largura de cada coluna (mapeada por ID).

        Returns:
            Dicionário mapeando col_id → ColumnGeometry.
        """
        geoms: dict[str, ColumnGeometry] = {}
        cumulative_x = 0

        for col in col_order:
            width = column_widths.get(col, 0)
            left = cumulative_x
            right = cumulative_x + width
            geoms[col] = ColumnGeometry(left=left, right=right, width=width)
            cumulative_x += width

        return geoms

    def compute_control_placements(
        self,
        geoms: Mapping[str, ColumnGeometry],
        required_widths: Mapping[str, int],
        min_width: int = 70,
        max_width: int = 160,
        padding: int = 2,
    ) -> dict[str, ControlPlacement]:
        """Calcula posicionamento dos controles dentro de cada coluna.

        Args:
            geoms: Geometria das colunas (de compute_column_geometries).
            required_widths: Largura necessária para cada controle (label + check + margem).
            min_width: Largura mínima do controle.
            max_width: Largura máxima do controle.
            padding: Padding lateral dentro da coluna.

        Returns:
            Dicionário mapeando col_id → ControlPlacement.
        """
        placements: dict[str, ControlPlacement] = {}

        for col, geom in geoms.items():
            req_w = required_widths.get(col, 0)

            # limite por coluna (clamp entre min_width e max_width, respeitando espaço disponível)
            available = geom.width - (2 * padding)
            gw = max(min_width, min(max_width, min(req_w, available)))

            # centraliza dentro da coluna
            gx = geom.left + (geom.width - gw) // 2

            # não deixa vazar a borda esquerda
            if gx < geom.left + padding:
                gx = geom.left + padding

            # não deixa vazar a borda direita
            if gx + gw > geom.right - padding:
                gx = max(geom.left + padding, geom.right - gw - padding)

            placements[col] = ControlPlacement(x=gx, width=gw)

        return placements
