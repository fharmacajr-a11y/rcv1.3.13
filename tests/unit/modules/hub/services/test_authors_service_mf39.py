# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false
"""Testes unitários para src/modules/hub/services/authors_service.py (MF-39).

Cobertura:
- _author_display_name_ttl: cache TTL com tick
- get_author_display_name: prioridades de resolução, fetch assíncrono, prefixos, fallback
- _start_author_fetch_async: threading, cache update, callbacks, duplicação
- debug_resolve_author: diagnóstico, aliases, sources, cache/prefix hits

Estratégia:
- Fakes simples para ScreenProtocol e HubState (duck typing para testes)
- Monkeypatch para time.time(), threading.Thread, logger, imports dinâmicos
- Validação de branches (early returns, TTL expirado, cache hit/miss, erros controlados)

Nota: pyright: reportArgumentType=false desabilita avisos de tipo para fakes de teste.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

from src.modules.hub.services.authors_service import (
    _author_display_name_ttl,
    debug_resolve_author,
    get_author_display_name,
    load_env_author_names,
)


# =============================================================================
# FAKES & HELPERS
# =============================================================================


class FakeHubState:
    """State fake com campos necessários para AuthorsService."""

    def __init__(self):
        self.author_cache: Dict[str, Any] = {}
        self.email_prefix_map: Dict[str, str] = {}
        self.pending_name_fetch: set = set()
        self.notes_last_data = None
        self.notes_last_snapshot = None


class FakeScreen:
    """Screen fake implementando ScreenProtocol."""

    def __init__(self):
        self.state = FakeHubState()
        self._author_names_cache: Dict[str, Any] = {}
        self._last_render_hash = None
        self._after_callbacks = []

    def after(self, ms: int, func) -> None:
        """Executa callback imediatamente para testes síncronos."""
        self._after_callbacks.append((ms, func))
        func()  # Executa imediatamente

    def clear_pending_name_fetch(self):
        if not hasattr(self.state, "pending_name_fetch"):
            self.state.pending_name_fetch = set()
        self.state.pending_name_fetch.clear()

    def add_pending_name_fetch(self, email: str):
        self.state.pending_name_fetch.add(email)

    def remove_pending_name_fetch(self, email: str):
        self.state.pending_name_fetch.discard(email)

    def render_notes(self, data):
        pass  # Stub


# =============================================================================
# TESTES: _author_display_name_ttl
# =============================================================================


def test_author_display_name_ttl_formats_prefix():
    """_author_display_name_ttl formata prefixo de email: primeira letra maiúscula, substitui '.' por espaço."""
    result = _author_display_name_ttl("john.doe@example.com", 12345)
    assert result == "John Doe"


def test_author_display_name_ttl_cache_by_tick():
    """_author_display_name_ttl usa tick para cache: mesma key + tick = resultado cacheado."""
    key = "user@test.com"
    tick = 100
    result1 = _author_display_name_ttl(key, tick)
    result2 = _author_display_name_ttl(key, tick)
    assert result1 == result2
    assert result1 == "User"


def test_author_display_name_ttl_different_tick_fresh_call():
    """_author_display_name_ttl com tick diferente pode resultar em nova chamada (mas resultado é igual)."""
    key = "alice@mail.com"
    result1 = _author_display_name_ttl(key, 50)
    result2 = _author_display_name_ttl(key, 51)
    # Resultado é o mesmo (função pura), mas cache pode ter entradas diferentes
    assert result1 == "Alice"
    assert result2 == "Alice"


def test_author_display_name_ttl_no_at_sign():
    """_author_display_name_ttl com string sem '@' formata a string inteira."""
    result = _author_display_name_ttl("bob.smith", 999)
    assert result == "Bob Smith"


# =============================================================================
# TESTES: get_author_display_name - CASOS BÁSICOS
# =============================================================================


def test_get_author_display_name_empty_email_returns_question_mark():
    """get_author_display_name com email vazio retorna '?'."""
    screen = FakeScreen()
    assert get_author_display_name(screen, "") == "?"
    assert get_author_display_name(screen, "   ") == "?"
    assert get_author_display_name(screen, None) == "?"


def test_get_author_display_name_from_author_names_map():
    """get_author_display_name retorna nome do AUTHOR_NAMES quando email está no mapa local."""
    screen = FakeScreen()
    # AUTHOR_NAMES tem "farmacajr@gmail.com": "Júnior"
    result = get_author_display_name(screen, "farmacajr@gmail.com")
    assert result == "Júnior"


def test_get_author_display_name_normalizes_email():
    """get_author_display_name normaliza email (lowercase, strip) antes de lookup."""
    screen = FakeScreen()
    result = get_author_display_name(screen, "  FARMACAJR@GMAIL.COM  ")
    assert result == "Júnior"


def test_get_author_display_name_cache_hit_tuple_format():
    """get_author_display_name retorna do cache quando email está em cache com formato (name, expiry) válido."""
    screen = FakeScreen()
    email = "cached@test.com"
    future_time = time.time() + 100
    screen._author_names_cache[email] = ("Cached Name", future_time)

    result = get_author_display_name(screen, email)
    assert result == "Cached Name"


def test_get_author_display_name_cache_hit_string_format_converts_to_tuple():
    """get_author_display_name com cache em formato string converte para tuple (compat)."""
    screen = FakeScreen()
    email = "oldformat@test.com"
    screen._author_names_cache[email] = "Old Format Name"

    result = get_author_display_name(screen, email)
    assert result == "Old Format Name"
    # Verifica que foi convertido para tuple
    cached = screen._author_names_cache[email]
    assert isinstance(cached, tuple)
    assert cached[0] == "Old Format Name"
    assert cached[1] > time.time()


def test_get_author_display_name_cache_expired_removes_entry():
    """get_author_display_name remove entrada do cache quando TTL expirou."""
    screen = FakeScreen()
    email = "expired@test.com"
    past_time = time.time() - 100
    screen._author_names_cache[email] = ("Expired Name", past_time)

    result = get_author_display_name(screen, email, start_async_fetch=False)
    # Não deve retornar "Expired Name", mas fallback
    assert result != "Expired Name"
    assert email not in screen._author_names_cache


def test_get_author_display_name_initializes_author_names_cache():
    """get_author_display_name inicializa _author_names_cache se não existir."""
    screen = FakeScreen()
    delattr(screen, "_author_names_cache")
    assert not hasattr(screen, "_author_names_cache")

    get_author_display_name(screen, "test@mail.com", start_async_fetch=False)
    assert hasattr(screen, "_author_names_cache")
    assert isinstance(screen._author_names_cache, dict)


def test_get_author_display_name_prefix_resolution_without_at():
    """get_author_display_name com prefixo (sem '@') resolve via email_prefix_map."""
    screen = FakeScreen()
    screen.state.email_prefix_map = {"john": "john@company.com"}
    # AUTHOR_NAMES não tem john@company.com, então vai usar fallback
    result = get_author_display_name(screen, "john", start_async_fetch=False)
    # Deve ter resolvido para john@company.com e aplicado fallback "John"
    assert result == "John"


def test_get_author_display_name_fallback_placeholder():
    """get_author_display_name retorna placeholder quando nenhuma fonte tem o email."""
    screen = FakeScreen()
    email = "unknown@newdomain.com"
    result = get_author_display_name(screen, email, start_async_fetch=False)
    # Fallback: "unknown" -> "Unknown"
    assert result == "Unknown"


def test_get_author_display_name_priority_order():
    """get_author_display_name respeita ordem: cache > AUTHOR_NAMES > fetch > placeholder."""
    screen = FakeScreen()
    email = "farmacajr@gmail.com"
    # AUTHOR_NAMES tem "Junior", mas cache tem outro nome
    future_time = time.time() + 100
    screen._author_names_cache[email] = ("Cache Override", future_time)

    result = get_author_display_name(screen, email)
    # Cache tem prioridade sobre AUTHOR_NAMES
    assert result == "Cache Override"


# =============================================================================
# TESTES: get_author_display_name - FETCH ASSÍNCRONO
# =============================================================================


def test_get_author_display_name_starts_async_fetch_when_enabled(monkeypatch):
    """get_author_display_name inicia fetch assíncrono quando start_async_fetch=True."""
    screen = FakeScreen()
    email = "fetch@async.com"
    thread_started = []

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon
            thread_started.append(self)

        def start(self):
            pass  # Não executa para não bloquear teste

    monkeypatch.setattr("threading.Thread", FakeThread)

    result = get_author_display_name(screen, email, start_async_fetch=True)
    # Deve retornar placeholder imediatamente
    assert result == "Fetch"
    # Thread deve ter sido criada
    assert len(thread_started) == 1
    assert email in screen.state.pending_name_fetch


def test_get_author_display_name_no_fetch_when_disabled(monkeypatch):
    """get_author_display_name NÃO inicia fetch quando start_async_fetch=False."""
    screen = FakeScreen()
    email = "nofetch@test.com"
    thread_started = []

    class FakeThread:
        def __init__(self, target, daemon):
            thread_started.append(self)

        def start(self):
            pass

    monkeypatch.setattr("threading.Thread", FakeThread)

    result = get_author_display_name(screen, email, start_async_fetch=False)
    assert result == "Nofetch"
    assert len(thread_started) == 0


def test_get_author_display_name_no_fetch_for_prefix_without_at(monkeypatch):
    """get_author_display_name NÃO inicia fetch para prefixos sem '@' (não é email completo)."""
    screen = FakeScreen()
    thread_started = []

    class FakeThread:
        def __init__(self, target, daemon):
            thread_started.append(self)

        def start(self):
            pass

    monkeypatch.setattr("threading.Thread", FakeThread)

    get_author_display_name(screen, "prefix", start_async_fetch=True)
    # Não deve iniciar thread (sem '@')
    assert len(thread_started) == 0


def test_start_author_fetch_async_avoids_duplicate_fetch(monkeypatch):
    """_start_author_fetch_async NÃO inicia fetch se email já está em pending_name_fetch."""
    screen = FakeScreen()
    email = "duplicate@test.com"
    screen.state.pending_name_fetch.add(email)
    thread_started = []

    class FakeThread:
        def __init__(self, target, daemon):
            thread_started.append(self)

        def start(self):
            pass

    monkeypatch.setattr("threading.Thread", FakeThread)

    get_author_display_name(screen, email, start_async_fetch=True)
    # Não deve criar nova thread
    assert len(thread_started) == 0


def test_start_author_fetch_async_initializes_pending_set():
    """_start_author_fetch_async inicializa pending_name_fetch via clear_pending_name_fetch se não existir."""
    screen = FakeScreen()
    delattr(screen.state, "pending_name_fetch")
    email = "init@test.com"

    # Stub threading para não executar
    import threading

    original_thread = threading.Thread

    def fake_thread(target, daemon):
        t = original_thread(target=lambda: None, daemon=True)
        return t

    import unittest.mock

    with unittest.mock.patch("threading.Thread", side_effect=fake_thread):
        get_author_display_name(screen, email, start_async_fetch=True)

    # Deve ter inicializado pending_name_fetch
    assert hasattr(screen.state, "pending_name_fetch")


def test_start_author_fetch_async_success_updates_cache(monkeypatch):
    """_start_author_fetch_async atualiza cache quando fetch retorna nome com sucesso."""
    screen = FakeScreen()
    email = "success@fetch.com"
    fetched_name = "Fetched Name"

    # Mock profiles_service.get_display_name_by_email
    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value=fetched_name)
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    # Mock threading.Thread para executar target imediatamente
    def fake_thread_executor(target, daemon):
        target()  # Executa imediatamente
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    get_author_display_name(screen, email, start_async_fetch=True)

    # Cache deve ter sido atualizado
    cached = screen._author_names_cache.get(email)
    assert cached is not None
    assert isinstance(cached, tuple)
    assert cached[0] == fetched_name
    assert email not in screen.state.pending_name_fetch  # Removido após fetch


def test_start_author_fetch_async_handles_fetch_exception(monkeypatch):
    """_start_author_fetch_async trata exceção do fetch sem explodir."""
    screen = FakeScreen()
    email = "error@fetch.com"

    # Mock profiles_service para levantar exceção
    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(side_effect=RuntimeError("Fetch error"))
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    # Mock threading.Thread
    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    # Não deve explodir
    result = get_author_display_name(screen, email, start_async_fetch=True)
    assert result == "Error"  # Fallback
    # Pending deve ser limpo mesmo com erro
    assert email not in screen.state.pending_name_fetch


def test_start_author_fetch_async_handles_after_exception(monkeypatch):
    """_start_author_fetch_async trata exceção no screen.after sem explodir."""
    screen = FakeScreen()
    email = "after_error@test.com"

    # Mock profiles_service
    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="After Error Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    # Mock screen.after para levantar exceção
    def bad_after(ms, func):
        raise RuntimeError("After error")

    screen.after = bad_after

    # Mock threading.Thread
    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    # Não deve explodir
    result = get_author_display_name(screen, email, start_async_fetch=True)
    assert result == "After_Error"  # Fallback (usa underscore)


def test_start_author_fetch_async_invalidates_last_render_hash(monkeypatch):
    """_start_author_fetch_async invalida _last_render_hash quando atualiza cache."""
    screen = FakeScreen()
    screen._last_render_hash = "old_hash"
    email = "invalidate@test.com"

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="Invalidate Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    get_author_display_name(screen, email, start_async_fetch=True)
    # Hash deve ter sido invalidado
    assert screen._last_render_hash is None


def test_start_author_fetch_async_triggers_render_notes_with_last_data(monkeypatch):
    """_start_author_fetch_async chama render_notes com notes_last_data se disponível."""
    screen = FakeScreen()
    screen.state.notes_last_data = [{"id": 1, "body": "Note 1"}]
    email = "render@test.com"
    render_called = []

    def fake_render_notes(data):
        render_called.append(data)

    screen.render_notes = fake_render_notes

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="Render Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    get_author_display_name(screen, email, start_async_fetch=True)
    assert len(render_called) == 1
    assert render_called[0] == screen.state.notes_last_data


def test_start_author_fetch_async_triggers_render_notes_with_snapshot_fallback(monkeypatch):
    """_start_author_fetch_async chama render_notes com notes_last_snapshot se notes_last_data ausente."""
    screen = FakeScreen()
    screen.state.notes_last_data = None
    screen.state.notes_last_snapshot = [{"id": 2, "body": "Snapshot"}]
    email = "snapshot@test.com"
    render_called = []

    def fake_render_notes(data):
        render_called.append(data)

    screen.render_notes = fake_render_notes

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="Snapshot Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    get_author_display_name(screen, email, start_async_fetch=True)
    assert len(render_called) == 1
    assert render_called[0] == screen.state.notes_last_snapshot


def test_start_author_fetch_async_no_render_if_no_notes_data(monkeypatch):
    """_start_author_fetch_async NÃO chama render_notes se notes_last_data e notes_last_snapshot ausentes."""
    screen = FakeScreen()
    screen.state.notes_last_data = None
    screen.state.notes_last_snapshot = None
    email = "norender@test.com"
    render_called = []

    def fake_render_notes(data):
        render_called.append(data)

    screen.render_notes = fake_render_notes

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="No Render Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    get_author_display_name(screen, email, start_async_fetch=True)
    # render_notes não deve ser chamado
    assert len(render_called) == 0


# =============================================================================
# TESTES: debug_resolve_author - RESOLUÇÃO BÁSICA
# =============================================================================


def test_debug_resolve_author_empty_input():
    """debug_resolve_author com input vazio retorna estrutura com valores default."""
    screen = FakeScreen()
    result = debug_resolve_author(screen, "")
    assert result["input"] == ""
    assert result["normalized"] == ""
    assert result["resolved_email"] == ""
    assert result["source"] == "placeholder"
    assert result["cache_hit"] is False


def test_debug_resolve_author_normalizes_input():
    """debug_resolve_author normaliza input (strip, lowercase)."""
    screen = FakeScreen()
    result = debug_resolve_author(screen, "  TEST@EXAMPLE.COM  ")
    assert result["normalized"] == "test@example.com"


def test_debug_resolve_author_from_cache_tuple():
    """debug_resolve_author retorna nome do cache quando encontrado (formato tuple)."""
    screen = FakeScreen()
    email = "cached@debug.com"
    future_time = time.time() + 100
    screen._author_names_cache[email] = ("Debug Cached", future_time)

    result = debug_resolve_author(screen, email)
    assert result["name"] == "Debug Cached"
    assert result["source"] == "names_cache"
    assert result["cache_hit"] is True


def test_debug_resolve_author_from_cache_string_converts():
    """debug_resolve_author converte cache string para tuple e retorna nome."""
    screen = FakeScreen()
    email = "oldcache@debug.com"
    screen._author_names_cache[email] = "Old Debug Cache"

    result = debug_resolve_author(screen, email)
    assert result["name"] == "Old Debug Cache"
    assert result["source"] == "names_cache"
    # Verifica que foi convertido
    cached = screen._author_names_cache[email]
    assert isinstance(cached, tuple)


def test_debug_resolve_author_cache_expired_skips():
    """debug_resolve_author ignora cache expirado e tenta próxima fonte."""
    screen = FakeScreen()
    email = "expired@debug.com"
    past_time = time.time() - 100
    screen._author_names_cache[email] = ("Expired Debug", past_time)

    result = debug_resolve_author(screen, email)
    assert result["name"] != "Expired Debug"
    assert result["source"] != "names_cache"
    assert email not in screen._author_names_cache


def test_debug_resolve_author_from_author_names():
    """debug_resolve_author retorna nome do AUTHOR_NAMES."""
    screen = FakeScreen()
    result = debug_resolve_author(screen, "farmacajr@gmail.com")
    assert result["name"] == "Júnior"
    assert result["source"] == "AUTHOR_NAMES"


def test_debug_resolve_author_from_fetch_by_email(monkeypatch):
    """debug_resolve_author busca nome via fetch síncrono quando não encontrado em cache/AUTHOR_NAMES."""
    screen = FakeScreen()
    email = "fetch@debug.com"

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="Fetched Debug Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    result = debug_resolve_author(screen, email)
    assert result["name"] == "Fetched Debug Name"
    assert result["source"] == "fetch_by_email"


def test_debug_resolve_author_fetch_exception_fallback(monkeypatch):
    """debug_resolve_author trata exceção do fetch e retorna placeholder."""
    screen = FakeScreen()
    email = "error@debug.com"

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(side_effect=RuntimeError("Debug fetch error"))
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    result = debug_resolve_author(screen, email)
    assert result["name"] == "Error"  # Fallback do prefixo
    assert result["source"] == "placeholder"


def test_debug_resolve_author_placeholder_fallback():
    """debug_resolve_author retorna placeholder quando nenhuma fonte encontra o email."""
    screen = FakeScreen()
    email = "unknown@newdomain.com"
    result = debug_resolve_author(screen, email)
    assert result["name"] == "Unknown"
    assert result["source"] == "placeholder"


# =============================================================================
# TESTES: debug_resolve_author - ALIASES E PREFIXOS
# =============================================================================


def test_debug_resolve_author_prefix_without_at_resolves_via_map():
    """debug_resolve_author com prefixo (sem '@') resolve via email_prefix_map."""
    screen = FakeScreen()
    screen.state.email_prefix_map = {"john": "john@company.com"}

    result = debug_resolve_author(screen, "john")
    assert result["resolved_email"] == "john@company.com"
    assert result["prefix_map_hit"] is True


def test_debug_resolve_author_prefix_with_alias(monkeypatch):
    """debug_resolve_author aplica alias ao prefixo antes de resolver via mapa."""
    screen = FakeScreen()
    screen.state.email_prefix_map = {"alice": "alice@work.com"}

    # Mock EMAIL_PREFIX_ALIASES
    fake_profile_module = MagicMock()
    fake_profile_module.EMAIL_PREFIX_ALIASES = {"ali": "alice"}
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    result = debug_resolve_author(screen, "ali")
    assert result["alias_applied"] is True
    assert result["resolved_email"] == "alice@work.com"


def test_debug_resolve_author_prefix_without_alias(monkeypatch):
    """debug_resolve_author com prefixo sem alias usa prefixo direto."""
    screen = FakeScreen()
    screen.state.email_prefix_map = {"bob": "bob@site.com"}

    # Mock EMAIL_PREFIX_ALIASES vazio
    fake_profile_module = MagicMock()
    fake_profile_module.EMAIL_PREFIX_ALIASES = {}
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    result = debug_resolve_author(screen, "bob")
    assert result["alias_applied"] is False
    assert result["resolved_email"] == "bob@site.com"


def test_debug_resolve_author_prefix_not_in_map_uses_alias_as_resolved():
    """debug_resolve_author com prefixo não no mapa usa alias/prefixo como resolved_email."""
    screen = FakeScreen()
    screen.state.email_prefix_map = {}

    # Mock EMAIL_PREFIX_ALIASES com alias
    import sys

    fake_profile_module = MagicMock()
    fake_profile_module.EMAIL_PREFIX_ALIASES = {"charlie": "chuck"}
    sys.modules["src.core.services.profiles_service"] = fake_profile_module

    result = debug_resolve_author(screen, "charlie")
    assert result["alias_applied"] is True
    assert result["resolved_email"] == "chuck"  # Alias usado como resolved


def test_debug_resolve_author_handles_aliases_import_exception():
    """debug_resolve_author trata exceção ao importar EMAIL_PREFIX_ALIASES."""
    screen = FakeScreen()
    email = "test@mail.com"

    # Remover profiles_service do sys.modules para forçar import error
    import sys

    if "src.core.services.profiles_service" in sys.modules:
        del sys.modules["src.core.services.profiles_service"]

    result = debug_resolve_author(screen, email)
    # Não deve explodir, continua com alias_applied=False
    assert result["alias_applied"] is False


def test_debug_resolve_author_initializes_author_names_cache():
    """debug_resolve_author inicializa _author_names_cache se não existir."""
    screen = FakeScreen()
    delattr(screen, "_author_names_cache")

    debug_resolve_author(screen, "init@test.com")
    assert hasattr(screen, "_author_names_cache")
    assert isinstance(screen._author_names_cache, dict)


def test_debug_resolve_author_full_email_no_prefix_resolution():
    """debug_resolve_author com email completo (contém '@') NÃO usa prefix_map."""
    screen = FakeScreen()
    screen.state.email_prefix_map = {"full": "full@ignored.com"}
    email = "full@real.com"

    result = debug_resolve_author(screen, email)
    assert result["resolved_email"] == "full@real.com"  # Não resolveu via mapa
    assert result["prefix_map_hit"] is False


# =============================================================================
# TESTES: SMOKE / INTEGRAÇÃO
# =============================================================================


def test_smoke_get_author_display_name_complete_flow(monkeypatch):
    """Smoke: fluxo completo de get_author_display_name com fetch e cache update."""
    screen = FakeScreen()
    email = "complete@flow.com"

    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="Complete Name")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)

    def fake_thread_executor(target, daemon):
        target()
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Thread", fake_thread_executor)

    # 1ª chamada: retorna placeholder, inicia fetch
    result1 = get_author_display_name(screen, email, start_async_fetch=True)
    assert result1 == "Complete"  # Placeholder

    # Fetch atualiza cache
    cached = screen._author_names_cache.get(email)
    assert cached is not None
    assert cached[0] == "Complete Name"

    # 2ª chamada: retorna do cache
    result2 = get_author_display_name(screen, email, start_async_fetch=False)
    assert result2 == "Complete Name"


def test_smoke_debug_resolve_author_with_all_sources(monkeypatch):
    """Smoke: debug_resolve_author testa todas as fontes de resolução em sequência."""
    screen = FakeScreen()

    # 1) Cache
    email1 = "cache@smoke.com"
    future = time.time() + 100
    screen._author_names_cache[email1] = ("Cache Smoke", future)
    r1 = debug_resolve_author(screen, email1)
    assert r1["source"] == "names_cache"

    # 2) AUTHOR_NAMES
    email2 = "farmacajr@gmail.com"
    r2 = debug_resolve_author(screen, email2)
    assert r2["source"] == "AUTHOR_NAMES"

    # 3) Fetch
    email3 = "fetch@smoke.com"
    fake_profile_module = MagicMock()
    fake_profile_module.get_display_name_by_email = MagicMock(return_value="Fetched Smoke")
    monkeypatch.setitem(__import__("sys").modules, "src.core.services.profiles_service", fake_profile_module)
    r3 = debug_resolve_author(screen, email3)
    assert r3["source"] == "fetch_by_email"

    # 4) Placeholder
    email4 = "placeholder@smoke.com"
    fake_profile_module.get_display_name_by_email = MagicMock(return_value=None)
    r4 = debug_resolve_author(screen, email4)
    assert r4["source"] == "placeholder"


# =============================================================================
# TESTES load_env_author_names (LINHAS 89-96, 108-110) - COV-TOCADOS
# =============================================================================


def test_load_env_author_names_empty_env(monkeypatch):
    """Testa RC_INITIALS_MAP vazio retorna dict vazio."""
    monkeypatch.setenv("RC_INITIALS_MAP", "")
    result = load_env_author_names()
    assert result == {}


def test_load_env_author_names_valid_json(monkeypatch):
    """Testa RC_INITIALS_MAP com JSON válido."""
    monkeypatch.setenv("RC_INITIALS_MAP", '{"user@test.com": "John Doe"}')
    result = load_env_author_names()
    assert result == {"user@test.com": "John Doe"}


def test_load_env_author_names_wrapped_quotes(monkeypatch):
    """Testa RC_INITIALS_MAP com aspas externas (tolerância)."""
    monkeypatch.setenv("RC_INITIALS_MAP", '\'{"user@test.com": "Jane"}\'')
    result = load_env_author_names()
    assert result == {"user@test.com": "Jane"}


def test_load_env_author_names_ast_literal_eval_fallback(monkeypatch):
    """Testa fallback para ast.literal_eval quando JSON falha."""
    # Aspas simples no dict (inválido JSON, válido Python)
    monkeypatch.setenv("RC_INITIALS_MAP", "{'user@test.com': 'Bob'}")
    result = load_env_author_names()
    assert result == {"user@test.com": "Bob"}


def test_load_env_author_names_invalid_format(monkeypatch):
    """Testa RC_INITIALS_MAP com formato inválido retorna vazio."""
    monkeypatch.setenv("RC_INITIALS_MAP", "not valid json or python")
    result = load_env_author_names()
    assert result == {}


def test_load_env_author_names_normalizes_emails(monkeypatch):
    """Testa que emails são normalizados para lowercase."""
    monkeypatch.setenv("RC_INITIALS_MAP", '{"USER@Test.COM": "Name"}')
    result = load_env_author_names()
    assert "user@test.com" in result


def test_load_env_author_names_ignores_empty_values(monkeypatch):
    """Testa que valores vazios são ignorados."""
    monkeypatch.setenv("RC_INITIALS_MAP", '{"user@test.com": "", "other@test.com": "Valid"}')
    result = load_env_author_names()
    assert "user@test.com" not in result
    assert result.get("other@test.com") == "Valid"


# ========== MF46: Additional branch coverage ==========


def test_load_env_author_names_exception_returns_empty_dict_mf46(monkeypatch):
    """Testa que exceção durante parse retorna dict vazio (linhas 108-110)."""
    # Força exceção no json.loads E ast.literal_eval usando formato inválido
    monkeypatch.setenv("RC_INITIALS_MAP", "{invalid")
    result = load_env_author_names()
    assert result == {}
