# -*- coding: utf-8 -*-
"""Factory centralizado para criação de botões padronizados com CustomTkinter.

OBJETIVO: Garantir tamanho, estilo e comportamento visual consistente em todos os
botões CTkButton do app, facilitando manutenção e garantindo UX uniforme.

USO:
    from src.ui.widgets.button_factory import make_btn, make_btn_sm, make_btn_icon

    btn = make_btn(
        master=parent,
        text="Meu Botão",
        command=callback,
        fg_color="#3b82f6",  # opcional: substitui cor padrão
    )
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    BUTTON_W,
    BUTTON_H,
    BUTTON_RADIUS,
    BUTTON_BORDER_SPACING,
    BUTTON_SM_W,
    BUTTON_SM_H,
    BUTTON_ICON,
    BTN_PRIMARY,
    BTN_PRIMARY_HOVER,
    BTN_DANGER,
    BTN_DANGER_HOVER,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    BTN_WARNING,
    BTN_WARNING_HOVER,
    BTN_SUCCESS,
    BTN_SUCCESS_HOVER,
    BTN_TEXT_ON_COLOR,
)


def make_btn(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Cria um CTkButton padronizado com tamanho e estilo consistentes.

    Args:
        master: Widget pai onde o botão será criado
        text: Texto do botão
        command: Callback quando botão é clicado
        **kwargs: Argumentos adicionais para customização (fg_color, hover_color, etc)
                  Estes sobrescrevem os padrões se fornecidos.

    Returns:
        Instância de ctk.CTkButton configurada com os tokens globais
    """
    defaults = {
        "width": BUTTON_W,
        "height": BUTTON_H,
        "corner_radius": BUTTON_RADIUS,
        "border_spacing": BUTTON_BORDER_SPACING,
    }
    config = {**defaults, **kwargs}
    return ctk.CTkButton(
        master=master,
        text=text,
        command=command,
        **config,
    )


def make_btn_sm(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Cria um CTkButton *pequeno* para barras/widgets compactos.

    Usa BUTTON_SM_W / BUTTON_SM_H. Ideal para toolbars densas onde o
    padrão de 140 px de largura não cabe.
    """
    defaults = {
        "width": BUTTON_SM_W,
        "height": BUTTON_SM_H,
        "corner_radius": BUTTON_RADIUS,
        "border_spacing": BUTTON_BORDER_SPACING,
    }
    config = {**defaults, **kwargs}
    return ctk.CTkButton(
        master=master,
        text=text,
        command=command,
        **config,
    )


def make_btn_icon(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Cria um CTkButton quadrado para ícones (⟳, 🔔, +, − etc.).

    Usa BUTTON_ICON × BUTTON_ICON (32 × 32 por padrão).
    """
    defaults = {
        "width": BUTTON_ICON,
        "height": BUTTON_ICON,
        "corner_radius": BUTTON_RADIUS,
        "border_spacing": BUTTON_BORDER_SPACING,
    }
    config = {**defaults, **kwargs}
    return ctk.CTkButton(
        master=master,
        text=text,
        command=command,
        **config,
    )


# =========================================================================
# Wrappers semânticos — delegam para make_btn com tokens de cor
# =========================================================================


def make_btn_primary(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Botão primário (azul) — ação principal / confirmação."""
    return make_btn(
        master,
        text,
        command,
        fg_color=BTN_PRIMARY,
        hover_color=BTN_PRIMARY_HOVER,
        text_color=BTN_TEXT_ON_COLOR,
        **kwargs,
    )


def make_btn_danger(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Botão de perigo (vermelho) — ação destrutiva."""
    return make_btn(
        master,
        text,
        command,
        fg_color=BTN_DANGER,
        hover_color=BTN_DANGER_HOVER,
        text_color=BTN_TEXT_ON_COLOR,
        **kwargs,
    )


def make_btn_secondary(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Botão secundário (cinza) — cancelar / dispensar."""
    return make_btn(
        master,
        text,
        command,
        fg_color=BTN_SECONDARY,
        hover_color=BTN_SECONDARY_HOVER,
        text_color=BTN_TEXT_ON_COLOR,
        **kwargs,
    )


def make_btn_warning(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Botão de aviso (âmbar) — requer atenção."""
    return make_btn(
        master,
        text,
        command,
        fg_color=BTN_WARNING,
        hover_color=BTN_WARNING_HOVER,
        text_color=BTN_TEXT_ON_COLOR,
        **kwargs,
    )


def make_btn_success(
    master: tk.Misc,
    text: str,
    command: Optional[Callable[[], None]] = None,
    **kwargs: Any,
) -> Any:
    """Botão de sucesso (verde) — confirmação positiva."""
    return make_btn(
        master,
        text,
        command,
        fg_color=BTN_SUCCESS,
        hover_color=BTN_SUCCESS_HOVER,
        text_color=BTN_TEXT_ON_COLOR,
        **kwargs,
    )
