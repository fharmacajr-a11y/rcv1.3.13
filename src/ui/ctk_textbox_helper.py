# -*- coding: utf-8 -*-
"""Helper para operações em CTkTextbox (atualização read-only).

MICROFASE 35: Centraliza lógica de atualização de CTkTextbox em modo read-only.

O CTkTextbox usa state="normal"/"disabled" como o Text padrão do Tk.
Para atualizar, é necessário:
1. Configurar state="normal"
2. Fazer delete/insert
3. Configurar state="disabled"
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

log = logging.getLogger(__name__)


def set_text_readonly(textbox: "Any", value: str) -> None:
    """Atualiza o conteúdo de um CTkTextbox em modo read-only.

    Esta função é segura para usar com CTkTextbox e ScrolledText.
    Alterna temporariamente para state="normal", atualiza o conteúdo,
    e volta para state="disabled".

    Args:
        textbox: Widget CTkTextbox ou ScrolledText.
        value: Novo texto a ser exibido.

    Exemplo:
        >>> from src.ui.ctk_textbox_helper import set_text_readonly
        >>> set_text_readonly(my_textbox, "Novo conteúdo aqui")
    """
    try:
        # Habilitar edição temporariamente
        textbox.configure(state="normal")

        # Limpar conteúdo existente
        # CTkTextbox usa "0.0" ou "1.0" - ambos funcionam
        textbox.delete("0.0", "end")

        # Inserir novo conteúdo
        textbox.insert("0.0", value)

        # Voltar para read-only
        textbox.configure(state="disabled")

    except Exception as exc:
        log.debug("Falha ao atualizar textbox read-only: %s", exc)


def append_text_readonly(textbox: "Any", value: str, scroll_to_end: bool = True) -> None:
    """Adiciona texto ao final de um CTkTextbox em modo read-only.

    Args:
        textbox: Widget CTkTextbox ou ScrolledText.
        value: Texto a ser adicionado ao final.
        scroll_to_end: Se True, faz scroll para o final após adicionar.
    """
    try:
        textbox.configure(state="normal")
        textbox.insert("end", value)
        textbox.configure(state="disabled")

        if scroll_to_end:
            textbox.see("end")

    except Exception as exc:
        log.debug("Falha ao adicionar texto ao textbox: %s", exc)


def clear_text_readonly(textbox: "Any") -> None:
    """Limpa o conteúdo de um CTkTextbox em modo read-only.

    Args:
        textbox: Widget CTkTextbox ou ScrolledText.
    """
    try:
        textbox.configure(state="normal")
        textbox.delete("0.0", "end")
        textbox.configure(state="disabled")
    except Exception as exc:
        log.debug("Falha ao limpar textbox: %s", exc)


def get_text_readonly(textbox: "Any") -> str:
    """Obtém o texto de um CTkTextbox (funciona mesmo em state disabled).

    Args:
        textbox: Widget CTkTextbox ou ScrolledText.

    Returns:
        Conteúdo do textbox como string.
    """
    try:
        return textbox.get("0.0", "end").strip()
    except Exception as exc:
        log.debug("Falha ao obter texto do textbox: %s", exc)
        return ""
