# -*- coding: utf-8 -*-
"""
MF-18: Façade para helpers do HubScreen - Re-exports de módulos temáticos.

Este módulo serve como ponto único de importação para todos os helpers
do HubScreen, mantendo compatibilidade com código existente enquanto
organiza a implementação em módulos temáticos.

ORGANIZAÇÃO PÓS-MF-18:
- hub_helpers_modules.py: Navegação e botões de módulos
- hub_helpers_notes.py: Formatação e manipulação de notas
- hub_helpers_session.py: Autenticação e utilitários gerais

Importações externas continuam funcionando normalmente:
    from src.modules.hub.views.hub_screen_helpers import build_module_buttons
"""

# Re-exports de módulos (MF-18)
from .hub_helpers_modules import (
    ModuleButton,
    build_module_buttons,
    calculate_module_button_style,
)
from .hub_helpers_notes import (
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
from .hub_helpers_session import (
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
