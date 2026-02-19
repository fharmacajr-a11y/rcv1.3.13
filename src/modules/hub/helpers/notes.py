# -*- coding: utf-8 -*-
"""Helpers para formatação, cache e manipulação de notas do Hub.

═══════════════════════════════════════════════════════════════════════════════
MÓDULO: hub/helpers/notes.py
CONTEXTO: ORG-003 - Consolidação de helpers de notas
═══════════════════════════════════════════════════════════════════════════════

Este módulo contém funções relacionadas à:
- Formatação e renderização de notas
- Cache de nomes de autores (TTL, resolução, atualização)
- Cálculo de hashes para detecção de mudanças
- Lógica de UI de notas (placeholders, habilitação de botões)

FONTES ORIGINAIS:
- src/modules/hub/views/hub_helpers_notes.py (formatação e UI)
- src/modules/hub/services/hub_notes_helpers.py (cache de autores)

HISTÓRICO:
- MF-18: Criação de hub_helpers_notes.py
- MF-33: Criação de hub_notes_helpers.py
- ORG-003: Consolidação em helpers/notes.py
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

# Type alias para o cache de autores: id → (nome, timestamp)
AuthorCache = Dict[str, Tuple[str, float]]

# Timezone local com fallback
try:
    _LOCAL_TZ = datetime.now().astimezone().tzinfo or timezone.utc
except Exception:
    _LOCAL_TZ = timezone.utc


# =========================================================================
# ESTADO DA UI DE NOTAS
# =========================================================================


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


# =========================================================================
# FORMATAÇÃO DE NOTAS
# =========================================================================


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


def format_note_preview(
    raw_text: str,
    *,
    max_length: int = 140,
) -> str:
    """Aplica cortes/ellipses/trimming para exibir preview de nota.

    Args:
        raw_text: Texto completo da nota
        max_length: Comprimento máximo do preview (padrão: 140 chars)

    Returns:
        Texto truncado com "..." se necessário, ou texto completo

    Notas:
        - Remove espaços em branco das extremidades
        - Se texto for mais curto que max_length, retorna sem modificar
        - Se truncar, adiciona "..." ao final (incluso no max_length)
    """
    text = raw_text.strip()

    if len(text) <= max_length:
        return text

    # Truncar e adicionar ellipsis
    # Usa max_length - 3 para garantir espaço para "..."
    truncate_point = max(0, max_length - 3)
    return text[:truncate_point] + "..."


# =========================================================================
# HASHES E DETECÇÃO DE MUDANÇAS
# =========================================================================


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


def calculate_notes_hash(notes: list[dict[str, Any]]) -> str:
    """Calcula hash simplificado de uma lista de notas para detecção de mudanças.

    Args:
        notes: Lista de dicionários com dados das notas

    Returns:
        String hash baseada em IDs e timestamps das notas

    Notas:
        - Usado para evitar re-renderizações desnecessárias
        - Hash considera apenas id + created_at de cada nota
        - Se lista for vazia, retorna hash de string vazia
    """
    if not notes:
        return hash("").__str__()

    # Concatenar id + created_at de todas as notas
    parts = []
    for note in notes:
        note_id = note.get("id", "")
        created_at = note.get("created_at", "")
        parts.append(f"{note_id}:{created_at}")

    # Hash da string concatenada
    content = "|".join(parts)
    return hash(content).__str__()


# =========================================================================
# CACHE DE AUTORES (de hub_notes_helpers.py)
# =========================================================================


def resolve_author_name(
    author_id: str | None,
    *,
    cache: AuthorCache,
    now_ts: float,
    ttl_seconds: float = 3600.0,
) -> str:
    """Resolve o nome de autor usando cache com TTL.

    Args:
        author_id: ID/email do autor (None = desconhecido)
        cache: Dicionário de cache (id → (nome, timestamp))
        now_ts: Timestamp atual (time.time())
        ttl_seconds: TTL do cache em segundos (padrão: 1 hora)

    Returns:
        Nome do autor ou "Desconhecido" se não encontrado/expirado

    Notas:
        - Se author_id for None/vazio, retorna "Desconhecido"
        - Se não estiver no cache, retorna "Desconhecido"
        - Se estiver no cache mas expirado, retorna "Desconhecido"
        - Cache expirado NÃO é removido aqui (service decide quando atualizar)
    """
    if not author_id:
        return "Desconhecido"

    # Normalizar: lowercase e strip
    author_key = author_id.strip().lower()

    if author_key not in cache:
        return "Desconhecido"

    # Verificar se entrada no cache está expirada
    cached_name, cached_ts = cache[author_key]
    age = now_ts - cached_ts

    if age > ttl_seconds:
        # Expirado: retorna placeholder (service pode agendar refresh)
        return "Desconhecido"

    return cached_name


def update_author_cache(
    cache: AuthorCache,
    author_id: str,
    author_name: str,
    now_ts: float,
) -> None:
    """Atualiza uma entrada no cache de autores.

    Args:
        cache: Dicionário de cache (mutável, atualizado in-place)
        author_id: ID/email do autor
        author_name: Nome de exibição do autor
        now_ts: Timestamp atual (time.time())

    Notas:
        - Normaliza author_id (lowercase + strip) antes de inserir
        - Se author_name for vazio, usa placeholder "Desconhecido"
        - Atualiza timestamp para reiniciar TTL
    """
    if not author_id:
        return

    author_key = author_id.strip().lower()
    display_name = author_name.strip() or "Desconhecido"

    cache[author_key] = (display_name, now_ts)


def bulk_update_author_cache(
    cache: AuthorCache,
    authors_map: dict[str, str],
    now_ts: float,
) -> None:
    """Atualiza múltiplas entradas no cache de autores de uma vez.

    Args:
        cache: Dicionário de cache (mutável, atualizado in-place)
        authors_map: Mapa de id → nome (id pode ser email, etc.)
        now_ts: Timestamp atual (time.time())

    Notas:
        - Normaliza todas as chaves antes de inserir
        - Útil após fetch em batch de nomes de autores do DB
    """
    for author_id, author_name in authors_map.items():
        update_author_cache(cache, author_id, author_name, now_ts)


def should_refresh_author_cache(
    last_refresh_ts: float,
    now_ts: float,
    cooldown_seconds: float = 300.0,
) -> bool:
    """Verifica se o cache de autores deve ser atualizado.

    Args:
        last_refresh_ts: Timestamp do último refresh (0.0 = nunca)
        now_ts: Timestamp atual (time.time())
        cooldown_seconds: Cooldown mínimo entre refreshes (padrão: 5 min)

    Returns:
        True se deve fazer refresh, False caso contrário

    Notas:
        - Se last_refresh_ts for 0.0, sempre retorna True (primeiro refresh)
        - Se o cooldown ainda não passou, retorna False
    """
    if last_refresh_ts <= 0.0:
        return True

    elapsed = now_ts - last_refresh_ts
    return elapsed >= cooldown_seconds


def normalize_author_cache_format(
    cache_input: dict[str, str] | dict[str, tuple[str, float]],
) -> AuthorCache:
    """Normaliza cache de autores de diferentes formatos para formato padrão.

    Args:
        cache_input: Cache em formato dict[str, str] (nome direto)
                     ou dict[str, tuple[str, float]] (nome + timestamp)

    Returns:
        Cache normalizado no formato AuthorCache (id → (nome, timestamp))

    Notas:
        - Se entrada for string, cria tupla com timestamp atual
        - Se entrada já for tupla, mantém como está
        - Usado para compatibilidade com código legacy
    """
    normalized: AuthorCache = {}
    now_ts = time.time()

    for key, value in cache_input.items():
        if isinstance(value, tuple):
            # Formato padrão: (nome, timestamp)
            normalized[key] = value
        else:
            # Formato legacy: nome direto → criar tupla com timestamp atual
            normalized[key] = (str(value), now_ts)

    return normalized


def format_note_body_for_display(
    note: dict[str, Any],
    *,
    max_length: int = 200,
    author_cache: AuthorCache | None = None,
    now_ts: float | None = None,
    ttl_seconds: float = 3600.0,
) -> dict[str, str]:
    """Formata uma nota completa para exibição (preview + autor resolvido).

    Args:
        note: Dicionário com dados brutos da nota (body, author_id, etc.)
        max_length: Comprimento máximo do preview do corpo
        author_cache: Cache de autores (opcional)
        now_ts: Timestamp atual (opcional, usa time.time() se não fornecido)
        ttl_seconds: TTL do cache de autores

    Returns:
        Dicionário com campos formatados:
            - 'preview': texto truncado do corpo
            - 'author_name': nome do autor resolvido (ou "Desconhecido")
            - 'author_id': id/email original do autor

    Notas:
        - Centraliza lógica de formatação em um único lugar
        - Se author_cache for None, sempre retorna "Desconhecido"
        - Útil para preparar dados antes de enviar para view
    """
    raw_body = note.get("body", "")
    author_id = note.get("author_id") or note.get("author_email")

    preview = format_note_preview(raw_body, max_length=max_length)

    # Resolver nome do autor usando cache
    if author_cache is None:
        author_name = "Desconhecido"
    else:
        ts = now_ts if now_ts is not None else time.time()
        author_name = resolve_author_name(
            author_id,
            cache=author_cache,
            now_ts=ts,
            ttl_seconds=ttl_seconds,
        )

    return {
        "preview": preview,
        "author_name": author_name,
        "author_id": author_id or "",
    }
