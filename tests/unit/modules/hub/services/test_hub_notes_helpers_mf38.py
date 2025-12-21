# -*- coding: utf-8 -*-
"""Testes para src/modules/hub/services/hub_notes_helpers.py (MF-38).

Cobertura:
- resolve_author_name: resolução com cache, normalização, TTL
- update_author_cache: atualização com normalização
- bulk_update_author_cache: atualização em lote
- should_refresh_author_cache: lógica de cooldown
- normalize_author_cache_format: conversão de formatos
- format_note_preview: truncamento com ellipsis
- format_note_body_for_display: formatação completa
- calculate_notes_hash: hash para detecção de mudanças
"""

from __future__ import annotations

from src.modules.hub.services.hub_notes_helpers import (
    bulk_update_author_cache,
    calculate_notes_hash,
    format_note_body_for_display,
    format_note_preview,
    normalize_author_cache_format,
    resolve_author_name,
    should_refresh_author_cache,
    update_author_cache,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1) resolve_author_name
# ═══════════════════════════════════════════════════════════════════════════════


def test_resolve_author_name_with_none():
    """resolve_author_name retorna 'Desconhecido' quando author_id é None."""
    cache = {}
    result = resolve_author_name(None, cache=cache, now_ts=100.0)
    assert result == "Desconhecido"


def test_resolve_author_name_with_empty_string():
    """resolve_author_name retorna 'Desconhecido' quando author_id é vazio."""
    cache = {}
    result = resolve_author_name("", cache=cache, now_ts=100.0)
    assert result == "Desconhecido"


def test_resolve_author_name_not_in_cache():
    """resolve_author_name retorna 'Desconhecido' quando key não está no cache."""
    cache = {"other@example.com": ("Other User", 50.0)}
    result = resolve_author_name("missing@example.com", cache=cache, now_ts=100.0)
    assert result == "Desconhecido"


def test_resolve_author_name_normalizes_key():
    """resolve_author_name normaliza author_id (strip + lowercase)."""
    cache = {"a@b.com": ("User A", 50.0)}

    # Com espaços e uppercase
    result = resolve_author_name("  A@B.COM  ", cache=cache, now_ts=100.0, ttl_seconds=3600.0)
    assert result == "User A"


def test_resolve_author_name_expired_cache():
    """resolve_author_name retorna 'Desconhecido' quando cache expirou."""
    cache = {"user@example.com": ("User Name", 50.0)}

    # Agora = 50 + 3601 = cache age = 3601s > ttl 3600s
    result = resolve_author_name("user@example.com", cache=cache, now_ts=3651.0, ttl_seconds=3600.0)
    assert result == "Desconhecido"


def test_resolve_author_name_valid_cache():
    """resolve_author_name retorna nome quando cache é válido."""
    cache = {"user@example.com": ("Valid User", 50.0)}

    # Agora = 50 + 100 = cache age = 100s < ttl 3600s
    result = resolve_author_name("user@example.com", cache=cache, now_ts=150.0, ttl_seconds=3600.0)
    assert result == "Valid User"


def test_resolve_author_name_edge_ttl():
    """resolve_author_name valida edge case: age exatamente igual ao TTL."""
    cache = {"user@example.com": ("Edge User", 100.0)}

    # age = 3600, ttl = 3600 => NÃO expirado (age > ttl é expirado)
    result = resolve_author_name("user@example.com", cache=cache, now_ts=3700.0, ttl_seconds=3600.0)
    assert result == "Edge User"

    # age = 3601, ttl = 3600 => expirado
    result = resolve_author_name("user@example.com", cache=cache, now_ts=3701.0, ttl_seconds=3600.0)
    assert result == "Desconhecido"


# ═══════════════════════════════════════════════════════════════════════════════
# 2) update_author_cache
# ═══════════════════════════════════════════════════════════════════════════════


def test_update_author_cache_empty_id():
    """update_author_cache não altera cache quando author_id é vazio."""
    cache = {}
    update_author_cache(cache, "", "Some Name", 100.0)
    assert cache == {}


