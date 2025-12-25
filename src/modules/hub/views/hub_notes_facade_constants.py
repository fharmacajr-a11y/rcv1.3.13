# -*- coding: utf-8 -*-
"""Constantes do HubNotesFacade (ORG-008).

Strings de log e mensagens de debug da façade de notas.
"""

# ════════════════════════════════════════════════════════════════════════
# Prefixos de Log de Debug
# ════════════════════════════════════════════════════════════════════════

LOG_PREFIX = "NotesFacade:"
"""Prefixo para logs de debug da façade de notas."""

# ════════════════════════════════════════════════════════════════════════
# Mensagens de Log de Operações
# ════════════════════════════════════════════════════════════════════════

LOG_ADD_NOTE = f"{LOG_PREFIX} on_add_note"
"""Log para operação de adicionar nota."""

LOG_UPDATE_UI_STATE = f"{LOG_PREFIX} update_notes_ui_state"
"""Log para atualização de estado de UI de notas."""

LOG_START_POLLING = f"{LOG_PREFIX} start_notes_polling"
"""Log para início de polling de notas."""

LOG_POLL_IF_NEEDED = f"{LOG_PREFIX} poll_notes_if_needed"
"""Log para polling condicional de notas."""

LOG_RETRY_AFTER_MISSING = f"{LOG_PREFIX} retry_after_table_missing"
"""Log para retry após erro de tabela ausente."""

LOG_COLLECT_DEBUG = f"{LOG_PREFIX} collect_notes_debug"
"""Log para coleta de informações de debug."""

# ════════════════════════════════════════════════════════════════════════
# Templates de Log com Parâmetros
# ════════════════════════════════════════════════════════════════════════


def log_edit_note(note_id: str) -> str:
    """Retorna mensagem de log para edição de nota.

    Args:
        note_id: ID da nota sendo editada

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} on_edit_note({note_id})"


def log_delete_note(note_id: str) -> str:
    """Retorna mensagem de log para exclusão de nota.

    Args:
        note_id: ID da nota sendo excluída

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} on_delete_note({note_id})"


def log_toggle_pin(note_id: str) -> str:
    """Retorna mensagem de log para toggle de pin.

    Args:
        note_id: ID da nota

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} on_toggle_pin({note_id})"


def log_toggle_done(note_id: str) -> str:
    """Retorna mensagem de log para toggle de done.

    Args:
        note_id: ID da nota

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} on_toggle_done({note_id})"


def log_render_notes(count: int, force: bool) -> str:
    """Retorna mensagem de log para renderização de notas.

    Args:
        count: Número de notas sendo renderizadas
        force: Se é forçado ou não

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} render_notes({count} notas, force={force})"


def log_poll_impl(force: bool) -> str:
    """Retorna mensagem de log para implementação de polling.

    Args:
        force: Se é forçado ou não

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} poll_notes_impl(force={force})"


def log_refresh_async(force: bool) -> str:
    """Retorna mensagem de log para refresh assíncrono.

    Args:
        force: Se é forçado ou não

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} refresh_notes_async(force={force})"


def log_realtime_note(note_id: str) -> str:
    """Retorna mensagem de log para evento realtime.

    Args:
        note_id: ID da nota do evento

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} on_realtime_note({note_id})"


def log_append_incremental(note_id: str) -> str:
    """Retorna mensagem de log para append incremental.

    Args:
        note_id: ID da nota sendo adicionada

    Returns:
        String de log formatada
    """
    return f"{LOG_PREFIX} append_note_incremental({note_id})"
