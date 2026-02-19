from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Any

from src.modules.hub.constants import (
    MODULES_COL_MINSIZE,
    MODULES_WEIGHT,
    NOTES_PANEL_MIN_WIDTH,
    NOTES_WEIGHT,
    PAD_INNER,
    PAD_OUTER,
    SPACER_MIN_WIDTH,
    SPACER_WEIGHT,
)


@dataclass(frozen=True)
class HubLayoutConfig:
    """Configuração imutável do layout do HUB (3 colunas: módulos | centro | notas).

    Attributes:
        modules_col: Índice da coluna do painel de módulos (default: 0).
        center_col: Índice da coluna do centro/dashboard (default: 1).
        notes_col: Índice da coluna do painel de notas (default: 2).
        row_main: Índice da linha principal (default: 0).
        modules_weight: Weight da coluna de módulos (default: 0 - sem expansão).
        center_weight: Weight da coluna central (default: 1 - expansível).
        notes_weight: Weight da coluna de notas (default: 0 - sem expansão).
        modules_minsize: Largura mínima da coluna de módulos.
        center_minsize: Largura mínima da coluna central.
        notes_minsize: Largura mínima da coluna de notas.
        pad_outer: Padding externo dos painéis.
        pad_inner: Padding interno entre painéis.
    """

    modules_col: int = 0
    center_col: int = 1
    notes_col: int = 2
    row_main: int = 0
    modules_weight: int = MODULES_WEIGHT
    center_weight: int = SPACER_WEIGHT
    notes_weight: int = NOTES_WEIGHT
    modules_minsize: int = MODULES_COL_MINSIZE
    center_minsize: int = SPACER_MIN_WIDTH
    notes_minsize: int = NOTES_PANEL_MIN_WIDTH
    pad_outer: int = PAD_OUTER
    pad_inner: int = PAD_INNER


def apply_hub_layout(root: tk.Widget, config: HubLayoutConfig) -> None:
    """Aplica configuração de grid (colunas/linhas/weights) ao container do HUB.

    Args:
        root: Widget raiz onde o grid será configurado.
        config: Configuração de layout (HubLayoutConfig).
    """
    # Configurar colunas com weights e minsizes
    # Coluna 0 (módulos): usa MODULES_COL_MINSIZE para largura mínima
    root.grid_columnconfigure(
        config.modules_col,
        weight=config.modules_weight,
        minsize=MODULES_COL_MINSIZE,
    )
    root.grid_columnconfigure(
        config.center_col,
        weight=config.center_weight,
        minsize=config.center_minsize,
    )
    root.grid_columnconfigure(
        config.notes_col,
        weight=config.notes_weight,
        minsize=config.notes_minsize,
    )

    # Configurar linha principal (expansível)
    root.grid_rowconfigure(config.row_main, weight=1)


def apply_hub_notes_right(root: tk.Widget, widgets: dict[str, Any]) -> None:
    """
    Aplica layout 3 colunas (esquerda | espaço | direita) nos widgets fornecidos.
    'widgets' contém refs criadas em hub_screen.py. Aqui é só grid/weights.

    DEPRECATED: Use apply_hub_layout + HubLayoutConfig para novos códigos.
    Mantido para compatibilidade com código existente.
    """
    # Criar config padrão (usa MODULES_COL_MINSIZE para coluna 0)
    config = HubLayoutConfig()

    # RC: hub-notes-right (posicionamento)
    modules = widgets["modules_panel"]
    spacer = widgets["spacer"]
    notes = widgets["notes_panel"]

    # Módulos à esquerda (coluna 0) - DEIXAR COMO ESTÁ
    modules.grid(
        row=config.row_main,
        column=config.modules_col,
        sticky="nsew",
        padx=(config.pad_outer, config.pad_inner),
        pady=(config.pad_outer, config.pad_outer),
    )

    # Centro (coluna 1) - área elástica
    spacer.grid(
        row=config.row_main,
        column=config.center_col,
        sticky="nsew",
    )

    # Notas à direita (coluna 2)
    notes.grid(
        row=config.row_main,
        column=config.notes_col,
        sticky="nsew",
        padx=(config.pad_inner, config.pad_outer),
        pady=(config.pad_outer, config.pad_outer),
    )

    # RC: hub-notes-right (layout base - grid de 3 colunas)
    # Coluna 0 usa minsize=MODULES_COL_MINSIZE conforme HubLayoutConfig
    apply_hub_layout(root, config)