def test_update_author_cache_normalizes_key():
    """update_author_cache normaliza key (strip + lowercase)."""
    cache = {}
    update_author_cache(cache, "  USER@EXAMPLE.COM  ", "User Name", 100.0)

    assert "user@example.com" in cache
    assert cache["user@example.com"] == ("User Name", 100.0)


def test_update_author_cache_empty_name_uses_placeholder():
    """update_author_cache usa 'Desconhecido' quando author_name é vazio."""
    cache = {}
    update_author_cache(cache, "user@example.com", "", 100.0)

    assert cache["user@example.com"] == ("Desconhecido", 100.0)


def test_update_author_cache_whitespace_name_uses_placeholder():
    """update_author_cache usa 'Desconhecido' quando author_name é apenas espaços."""
    cache = {}
    update_author_cache(cache, "user@example.com", "   ", 100.0)

    assert cache["user@example.com"] == ("Desconhecido", 100.0)


def test_update_author_cache_saves_name_and_timestamp():
    """update_author_cache salva (nome, timestamp) corretamente."""
    cache = {}
    update_author_cache(cache, "user@example.com", "Valid User", 123.456)

    assert cache["user@example.com"] == ("Valid User", 123.456)


def test_update_author_cache_overwrites_existing():
    """update_author_cache sobrescreve entrada existente."""
    cache = {"user@example.com": ("Old Name", 50.0)}
    update_author_cache(cache, "user@example.com", "New Name", 200.0)

    assert cache["user@example.com"] == ("New Name", 200.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 3) bulk_update_author_cache
# ═══════════════════════════════════════════════════════════════════════════════


def test_bulk_update_author_cache_updates_multiple():
    """bulk_update_author_cache atualiza múltiplos ids."""
    cache = {}
    authors_map = {
        "user1@example.com": "User One",
        "user2@example.com": "User Two",
        "user3@example.com": "User Three",
    }
    bulk_update_author_cache(cache, authors_map, 100.0)

    assert len(cache) == 3
    assert cache["user1@example.com"] == ("User One", 100.0)
    assert cache["user2@example.com"] == ("User Two", 100.0)
    assert cache["user3@example.com"] == ("User Three", 100.0)


def test_bulk_update_author_cache_normalizes_keys():
    """bulk_update_author_cache normaliza todas as keys."""
    cache = {}
    authors_map = {
        "  USER1@EXAMPLE.COM  ": "User One",
        "USER2@example.com": "User Two",
    }
    bulk_update_author_cache(cache, authors_map, 100.0)

    assert "user1@example.com" in cache
    assert "user2@example.com" in cache


def test_bulk_update_author_cache_handles_empty_names():
    """bulk_update_author_cache usa placeholder para nomes vazios."""
    cache = {}
    authors_map = {
        "user1@example.com": "",
        "user2@example.com": "   ",
    }
    bulk_update_author_cache(cache, authors_map, 100.0)

    assert cache["user1@example.com"] == ("Desconhecido", 100.0)
    assert cache["user2@example.com"] == ("Desconhecido", 100.0)


def test_bulk_update_author_cache_empty_map():
    """bulk_update_author_cache funciona com map vazio."""
    cache = {}
    bulk_update_author_cache(cache, {}, 100.0)
    assert cache == {}


# ═══════════════════════════════════════════════════════════════════════════════
# 4) should_refresh_author_cache
# ═══════════════════════════════════════════════════════════════════════════════


def test_should_refresh_author_cache_first_time():
    """should_refresh_author_cache retorna True quando last_refresh_ts <= 0."""
    assert should_refresh_author_cache(0.0, 100.0, 300.0) is True
    assert should_refresh_author_cache(-1.0, 100.0, 300.0) is True


def test_should_refresh_author_cache_within_cooldown():
    """should_refresh_author_cache retorna False quando elapsed < cooldown."""
    last_refresh = 100.0
    now = 100.0 + 100.0  # Elapsed = 100s
    cooldown = 300.0

    assert should_refresh_author_cache(last_refresh, now, cooldown) is False


def test_should_refresh_author_cache_after_cooldown():
    """should_refresh_author_cache retorna True quando elapsed >= cooldown."""
    last_refresh = 100.0
    now = 100.0 + 300.0  # Elapsed = 300s
    cooldown = 300.0

    assert should_refresh_author_cache(last_refresh, now, cooldown) is True


