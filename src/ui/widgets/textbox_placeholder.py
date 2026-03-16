# -*- coding: utf-8 -*-
"""Helper reutilizável de placeholder para CTkTextbox.

CTkTextbox não suporta placeholder_text nativamente.
Este módulo oferece funções para adicionar comportamento de placeholder
via binds de FocusIn/FocusOut com flag de controle interno.
"""

from __future__ import annotations

from typing import Any


def setup_textbox_placeholder(
    textbox: Any,
    placeholder_text: str,
    text_color: str | tuple[str, str],
    muted_color: str | tuple[str, str],
) -> None:
    """Configura placeholder visual em um CTkTextbox.

    O texto-guia aparece quando o campo está vazio e sem foco,
    usando cor ``muted_color``. Ao focar, o texto-guia é removido
    e a cor original é restaurada. Ao perder foco com campo vazio,
    o placeholder reaparece.

    Um flag ``_placeholder_active`` é armazenado no widget para que
    o código de save possa verificar se o conteúdo é placeholder.

    Args:
        textbox: Instância de CTkTextbox.
        placeholder_text: Texto-guia a exibir.
        text_color: Cor do texto real (token do tema).
        muted_color: Cor do placeholder (token do tema).
    """
    textbox._placeholder_text = placeholder_text  # pyright: ignore[reportAttributeAccessIssue]
    textbox._placeholder_active = False  # pyright: ignore[reportAttributeAccessIssue]
    textbox._ph_text_color = text_color  # pyright: ignore[reportAttributeAccessIssue]
    textbox._ph_muted_color = muted_color  # pyright: ignore[reportAttributeAccessIssue]

    def _on_focus_in(_event: object = None) -> None:
        if getattr(textbox, "_placeholder_active", False):
            textbox.delete("1.0", "end")
            textbox.configure(text_color=text_color)
            textbox._placeholder_active = False  # pyright: ignore[reportAttributeAccessIssue]

    def _on_focus_out(_event: object = None) -> None:
        content = textbox.get("1.0", "end").strip()
        if not content:
            _show_placeholder(textbox)

    # Bind no widget interno (_textbox é o tk.Text real dentro do CTkTextbox)
    inner = getattr(textbox, "_textbox", textbox)
    inner.bind("<FocusIn>", _on_focus_in, add="+")
    inner.bind("<FocusOut>", _on_focus_out, add="+")

    # Ativar placeholder inicial se o textbox está vazio
    content = textbox.get("1.0", "end").strip()
    if not content:
        _show_placeholder(textbox)


def _show_placeholder(textbox: Any) -> None:
    """Insere o texto-guia no textbox com cor muted."""
    ph_text = getattr(textbox, "_placeholder_text", "")
    muted = getattr(textbox, "_ph_muted_color", "gray")
    textbox.delete("1.0", "end")
    textbox.configure(text_color=muted)
    textbox.insert("1.0", ph_text)
    textbox._placeholder_active = True  # pyright: ignore[reportAttributeAccessIssue]


def clear_textbox_placeholder(textbox: Any) -> None:
    """Desativa o placeholder programaticamente.

    Chamar ANTES de inserir dados reais carregados do banco.
    Remove o texto-guia e restaura a cor original.
    """
    if getattr(textbox, "_placeholder_active", False):
        textbox.delete("1.0", "end")
        text_color = getattr(textbox, "_ph_text_color", None)
        if text_color:
            textbox.configure(text_color=text_color)
        textbox._placeholder_active = False  # pyright: ignore[reportAttributeAccessIssue]


def get_textbox_content(textbox: Any) -> str:
    """Retorna o conteúdo real do textbox, ou string vazia se placeholder ativo.

    Usar no lugar de ``textbox.get("1.0", "end").strip()`` para leitura
    segura que nunca retorna o texto-guia.
    """
    if getattr(textbox, "_placeholder_active", False):
        return ""
    return textbox.get("1.0", "end").strip()
