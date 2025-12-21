# -*- coding: utf-8 -*-
"""UI Builders para client_form.

Este módulo contém funções helper para construir widgets padronizados do
formulário de clientes, reduzindo repetição de código e facilitando manutenção.

Refatoração: UI-DECOUPLE-CLIENT-FORM-002 (Fase 2)
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List

try:
    import ttkbootstrap as tb
except Exception:
    tb = ttk  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# Builders de Campos de Entrada
# =============================================================================


def create_labeled_entry(
    parent: tk.Widget,
    label_text: str,
    row_idx: int,
    column: int = 0,
    padx: int = 6,
    pady_label: tuple[int, int] = (5, 0),
    pady_entry: tuple[int, int] = (0, 5),
) -> tuple[ttk.Label, ttk.Entry, int]:
    """Cria um par label+entry padronizado em duas linhas consecutivas.

    Args:
        parent: Widget pai onde criar os elementos.
        label_text: Texto do label.
        row_idx: Índice da linha inicial (label).
        column: Coluna onde criar (padrão: 0).
        padx: Padding horizontal (padrão: 6).
        pady_label: Padding vertical do label (padrão: (5, 0)).
        pady_entry: Padding vertical do entry (padrão: (0, 5)).

    Returns:
        Tupla (label, entry, próximo_row_idx).
    """
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row_idx, column=column, sticky="w", padx=padx, pady=pady_label)

    entry = ttk.Entry(parent)
    entry.grid(row=row_idx + 1, column=column, sticky="ew", padx=padx, pady=pady_entry)

    return label, entry, row_idx + 2


def create_labeled_text(
    parent: tk.Widget,
    label_text: str,
    row_idx: int,
    column: int = 0,
    width: int = 52,
    height: int = 7,
    padx: int = 6,
    pady_label: tuple[int, int] = (0, 0),
    pady_text: tuple[int, int] = (0, 5),
) -> tuple[ttk.Label, tk.Text, int, int]:
    """Cria um par label+Text padronizado em duas linhas consecutivas.

    Args:
        parent: Widget pai onde criar os elementos.
        label_text: Texto do label.
        row_idx: Índice da linha inicial (label).
        column: Coluna onde criar (padrão: 0).
        width: Largura do Text (padrão: 52).
        height: Altura do Text (padrão: 7).
        padx: Padding horizontal (padrão: 6).
        pady_label: Padding vertical do label (padrão: (0, 0)).
        pady_text: Padding vertical do Text (padrão: (0, 5)).

    Returns:
        Tupla (label, text_widget, row_do_text, próximo_row_idx).
    """
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row_idx, column=column, sticky="w", padx=padx, pady=pady_label)

    text_widget = tk.Text(parent, width=width, height=height)
    text_row = row_idx + 1
    text_widget.grid(row=text_row, column=column, padx=padx, pady=pady_text, sticky="nsew")

    return label, text_widget, text_row, row_idx + 2


def create_status_dropdown(
    parent: tk.Widget,
    label_text: str,
    status_choices: List[str],
    on_senhas_clicked: Callable[[], None],
) -> tuple[ttk.LabelFrame, ttk.Combobox, tk.StringVar, Any]:
    """Cria frame de status com dropdown e botão Senhas.

    Args:
        parent: Widget pai onde criar o frame.
        label_text: Texto do LabelFrame.
        status_choices: Lista de opções de status.
        on_senhas_clicked: Callback para botão Senhas.

    Returns:
        Tupla (frame, combobox, string_var, btn_senhas).
    """
    frame = ttk.LabelFrame(parent, text=label_text)
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=0)

    status_var = tk.StringVar(value="")
    combobox = ttk.Combobox(frame, textvariable=status_var, values=status_choices, state="readonly")
    combobox.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

    btn_senhas = tb.Button(
        frame,
        text="Senhas",
        command=on_senhas_clicked,
        bootstyle="secondary",
    )
    btn_senhas.grid(row=0, column=1, sticky="w", padx=6, pady=6)

    return frame, combobox, status_var, btn_senhas


# =============================================================================
# Builders de Barra de Botões
# =============================================================================


def create_button_bar(
    parent: tk.Widget,
    on_save: Callable[[], None],
    on_save_and_upload: Callable[[], None],
    on_cartao_cnpj: Callable[[], None],
    on_cancel: Callable[[], None],
) -> Dict[str, Any]:
    """Cria barra de botões padrão do formulário.

    Args:
        parent: Widget pai onde criar a barra.
        on_save: Callback para botão Salvar.
        on_save_and_upload: Callback para botão Enviar documentos.
        on_cartao_cnpj: Callback para botão Cartão CNPJ.
        on_cancel: Callback para botão Cancelar.

    Returns:
        Dicionário com botões: {"save", "upload", "cartao_cnpj", "cancel"}.
    """
    btn_save = tb.Button(parent, text="Salvar", command=on_save, bootstyle="success")
    btn_save.pack(side="left", padx=5)

    btn_cartao_cnpj = tb.Button(parent, text="Cartão CNPJ", command=on_cartao_cnpj, bootstyle="info")
    btn_cartao_cnpj.pack(side="left", padx=5)

    btn_upload = tb.Button(parent, text="Enviar documentos", command=on_save_and_upload, bootstyle="info")
    btn_upload.pack(side="left", padx=5)

    btn_cancel = tb.Button(parent, text="Cancelar", command=on_cancel, bootstyle="danger")
    btn_cancel.pack(side="left", padx=5)

    return {
        "save": btn_save,
        "upload": btn_upload,
        "cartao_cnpj": btn_cartao_cnpj,
        "cancel": btn_cancel,
    }


# =============================================================================
# Helpers de Configuração
# =============================================================================


def apply_light_selection(widget: tk.Widget) -> None:
    """Tenta aplicar cor de seleção mais clara nos widgets.

    Args:
        widget: Widget onde aplicar seleção clara.
    """
    try:
        widget.configure(
            selectbackground="#5bc0de",  # azul claro
            selectforeground="#000000",  # texto preto
        )
    except tk.TclError:
        # Widget (ex. ttk.Entry) não suporta essas opções; mantém seleção padrão
        pass


def bind_dirty_tracking(widget: tk.Widget, on_change: Callable[..., None]) -> None:
    """Conecta eventos de modificação ao callback dirty tracking.

    Args:
        widget: Widget onde conectar eventos.
        on_change: Callback a chamar quando widget é modificado.
    """
    try:
        widget.bind("<KeyRelease>", on_change, add="+")
        widget.bind("<<Paste>>", on_change, add="+")
        widget.bind("<<Cut>>", on_change, add="+")
    except Exception as exc:  # noqa: BLE001  # nosec B110
        logger.debug("Widget não suporta bindings de evento: %s", exc)
