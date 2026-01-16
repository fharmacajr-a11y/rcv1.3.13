# -*- coding: utf-8 -*-
"""UI Builders CustomTkinter para formulário de clientes.

Este módulo contém funções helper para construir widgets CustomTkinter
padronizados do formulário de clientes, mantendo visual moderno e consistente.

Refatoração: MICROFASE-5 (Forms com CustomTkinter)
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Any, Callable

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

if TYPE_CHECKING:
    pass  # ctk já importado via src.ui.ctk_config

logger = logging.getLogger(__name__)


# =============================================================================
# Builders de Campos de Entrada CTk
# =============================================================================


def create_labeled_entry_ctk(
    parent: tk.Widget,
    label_text: str,
    row_idx: int,
    column: int = 0,
    padx: int = 6,
    pady_label: tuple[int, int] = (5, 0),
    pady_entry: tuple[int, int] = (0, 5),
    fg_color: tuple[str, str] | str | None = None,
    text_color: tuple[str, str] | str | None = None,
    border_color: tuple[str, str] | str | None = None,
) -> tuple[ctk.CTkLabel, ctk.CTkEntry, int]:
    """Cria um par CTkLabel+CTkEntry padronizado em duas linhas consecutivas.

    Args:
        parent: Widget pai onde criar os elementos.
        label_text: Texto do label.
        row_idx: Índice da linha inicial (label).
        column: Coluna onde criar (padrão: 0).
        padx: Padding horizontal (padrão: 6).
        pady_label: Padding vertical do label (padrão: (5, 0)).
        pady_entry: Padding vertical do entry (padrão: (0, 5)).
        fg_color: Cor de fundo do entry (tupla light/dark ou string).
        text_color: Cor do texto (tupla light/dark ou string).
        border_color: Cor da borda (tupla light/dark ou string).

    Returns:
        Tupla (label, entry, próximo_row_idx).
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        raise RuntimeError("CustomTkinter não disponível")

    # Label
    label = ctk.CTkLabel(parent, text=label_text, anchor="w")
    label.grid(row=row_idx, column=column, sticky="w", padx=padx, pady=pady_label)

    # Entry com cores opcionais
    entry_kwargs: dict[str, Any] = {}
    if fg_color is not None:
        entry_kwargs["fg_color"] = fg_color
    if text_color is not None:
        entry_kwargs["text_color"] = text_color
    if border_color is not None:
        entry_kwargs["border_color"] = border_color

    entry = ctk.CTkEntry(parent, **entry_kwargs)
    entry.grid(row=row_idx + 1, column=column, sticky="ew", padx=padx, pady=pady_entry)

    return label, entry, row_idx + 2


def create_labeled_textbox_ctk(
    parent: tk.Widget,
    label_text: str,
    row_idx: int,
    column: int = 0,
    width: int = 400,
    height: int = 120,
    padx: int = 6,
    pady_label: tuple[int, int] = (0, 0),
    pady_text: tuple[int, int] = (0, 5),
    fg_color: tuple[str, str] | str | None = None,
    text_color: tuple[str, str] | str | None = None,
    border_color: tuple[str, str] | str | None = None,
) -> tuple[ctk.CTkLabel, ctk.CTkTextbox, int, int]:
    """Cria um par CTkLabel+CTkTextbox padronizado em duas linhas consecutivas.

    Args:
        parent: Widget pai onde criar os elementos.
        label_text: Texto do label.
        row_idx: Índice da linha inicial (label).
        column: Coluna onde criar (padrão: 0).
        width: Largura do Textbox (padrão: 400).
        height: Altura do Textbox (padrão: 120).
        padx: Padding horizontal (padrão: 6).
        pady_label: Padding vertical do label (padrão: (0, 0)).
        pady_text: Padding vertical do Textbox (padrão: (0, 5)).
        fg_color: Cor de fundo do textbox (tupla light/dark ou string).
        text_color: Cor do texto (tupla light/dark ou string).
        border_color: Cor da borda (tupla light/dark ou string).

    Returns:
        Tupla (label, textbox_widget, row_do_textbox, próximo_row_idx).
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        raise RuntimeError("CustomTkinter não disponível")

    # Label
    label = ctk.CTkLabel(parent, text=label_text, anchor="w")
    label.grid(row=row_idx, column=column, sticky="w", padx=padx, pady=pady_label)

    # Textbox com cores opcionais
    textbox_kwargs: dict[str, Any] = {
        "width": width,
        "height": height,
    }
    if fg_color is not None:
        textbox_kwargs["fg_color"] = fg_color
    if text_color is not None:
        textbox_kwargs["text_color"] = text_color
    if border_color is not None:
        textbox_kwargs["border_color"] = border_color

    textbox = ctk.CTkTextbox(parent, **textbox_kwargs)
    text_row = row_idx + 1
    textbox.grid(row=text_row, column=column, padx=padx, pady=pady_text, sticky="nsew")

    return label, textbox, text_row, row_idx + 2


def create_status_dropdown_ctk(
    parent: tk.Widget,
    label_text: str,
    choices: list[str],
    row_idx: int,
    column: int = 0,
    padx: int = 6,
    pady_label: tuple[int, int] = (0, 0),
    pady_combo: tuple[int, int] = (0, 5),
    fg_color: tuple[str, str] | str | None = None,
    button_color: tuple[str, str] | str | None = None,
    button_hover_color: tuple[str, str] | str | None = None,
    dropdown_fg_color: tuple[str, str] | str | None = None,
    text_color: tuple[str, str] | str | None = None,
    variable: tk.StringVar | None = None,
    command: Callable[[str], None] | None = None,
) -> tuple[ctk.CTkLabel, ctk.CTkOptionMenu, int]:
    """Cria um par CTkLabel+CTkOptionMenu para dropdown de status.

    Args:
        parent: Widget pai onde criar os elementos.
        label_text: Texto do label.
        choices: Lista de opções para o dropdown.
        row_idx: Índice da linha inicial (label).
        column: Coluna onde criar (padrão: 0).
        padx: Padding horizontal (padrão: 6).
        pady_label: Padding vertical do label (padrão: (0, 0)).
        pady_combo: Padding vertical do dropdown (padrão: (0, 5)).
        fg_color: Cor de fundo do botão (tupla light/dark ou string).
        button_color: Cor do botão (tupla light/dark ou string).
        button_hover_color: Cor do hover (tupla light/dark ou string).
        dropdown_fg_color: Cor de fundo do dropdown (tupla light/dark ou string).
        text_color: Cor do texto (tupla light/dark ou string).
        variable: StringVar para binding (opcional).
        command: Callback quando valor muda (opcional).

    Returns:
        Tupla (label, option_menu, próximo_row_idx).
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        raise RuntimeError("CustomTkinter não disponível")

    # Label
    label = ctk.CTkLabel(parent, text=label_text, anchor="w")
    label.grid(row=row_idx, column=column, sticky="w", padx=padx, pady=pady_label)

    # OptionMenu com cores opcionais
    optionmenu_kwargs: dict[str, Any] = {
        "values": choices,
    }
    if variable is not None:
        optionmenu_kwargs["variable"] = variable
    if command is not None:
        optionmenu_kwargs["command"] = command
    if fg_color is not None:
        optionmenu_kwargs["fg_color"] = fg_color
    if button_color is not None:
        optionmenu_kwargs["button_color"] = button_color
    if button_hover_color is not None:
        optionmenu_kwargs["button_hover_color"] = button_hover_color
    if dropdown_fg_color is not None:
        optionmenu_kwargs["dropdown_fg_color"] = dropdown_fg_color
    if text_color is not None:
        optionmenu_kwargs["text_color"] = text_color

    option_menu = ctk.CTkOptionMenu(parent, **optionmenu_kwargs)
    option_menu.grid(row=row_idx + 1, column=column, sticky="ew", padx=padx, pady=pady_combo)

    return label, option_menu, row_idx + 2


