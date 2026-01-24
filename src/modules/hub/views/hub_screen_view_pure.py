# -*- coding: utf-8 -*-
"""Funções puras do HubScreenView (ORG-006).

Helpers de UI sem dependências de estado ou tkinter.
Podem ser testadas isoladamente sem mockar widgets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    pass


def make_module_button(
    parent: Any,  # tk.Misc
    text: str,
    command: Callable[[], None] | None = None,
    **kwargs: Any,
) -> Any:  # CTkButton or tk.Button
    """Cria um botão de módulo com estilo consistente.

    Helper puro para criação de botões do painel de módulos.
    Extraído do helper inline `mk_btn` em _build_modules_panel.

    Args:
        parent: Widget pai onde o botão será criado
        text: Texto do botão
        command: Callback do botão (opcional)
        **kwargs: Argumentos adicionais (ignorados para compatibilidade)

    Returns:
        CTkButton or tk.Button configurado

    Examples:
        >>> btn = make_module_button(frame, "Clientes", open_clientes)
        >>> btn.grid(row=0, column=0)
    """
    from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
    import tkinter as tk

    if HAS_CUSTOMTKINTER and ctk is not None:
        return ctk.CTkButton(parent, text=text, command=command)
    return tk.Button(parent, text=text, command=command)


def extract_time_from_timestamp(timestamp: str) -> str:
    """Extrai hora (HH:MM) de um timestamp ISO 8601.

    Função pura para formatação de timestamps em notas.
    Extraída de update_notes_panel.

    Args:
        timestamp: String de timestamp (formato ISO 8601 ou hora direta)

    Returns:
        Hora formatada (HH:MM) ou string vazia se inválido

    Examples:
        >>> extract_time_from_timestamp("2025-12-25T14:30:00Z")
        '14:30'
        >>> extract_time_from_timestamp("14:30")
        '14:30'
        >>> extract_time_from_timestamp("invalid")
        ''
    """
    from datetime import datetime

    try:
        if "T" in timestamp:
            # Timestamp ISO 8601 completo
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        # Assume que já é uma string de hora
        return timestamp[:5] if len(timestamp) >= 5 else ""
    except Exception:
        return ""


def format_note_line(note: dict[str, str]) -> str:
    """Formata uma linha de nota para exibição.

    Função pura para formatação de notas.
    Extraída de update_notes_panel.

    Args:
        note: Dicionário com campos created_at, author_email, body

    Returns:
        Linha formatada: "[HH:MM] email: texto"

    Examples:
        >>> note = {
        ...     "created_at": "2025-12-25T14:30:00Z",
        ...     "author_email": "user@example.com",
        ...     "body": "Test note"
        ... }
        >>> format_note_line(note)
        '[14:30] user@example.com: Test note\\n'
    """
    created_at = note.get("created_at", "")
    author_email = note.get("author_email", "")
    body = note.get("body", "")

    time_str = extract_time_from_timestamp(created_at)
    return f"[{time_str}] {author_email}: {body}\n"
