# -*- coding: utf-8 -*-
"""DEPRECATED: Use src.modules.hub.helpers.notes (mantido para compatibilidade).

ORG-003: Helpers de notas foram consolidados em hub/helpers/notes.py.
Este arquivo permanece como shim de compatibilidade para não quebrar imports externos.

Para novos códigos, importe diretamente de:
    from src.modules.hub.helpers.notes import ...
"""

from __future__ import annotations

# Re-exports do novo local (ORG-003)
from ..helpers.notes import (
    calculate_notes_content_hash,
    calculate_notes_ui_state,
    format_note_line,
    format_notes_count,
    format_timestamp,
    is_notes_list_empty,
    normalize_note_dict,
    should_show_notes_section,
    should_skip_render_empty_notes,
)

__all__ = [
    "calculate_notes_ui_state",
    "calculate_notes_content_hash",
    "normalize_note_dict",
    "format_timestamp",
    "format_note_line",
    "should_show_notes_section",
    "format_notes_count",
    "is_notes_list_empty",
    "should_skip_render_empty_notes",
]
