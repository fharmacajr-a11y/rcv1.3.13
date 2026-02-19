# -*- coding: utf-8 -*-
"""
Façade para helpers do HubScreen - Re-exports de módulos organizados.

ORG-003: Helpers foram consolidados em hub/helpers/ (organização temática).
Este arquivo serve como ponto único de importação para compatibilidade.

ORGANIZAÇÃO PÓS-ORG-003:
- hub/helpers/modules.py: Navegação e botões de módulos
- hub/helpers/notes.py: Formatação e manipulação de notas
- hub/helpers/session.py: Autenticação e utilitários gerais
- hub/helpers/debug.py: Debug e diagnóstico

Importações externas continuam funcionando normalmente:
    from src.modules.hub.views.hub_screen_helpers import build_module_buttons
"""

# Re-exports do novo local (ORG-003)
from ..helpers.modules import (
    ModuleButton,
    build_module_buttons,
    calculate_module_button_style,
)
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
from ..helpers.session import (
    calculate_retry_delay_ms,
    extract_email_prefix,
    format_author_fallback,
    is_auth_ready,
    should_skip_refresh_by_cooldown,
)

__all__ = [
    # Módulos e navegação (hub_helpers_modules)
    "ModuleButton",
    "build_module_buttons",
    "calculate_module_button_style",
    # Notas (hub_helpers_notes)
    "calculate_notes_content_hash",
    "calculate_notes_ui_state",
    "format_note_line",
    "format_notes_count",
    "format_timestamp",
    "is_notes_list_empty",
    "normalize_note_dict",
    "should_show_notes_section",
    "should_skip_render_empty_notes",
    # Sessão e utilitários (hub_helpers_session)
    "calculate_retry_delay_ms",
    "extract_email_prefix",
    "format_author_fallback",
    "is_auth_ready",
    "should_skip_refresh_by_cooldown",
]