def test_should_refresh_author_cache_edge_cooldown():
    """should_refresh_author_cache valida edge case: elapsed exatamente igual cooldown."""
    last_refresh = 100.0
    now = 100.0 + 300.0  # Elapsed = 300s
    cooldown = 300.0

    # elapsed >= cooldown => True
    assert should_refresh_author_cache(last_refresh, now, cooldown) is True

    # elapsed < cooldown => False
    now_minus_one = 100.0 + 299.0  # Elapsed = 299s
    assert should_refresh_author_cache(last_refresh, now_minus_one, cooldown) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 5) normalize_author_cache_format
# ═══════════════════════════════════════════════════════════════════════════════


def test_normalize_author_cache_format_with_tuples(monkeypatch):
    """normalize_author_cache_format mantém tuplas (nome, ts)."""
    monkeypatch.setattr("time.time", lambda: 123.0)

    cache_input = {
        "user1@example.com": ("User One", 50.0),
        "user2@example.com": ("User Two", 75.0),
    }

    result = normalize_author_cache_format(cache_input)

    assert result["user1@example.com"] == ("User One", 50.0)
    assert result["user2@example.com"] == ("User Two", 75.0)


def test_normalize_author_cache_format_with_strings(monkeypatch):
    """normalize_author_cache_format converte strings para tuplas (str, now_ts)."""
    monkeypatch.setattr("time.time", lambda: 123.0)

    cache_input = {
        "user1@example.com": "User One",
        "user2@example.com": "User Two",
    }

    result = normalize_author_cache_format(cache_input)

    assert result["user1@example.com"] == ("User One", 123.0)
    assert result["user2@example.com"] == ("User Two", 123.0)


def test_normalize_author_cache_format_mixed(monkeypatch):
    """normalize_author_cache_format lida com mix de tuplas e strings."""
    monkeypatch.setattr("time.time", lambda: 123.0)

    cache_input = {
        "user1@example.com": ("User One", 50.0),
        "user2@example.com": "User Two",
    }

    result = normalize_author_cache_format(cache_input)

    assert result["user1@example.com"] == ("User One", 50.0)
    assert result["user2@example.com"] == ("User Two", 123.0)


def test_normalize_author_cache_format_empty():
    """normalize_author_cache_format funciona com dict vazio."""
    result = normalize_author_cache_format({})
    assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# 6) format_note_preview
# ═══════════════════════════════════════════════════════════════════════════════


def test_format_note_preview_applies_strip():
    """format_note_preview remove espaços das extremidades."""
    result = format_note_preview("  Hello World  ", max_length=100)
    assert result == "Hello World"


def test_format_note_preview_short_text():
    """format_note_preview retorna texto completo quando <= max_length."""
    result = format_note_preview("Short text", max_length=20)
    assert result == "Short text"


def test_format_note_preview_exact_max_length():
    """format_note_preview retorna texto completo quando len == max_length."""
    result = format_note_preview("1234567890", max_length=10)
    assert result == "1234567890"


def test_format_note_preview_truncates_with_ellipsis():
    """format_note_preview trunca e adiciona '...' quando > max_length."""
    result = format_note_preview("This is a very long text that needs truncation", max_length=20)

    # max_length=20 => truncate_point = 20-3 = 17
    # result = text[:17] + "..." = 17 + 3 = 20 chars
    assert len(result) == 20
    assert result.endswith("...")
    assert result == "This is a very lo..."


def test_format_note_preview_edge_max_length_3():
    """format_note_preview com max_length=3 retorna '...'."""
    result = format_note_preview("Long text", max_length=3)
    assert result == "..."


def test_format_note_preview_edge_max_length_0():
    """format_note_preview com max_length=0 retorna '...'."""
    # truncate_point = max(0, 0-3) = 0
    # text[:0] + "..." = "..."
    result = format_note_preview("Any text", max_length=0)
    assert result == "..."


def test_format_note_preview_edge_max_length_2():
    """format_note_preview com max_length=2 retorna primeiros chars (pode ser vazio + '...')."""
    # truncate_point = max(0, 2-3) = 0
    # text[:0] + "..." = "..."
    result = format_note_preview("Text", max_length=2)
    assert result == "..."