def create_separator_ctk(
    parent: tk.Widget,
    row_idx: int,
    column: int = 0,
    columnspan: int = 1,
    fg_color: tuple[str, str] | str | None = None,
    height: int = 1,
) -> tuple[ctk.CTkFrame, int]:
    """Cria um separador horizontal usando CTkFrame.

    Args:
        parent: Widget pai onde criar.
        row_idx: Índice da linha.
        column: Coluna onde criar (padrão: 0).
        columnspan: Número de colunas para expandir (padrão: 1).
        fg_color: Cor do separador (tupla light/dark ou string).
        height: Altura do separador em pixels (padrão: 1).

    Returns:
        Tupla (separator_frame, próximo_row_idx).
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        raise RuntimeError("CustomTkinter não disponível")

    sep_kwargs: dict[str, Any] = {
        "height": height,
    }
    if fg_color is not None:
        sep_kwargs["fg_color"] = fg_color

    separator = ctk.CTkFrame(parent, **sep_kwargs)
    separator.grid(row=row_idx, column=column, columnspan=columnspan, sticky="ew", pady=5)

    return separator, row_idx + 1


def create_button_ctk(
    parent: tk.Widget,
    text: str,
    command: Callable[[], None] | None = None,
    fg_color: tuple[str, str] | str | None = None,
    hover_color: tuple[str, str] | str | None = None,
    text_color: tuple[str, str] | str | None = None,
    width: int | None = None,
) -> ctk.CTkButton:
    """Cria um CTkButton padronizado.

    Args:
        parent: Widget pai onde criar.
        text: Texto do botão.
        command: Callback ao clicar (opcional).
        fg_color: Cor de fundo (tupla light/dark ou string).
        hover_color: Cor no hover (tupla light/dark ou string).
        text_color: Cor do texto (tupla light/dark ou string).
        width: Largura do botão em pixels (opcional).

    Returns:
        Instância de CTkButton.
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        raise RuntimeError("CustomTkinter não disponível")

    button_kwargs: dict[str, Any] = {
        "text": text,
    }
    if command is not None:
        button_kwargs["command"] = command
    if fg_color is not None:
        button_kwargs["fg_color"] = fg_color
    if hover_color is not None:
        button_kwargs["hover_color"] = hover_color
    if text_color is not None:
        button_kwargs["text_color"] = text_color
    if width is not None:
        button_kwargs["width"] = width

    return ctk.CTkButton(parent, **button_kwargs)


def bind_dirty_tracking_ctk(
    widget: tk.Widget,
    on_dirty: Callable[[Any], None],
) -> None:
    """Configura dirty tracking para widget CTk.

    Args:
        widget: Widget CTk (Entry, Textbox, OptionMenu).
        on_dirty: Callback para marcar como modificado.
    """
    # CTkEntry e CTkTextbox suportam bindings normais do Tkinter
    if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox)):  # type: ignore[misc]
        widget.bind("<KeyRelease>", on_dirty)
        widget.bind("<<Paste>>", on_dirty)
        widget.bind("<<Cut>>", on_dirty)
    elif hasattr(widget, "configure") and hasattr(widget, "cget"):
        # Para OptionMenu/ComboBox, capturar mudança via command
        # (já configurado no create_status_dropdown_ctk se command foi passado)
        pass
