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
    AuthorCache,
    bulk_update_author_cache,
    calculate_notes_hash,
    format_note_body_for_display,
    format_note_preview,
    normalize_author_cache_format,
    resolve_author_name,
    should_refresh_author_cache,
    update_author_cache,
)

__all__ = [
    "AuthorCache",
    "resolve_author_name",
    "update_author_cache",
    "bulk_update_author_cache",
    "should_refresh_author_cache",
    "normalize_author_cache_format",
    "format_note_preview",
    "format_note_body_for_display",
    "calculate_notes_hash",
]
