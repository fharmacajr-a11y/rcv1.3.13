# -*- coding: utf-8 -*-
"""Helpers para formatação de notas e cache de autores (sem UI/Tkinter).

MF-33: Extrai lógica de apresentação e cache de autores para módulo dedicado,
seguindo a mesma arquitetura limpa aplicada ao dashboard (MF-32).

Responsabilidades:
- Gerenciar cache de nomes de autores (resolve, expira, atualiza)
- Formatar texto de notas para preview (truncate, ellipses)
- Lógica headless (sem Tkinter), usável em services/controllers/testes

Este módulo NÃO conhece:
- HubScreen ou qualquer view
- Tkinter/ttk widgets
- Lógica de UI ou renderização
"""

from __future__ import annotations

import time
from typing import Any, Dict, Tuple

# Type alias para o cache de autores: id → (nome, timestamp)
AuthorCache = Dict[str, Tuple[str, float]]


# =========================================================================
# CACHE DE AUTORES
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


# =========================================================================
# FORMATAÇÃO DE NOTAS
# =========================================================================


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


# =========================================================================
# HELPERS AUXILIARES
# =========================================================================


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