# ═══════════════════════════════════════════════════════════════════════════════
# 7) format_note_body_for_display
# ═══════════════════════════════════════════════════════════════════════════════


def test_format_note_body_for_display_no_cache():
    """format_note_body_for_display retorna 'Desconhecido' quando cache é None."""
    note = {"body": "Test body", "author_id": "user@example.com"}

    result = format_note_body_for_display(note, max_length=100, author_cache=None)

    assert result["preview"] == "Test body"
    assert result["author_name"] == "Desconhecido"
    assert result["author_id"] == "user@example.com"


def test_format_note_body_for_display_uses_author_id():
    """format_note_body_for_display usa author_id quando presente."""
    cache = {"user@example.com": ("User Name", 50.0)}
    note = {"body": "Test body", "author_id": "user@example.com"}

    result = format_note_body_for_display(note, max_length=100, author_cache=cache, now_ts=100.0)

    assert result["author_name"] == "User Name"
    assert result["author_id"] == "user@example.com"


def test_format_note_body_for_display_fallback_to_email():
    """format_note_body_for_display usa author_email quando author_id ausente."""
    cache = {"fallback@example.com": ("Fallback User", 50.0)}
    note = {"body": "Test body", "author_email": "fallback@example.com"}

    result = format_note_body_for_display(note, max_length=100, author_cache=cache, now_ts=100.0)

    assert result["author_name"] == "Fallback User"
    assert result["author_id"] == "fallback@example.com"


def test_format_note_body_for_display_truncates_preview():
    """format_note_body_for_display trunca preview respeitando max_length."""
    cache = {}
    note = {"body": "This is a very long note body that should be truncated", "author_id": "user@example.com"}

    result = format_note_body_for_display(note, max_length=20, author_cache=cache, now_ts=100.0)

    assert len(result["preview"]) == 20
    assert result["preview"].endswith("...")


def test_format_note_body_for_display_with_cache_and_now_ts():
    """format_note_body_for_display usa resolve_author_name com now_ts fornecido."""
    cache = {"user@example.com": ("Cached User", 50.0)}
    note = {"body": "Test", "author_id": "user@example.com"}

    result = format_note_body_for_display(note, max_length=100, author_cache=cache, now_ts=100.0, ttl_seconds=3600.0)

    assert result["author_name"] == "Cached User"


def test_format_note_body_for_display_uses_time_when_now_ts_none(monkeypatch):
    """format_note_body_for_display usa time.time() quando now_ts é None."""
    monkeypatch.setattr("time.time", lambda: 200.0)

    cache = {"user@example.com": ("Time User", 50.0)}
    note = {"body": "Test", "author_id": "user@example.com"}

    result = format_note_body_for_display(note, max_length=100, author_cache=cache, now_ts=None, ttl_seconds=3600.0)

    # resolve_author_name deveria usar ts=200.0 (patched time.time)
    assert result["author_name"] == "Time User"


def test_format_note_body_for_display_missing_body():
    """format_note_body_for_display lida com body ausente."""
    note = {"author_id": "user@example.com"}

    result = format_note_body_for_display(note, max_length=100, author_cache=None)

    assert result["preview"] == ""
    assert result["author_name"] == "Desconhecido"


def test_format_note_body_for_display_missing_author():
    """format_note_body_for_display lida com author ausente."""
    note = {"body": "Test body"}

    result = format_note_body_for_display(note, max_length=100, author_cache=None)

    assert result["preview"] == "Test body"
    assert result["author_name"] == "Desconhecido"
    assert result["author_id"] == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 8) calculate_notes_hash
# ═══════════════════════════════════════════════════════════════════════════════


def test_calculate_notes_hash_empty_list():
    """calculate_notes_hash retorna hash de lista vazia."""
    result = calculate_notes_hash([])

    # Não fixar valor, apenas validar que é string
    assert isinstance(result, str)
    assert len(result) > 0


