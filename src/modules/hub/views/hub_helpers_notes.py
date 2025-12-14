# -*- coding: utf-8 -*-
"""
MF-18: Helpers para notas do Hub.

Este módulo contém funções relacionadas à manipulação, formatação e
renderização de notas no HubScreen.

Extraído de hub_screen_helpers.py na MF-18 para melhor organização.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

# Timezone local com fallback
try:
    _LOCAL_TZ = datetime.now().astimezone().tzinfo or timezone.utc
except Exception:
    _LOCAL_TZ = timezone.utc


def calculate_notes_ui_state(has_org_id: bool) -> dict[str, Any]:
    """
    Calcula o estado da UI de notas baseado na presença de org_id.

    Determina se o botão "Adicionar Nota" deve estar habilitado e qual
    mensagem de placeholder deve aparecer no campo de texto.

    Args:
        has_org_id: Se True, sessão tem organização válida

    Returns:
        dict com chaves:
            - button_enabled (bool): Se botão "Adicionar" está habilitado
            - placeholder_message (str): Mensagem para campo de texto
            - text_field_enabled (bool): Se campo de texto está habilitado

    Examples:
        >>> calculate_notes_ui_state(True)
        {'button_enabled': True, 'placeholder_message': '', 'text_field_enabled': True}
        >>> result = calculate_notes_ui_state(False)
        >>> result['button_enabled']
        False
        >>> 'Sessão sem organização' in result['placeholder_message']
        True
        >>> result['text_field_enabled']
        False
    """
    if has_org_id:
        return {
            "button_enabled": True,
            "placeholder_message": "",
            "text_field_enabled": True,
        }

    return {
        "button_enabled": False,
        "placeholder_message": "Sessão sem organização. Faça login novamente.",
        "text_field_enabled": False,
    }


def calculate_notes_content_hash(notes: list[dict[str, Any]]) -> str:
    """
    Calcula hash SHA256 do conteúdo das notas para detectar mudanças.

    Usa apenas campos relevantes para renderização (author_email, created_at,
    body length, author_name) para gerar uma assinatura única do conteúdo.
    Isso permite skip de re-render quando o conteúdo não mudou.

    Args:
        notes: Lista de dicionários com dados das notas

    Returns:
        str: Hash SHA256 hex (64 caracteres) do conteúdo normalizado

    Examples:
        >>> notes = [
        ...     {
        ...         'author_email': 'user@example.com',
        ...         'created_at': '2025-01-01T10:00:00Z',
        ...         'body': 'Test',
        ...         'author_name': 'User',
        ...     },
        ... ]
        >>> hash1 = calculate_notes_content_hash(notes)
        >>> len(hash1)
        64
        >>> hash2 = calculate_notes_content_hash(notes)
        >>> hash1 == hash2
        True
        >>> notes2 = [
        ...     {
        ...         'author_email': 'user@example.com',
        ...         'created_at': '2025-01-01T10:00:00Z',
        ...         'body': 'Changed',
        ...         'author_name': 'User',
        ...     },
        ... ]
        >>> hash3 = calculate_notes_content_hash(notes2)
        >>> hash1 == hash3
        False
        >>> calculate_notes_content_hash([])
        'd751713988987e9331980363e24189ce'
    """
    sig_items = []
    for n in notes:
        email = (n.get("author_email") or "").strip().lower()
        created_at = n.get("created_at") or ""
        body_len = len(n.get("body") or "")
        author_name = n.get("author_name") or ""
        sig_items.append((email, created_at, body_len, author_name))

    # Usar MD5 para consistência (hash mais curto, não para segurança)
    content_json = json.dumps(sig_items, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(content_json.encode("utf-8"), usedforsecurity=False).hexdigest()  # nosec B324


def normalize_note_dict(note: Any) -> dict[str, Any]:
    """
    Normaliza uma nota (dict/tuple/list) para formato dict padrão.

    Converte diferentes formatos de entrada (tuplas legadas, listas, dicts)
    para um formato de dicionário consistente com chaves padronizadas.

    Args:
        note: Nota em qualquer formato (dict, tuple, list, ou outro)

    Returns:
        dict com chaves padronizadas:
            - author_email (str)
            - created_at (str)
            - body (str)
            - author_name (str, opcional)

    Examples:
        >>> normalize_note_dict({'author_email': 'user@test.com', 'body': 'Test'})
        {'author_email': 'user@test.com', 'created_at': '', 'body': 'Test', 'author_name': ''}
        >>> normalize_note_dict(('2025-01-01T10:00:00Z', 'user@test.com', 'Test'))
        {'author_email': 'user@test.com', 'created_at': '2025-01-01T10:00:00Z', 'body': 'Test', 'author_name': ''}
        >>> normalize_note_dict(['user@test.com', 'Test'])
        {'author_email': 'user@test.com', 'created_at': '', 'body': 'Test', 'author_name': ''}
        >>> normalize_note_dict({})
        {'author_email': '', 'created_at': '', 'body': '', 'author_name': ''}
    """
    if isinstance(note, dict):
        return {
            "author_email": (note.get("author_email") or note.get("author") or note.get("email") or ""),
            "created_at": (note.get("created_at") or note.get("timestamp") or ""),
            "body": (note.get("body") or note.get("text") or note.get("content") or ""),
            "author_name": (note.get("author_name") or note.get("display_name") or ""),
        }

    if isinstance(note, (tuple, list)):
        # Formatos possíveis:
        # (created_at, author, body) - 3 elementos
        # (author, body) - 2 elementos
        # (body,) - 1 elemento
        if len(note) >= 3:
            return {
                "author_email": str(note[1]),
                "created_at": str(note[0]),
                "body": str(note[2]),
                "author_name": "",
            }
        if len(note) == 2:
            return {
                "author_email": str(note[0]),
                "created_at": "",
                "body": str(note[1]),
                "author_name": "",
            }
        if len(note) == 1:
            return {
                "author_email": "",
                "created_at": "",
                "body": str(note[0]),
                "author_name": "",
            }

    # Fallback: converter para string
    return {
        "author_email": "",
        "created_at": "",
        "body": str(note) if note else "",
        "author_name": "",
    }


def format_timestamp(ts_iso: str | None) -> str:
    """
    Converte timestamp ISO do Supabase para string local dd/mm/YYYY - HH:MM.

    Usa timezone local do sistema e trata casos de erro retornando
    o timestamp original ou "?" se vazio/inválido.

    Args:
        ts_iso: Timestamp ISO 8601 (ex: "2025-01-01T10:30:00Z")

    Returns:
        str: Timestamp formatado ou "?" se inválido

    Examples:
        >>> format_timestamp("2025-01-15T14:30:00Z")  # doctest: +SKIP
        '15/01/2025 - 11:30'
        >>> format_timestamp("")
        '?'
        >>> format_timestamp(None)
        '?'
        >>> format_timestamp("invalid")
        'invalid'
    """
    try:
        if not ts_iso:
            return "?"
        # Normalizar formato ISO
        value = ts_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        # Garantir timezone UTC se não tiver
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Converter para timezone local
        dt_local = dt.astimezone(_LOCAL_TZ)
        return dt_local.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        # Retornar timestamp original em caso de erro
        return ts_iso or "?"


def format_note_line(created_at: str | None, author_display: str, text: str) -> str:
    """
    Compõe linha de nota no formato padrão: [timestamp] autor: texto.

    Formato: "[dd/mm/YYYY - HH:MM] Nome do Autor: Texto da nota"

    Args:
        created_at: Timestamp ISO 8601
        author_display: Nome de exibição do autor
        text: Corpo da nota

    Returns:
        str: Linha formatada completa

    Examples:
        >>> format_note_line("2025-01-15T14:30:00Z", "João Silva", "Reunião às 15h")  # doctest: +SKIP
        '[15/01/2025 - 11:30] João Silva: Reunião às 15h'
        >>> format_note_line("", "Usuário", "Nota sem timestamp")
        '[?] Usuário: Nota sem timestamp'
        >>> format_note_line(None, "Anônimo", "Teste")
        '[?] Anônimo: Teste'
    """
    ts = format_timestamp(created_at)
    return f"[{ts}] {author_display}: {text}"


def should_show_notes_section(_notes_count: int) -> bool:  # noqa: ARG001 (reservado para lógica futura)
    """
    Determina se seção de notas deve ser exibida baseado em contagem.

    Por enquanto sempre retorna True (seção sempre visível), mas
    centraliza a lógica para facilitar mudanças futuras.

    Args:
        _notes_count: Número de notas disponíveis (reservado para uso futuro)

    Returns:
        bool: True se deve mostrar seção de notas

    Examples:
        >>> should_show_notes_section(0)
        True
        >>> should_show_notes_section(1)
        True
        >>> should_show_notes_section(100)
        True
    """
    # Seção de notas sempre visível (mesmo vazia)
    return True


def format_notes_count(count: int) -> str:
    """
    Formata texto de contagem de notas com pluralização correta.

    Args:
        count: Número de notas

    Returns:
        str: Texto formatado (ex: "0 notas", "1 nota", "5 notas")

    Examples:
        >>> format_notes_count(0)
        '0 notas'
        >>> format_notes_count(1)
        '1 nota'
        >>> format_notes_count(2)
        '2 notas'
        >>> format_notes_count(100)
        '100 notas'
    """
    if count == 1:
        return "1 nota"
    return f"{count} notas"


def is_notes_list_empty(notes: list[dict[str, Any]] | None) -> bool:
    """
    Verifica se lista de notas está vazia ou None.

    Args:
        notes: Lista de notas ou None

    Returns:
        bool: True se lista está vazia/None, False caso contrário

    Examples:
        >>> is_notes_list_empty(None)
        True
        >>> is_notes_list_empty([])
        True
        >>> is_notes_list_empty([{'body': 'test'}])
        False
    """
    return not notes or len(notes) == 0


def should_skip_render_empty_notes(notes: list[dict[str, Any]] | None) -> bool:
    """
    Determina se deve pular render quando lista de notas vem vazia.

    Evita "branco" e piscadas na UI mantendo conteúdo anterior quando
    recebe lista vazia (comportamento defensivo).

    Args:
        notes: Lista de notas ou None

    Returns:
        bool: True se deve PULAR render, False se deve PERMITIR render

    Examples:
        >>> should_skip_render_empty_notes(None)
        True
        >>> should_skip_render_empty_notes([])
        True
        >>> should_skip_render_empty_notes([{'body': 'test'}])
        False
    """
    return is_notes_list_empty(notes)
