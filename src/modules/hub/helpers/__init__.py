# -*- coding: utf-8 -*-
"""Hub Helpers - Funções utilitárias consolidadas para o módulo Hub.

═══════════════════════════════════════════════════════════════════════════════
PACOTE: src.modules.hub.helpers
CONTEXTO: ORG-003 - Consolidação de helpers do Hub
═══════════════════════════════════════════════════════════════════════════════

Este pacote centraliza todos os helpers do módulo Hub, organizados por tema:

MÓDULOS:
- session.py: Helpers de autenticação, sessão e cooldown/retry
- notes.py: Helpers de formatação e manipulação de notas
- modules.py: Helpers de navegação e botões de módulos
- debug.py: Helpers de debug e diagnóstico
- screen.py: Helpers de layout e rotinas de tela (futuro)

PRINCÍPIOS:
- Organização temática (um módulo por responsabilidade)
- Funções puras quando possível (sem estado global)
- Documentação completa (docstrings + examples)
- Testabilidade (fácil de mockar e testar)

HISTÓRICO:
- ORG-003: Criação inicial (consolidação de helpers dispersos em views/ e services/)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

# Re-exports de todos os módulos
from .debug import (
    collect_full_notes_debug,
    collect_notes_debug_data,
    hub_dlog,
    show_debug_info,
)
from .modules import (
    ModuleButton,
    build_module_buttons,
    calculate_module_button_style,
)
from .notes import (
    bulk_update_author_cache,
    calculate_notes_content_hash,
    calculate_notes_hash,
    calculate_notes_ui_state,
    format_note_body_for_display,
    format_note_line,
    format_note_preview,
    format_notes_count,
    format_timestamp,
    is_notes_list_empty,
    normalize_author_cache_format,
    normalize_note_dict,
    resolve_author_name,
    should_refresh_author_cache,
    should_show_notes_section,
    should_skip_render_empty_notes,
    update_author_cache,
)
from .session import (
    calculate_retry_delay_ms,
    extract_email_prefix,
    format_author_fallback,
    get_app_from_widget,
    get_email_safe_from_widget,
    get_org_id_safe_from_widget,
    get_user_id_safe_from_widget,
    is_auth_ready,
    is_online_from_widget,
    should_skip_refresh_by_cooldown,
)

__all__ = [
    # Debug
    "collect_full_notes_debug",
    "collect_notes_debug_data",
    "hub_dlog",
    "show_debug_info",
    # Modules
    "ModuleButton",
    "build_module_buttons",
    "calculate_module_button_style",
    # Notes
    "bulk_update_author_cache",
    "calculate_notes_content_hash",
    "calculate_notes_hash",
    "calculate_notes_ui_state",
    "format_note_body_for_display",
    "format_note_line",
    "format_note_preview",
    "format_notes_count",
    "format_timestamp",
    "is_notes_list_empty",
    "normalize_author_cache_format",
    "normalize_note_dict",
    "resolve_author_name",
    "should_refresh_author_cache",
    "should_show_notes_section",
    "should_skip_render_empty_notes",
    "update_author_cache",
    # Session
    "calculate_retry_delay_ms",
    "extract_email_prefix",
    "format_author_fallback",
    "get_app_from_widget",
    "get_email_safe_from_widget",
    "get_org_id_safe_from_widget",
    "get_user_id_safe_from_widget",
    "is_auth_ready",
    "is_online_from_widget",
    "should_skip_refresh_by_cooldown",
]