def test_calculate_notes_hash_consistent():
    """calculate_notes_hash retorna mesmo hash para mesma lista."""
    notes = [
        {"id": "1", "created_at": "2025-01-01T00:00:00Z"},
        {"id": "2", "created_at": "2025-01-02T00:00:00Z"},
    ]

    hash1 = calculate_notes_hash(notes)
    hash2 = calculate_notes_hash(notes)

    assert hash1 == hash2


def test_calculate_notes_hash_changes_with_created_at():
    """calculate_notes_hash muda quando created_at muda."""
    notes_v1 = [{"id": "1", "created_at": "2025-01-01T00:00:00Z"}]
    notes_v2 = [{"id": "1", "created_at": "2025-01-02T00:00:00Z"}]

    hash1 = calculate_notes_hash(notes_v1)
    hash2 = calculate_notes_hash(notes_v2)

    assert hash1 != hash2


def test_calculate_notes_hash_changes_with_id():
    """calculate_notes_hash muda quando id muda."""
    notes_v1 = [{"id": "1", "created_at": "2025-01-01T00:00:00Z"}]
    notes_v2 = [{"id": "2", "created_at": "2025-01-01T00:00:00Z"}]

    hash1 = calculate_notes_hash(notes_v1)
    hash2 = calculate_notes_hash(notes_v2)

    assert hash1 != hash2


def test_calculate_notes_hash_order_sensitive():
    """calculate_notes_hash muda quando ordem muda."""
    notes_v1 = [
        {"id": "1", "created_at": "2025-01-01T00:00:00Z"},
        {"id": "2", "created_at": "2025-01-02T00:00:00Z"},
    ]
    notes_v2 = [
        {"id": "2", "created_at": "2025-01-02T00:00:00Z"},
        {"id": "1", "created_at": "2025-01-01T00:00:00Z"},
    ]

    hash1 = calculate_notes_hash(notes_v1)
    hash2 = calculate_notes_hash(notes_v2)

    assert hash1 != hash2


def test_calculate_notes_hash_missing_fields():
    """calculate_notes_hash tolera campos ausentes."""
    notes = [
        {"id": "1"},  # Falta created_at
        {"created_at": "2025-01-01T00:00:00Z"},  # Falta id
    ]

    result = calculate_notes_hash(notes)
    assert isinstance(result, str)


def test_calculate_notes_hash_ignores_other_fields():
    """calculate_notes_hash ignora campos extras."""
    notes_v1 = [
        {"id": "1", "created_at": "2025-01-01T00:00:00Z", "body": "Text A"},
    ]
    notes_v2 = [
        {"id": "1", "created_at": "2025-01-01T00:00:00Z", "body": "Text B"},
    ]

    hash1 = calculate_notes_hash(notes_v1)
    hash2 = calculate_notes_hash(notes_v2)

    # Body diferente não muda hash (só usa id + created_at)
    assert hash1 == hash2


# ═══════════════════════════════════════════════════════════════════════════════
# Smoke tests (integração leve)
# ═══════════════════════════════════════════════════════════════════════════════


def test_complete_workflow_author_cache():
    """Smoke test: workflow completo de cache de autores."""
    cache = {}

    # Atualizar cache
    update_author_cache(cache, "user1@example.com", "User One", 100.0)
    update_author_cache(cache, "user2@example.com", "User Two", 100.0)

    # Resolver nomes
    name1 = resolve_author_name("user1@example.com", cache=cache, now_ts=150.0)
    name2 = resolve_author_name("USER2@EXAMPLE.COM", cache=cache, now_ts=150.0)

    assert name1 == "User One"
    assert name2 == "User Two"

    # Verificar refresh
    should_refresh = should_refresh_author_cache(100.0, 450.0, 300.0)
    assert should_refresh is True


def test_complete_workflow_note_formatting():
    """Smoke test: workflow completo de formatação de nota."""
    cache = {"author@example.com": ("Note Author", 50.0)}

    note = {
        "body": "This is a sample note body for testing the formatting logic",
        "author_id": "author@example.com",
    }

    result = format_note_body_for_display(note, max_length=30, author_cache=cache, now_ts=100.0)

    assert len(result["preview"]) <= 30
    assert result["preview"].endswith("...")
    assert result["author_name"] == "Note Author"
    assert result["author_id"] == "author@example.com"
