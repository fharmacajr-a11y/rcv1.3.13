"""Helper para compatibilidade entre tk.Text e ctk.CTkTextbox.

O CTkTextbox não possui alguns métodos do tk.Text que são necessários
para funcionalidades como tags, context menu e índices. Este helper
fornece acesso ao widget interno quando necessário.
"""

import tkinter as tk
from typing import Any, Union


def get_inner_text_widget(widget: Any) -> tk.Text:
    """Retorna o widget Text interno de um CTkTextbox ou o próprio widget se for Text.
    
    Args:
        widget: Widget que pode ser tk.Text ou ctk.CTkTextbox
        
    Returns:
        O widget tk.Text interno (para operações como tags, context menu)
    """
    # Se for CTkTextbox, acessar o widget interno via _textbox
    if hasattr(widget, '_textbox'):
        return widget._textbox  # type: ignore[attr-defined]
    
    # Caso contrário, assumir que é tk.Text
    return widget


def configure_text_readonly(widget: Any) -> None:
    """Configura um widget de texto como read-only sem usar state='disabled'.
    
    Para CTkTextbox, usa bind para bloquear input mas permitir seleção/cópia.
    Para tk.Text, usa state='disabled' como fallback.
    
    Args:
        widget: Widget que pode ser tk.Text ou ctk.CTkTextbox
    """
    if hasattr(widget, '_textbox'):
        # CTkTextbox: usar bind para bloquear entrada mas permitir seleção
        inner = get_inner_text_widget(widget)
        inner.bind("<Key>", lambda e: "break")
        inner.bind("<<Paste>>", lambda e: "break")
        inner.bind("<Button-3>", lambda e: None)  # Permitir context menu
    else:
        # tk.Text: usar state disabled
        widget.configure(state="disabled")