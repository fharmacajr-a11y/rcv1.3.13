# -*- coding: utf-8 -*-
"""Helper dedicado para rendering de notas do HUB.

Centraliza TODA a lógica de apresentação (cores, formatação, tooltips)
de forma headless (sem depender de Tkinter).

Este módulo serve para:
- Manter as views limpas (apenas montagem de widgets).
- Evitar duplicação de lógica de formatação.
- Facilitar testes unitários de rendering.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.hub.viewmodels.notes_vm import NoteItemView


# =========================================================================
# CORES DE AUTORES
# =========================================================================

# Paleta de cores para autores (hash-based)
AUTHOR_COLOR_PALETTE = [
    "#3498db",  # blue
    "#2ecc71",  # green
    "#e74c3c",  # red
    "#f39c12",  # orange
    "#9b59b6",  # purple
    "#1abc9c",  # turquoise
    "#34495e",  # dark gray
    "#e67e22",  # dark orange
]


def get_author_color(author_key: str) -> str:
    """Retorna cor consistente para um autor baseada em seu identificador.

    Args:
        author_key: Identificador do autor (email, tag_name, etc).

    Returns:
        String de cor hex (ex: '#3498db').
    """
    # Hash author_key to get consistent color
    hash_val = hash(author_key)
    color_index = abs(hash_val) % len(AUTHOR_COLOR_PALETTE)
    return AUTHOR_COLOR_PALETTE[color_index]


# =========================================================================
# FORMATAÇÃO DE TEXTO
# =========================================================================


def format_note_header(note: "NoteItemView") -> str:
    """Monta a primeira linha da nota (timestamp + autor).

    Args:
        note: Item de nota formatado do ViewModel.

    Returns:
        String formatada: "[HH:MM] Nome: " ou "[??:??] Desconhecido: "
    """
    # Formatar timestamp
    formatted_time = format_timestamp(note.created_at)

    # Nome de exibição
    display_name = note.author_name or note.author_email or "Desconhecido"

    # Montar header: [HH:MM] Nome:
    return f"[{formatted_time}] {display_name}: "


def format_note_body(note: "NoteItemView", max_len: int = 200) -> str:
    """Gera o texto de corpo/resumo, aplicando truncate se necessário.

    Args:
        note: Item de nota formatado do ViewModel.
        max_len: Comprimento máximo do texto antes de truncar.

    Returns:
        Texto da nota (ou truncado com "...").
    """
    body = (note.body or "").strip()

    # Truncar se ultrapassar max_len
    if len(body) > max_len:
        return body[:max_len] + "..."

    return body


def format_note_full_line(note: "NoteItemView") -> str:
    """Monta a linha completa da nota (header + body).

    Args:
        note: Item de nota formatado do ViewModel.

    Returns:
        String formatada: "[HH:MM] Nome: texto completo"
    """
    header = format_note_header(note)
    body = note.body or ""
    return header + body


def format_timestamp(iso_timestamp: str) -> str:
    """Formata timestamp ISO para exibição (HH:MM).

    Args:
        iso_timestamp: Timestamp em formato ISO string.

    Returns:
        String formatada "HH:MM" ou "??:??" se inválido.
    """
    try:
        # Tentar parsear ISO timestamp
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return "??:??"


# =========================================================================
# TOOLTIPS
# =========================================================================


def build_note_tooltip_text(note: "NoteItemView") -> str:
    """Texto a ser usado em tooltips quando o usuário passa o mouse.

    Args:
        note: Item de nota formatado do ViewModel.

    Returns:
        String com informações completas: data completa + autor + texto.
    """
    # Data completa (em vez de apenas HH:MM)
    full_date = format_full_timestamp(note.created_at)

    # Nome de exibição
    display_name = note.author_name or note.author_email or "Desconhecido"

    # Texto completo (sem truncar)
    body = note.body or ""

    # Montar tooltip: data completa | autor | texto
    return f"{full_date}\n{display_name}\n\n{body}"


def format_full_timestamp(iso_timestamp: str) -> str:
    """Formata timestamp ISO para exibição completa (DD/MM/YYYY HH:MM:SS).

    Args:
        iso_timestamp: Timestamp em formato ISO string.

    Returns:
        String formatada "DD/MM/YYYY HH:MM:SS" ou "Data inválida".
    """
    try:
        # Tentar parsear ISO timestamp
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return "Data inválida"
