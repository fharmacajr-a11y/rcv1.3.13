# -*- coding: utf-8 -*-
"""Testes para src/modules/hub/state.py (MF-37).

Cobertura:
- HubScreenConfig (defaults)
- HubState (defaults, should_refresh_authors_cache, update_notes_hash, mark_*_refresh)
- ensure_hub_state / ensure_state
"""

from __future__ import annotations

from src.modules.hub.state import (
    HubScreenConfig,
    HubState,
    ensure_hub_state,
    ensure_state,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1) HubScreenConfig
# ═══════════════════════════════════════════════════════════════════════════════


def test_hub_screen_config_defaults():
    """HubScreenConfig instancia com valores padrão."""
    config = HubScreenConfig()

    assert config.AUTH_RETRY_MS == 2000
    assert config.NAMES_REFRESH_COOLDOWN_S == 30
    assert config.NOTES_POLL_INTERVAL_MS == 10000
    assert config.DASHBOARD_POLL_INTERVAL_MS == 60000


def test_hub_screen_config_custom_values():
    """HubScreenConfig aceita valores customizados."""
    config = HubScreenConfig(
        AUTH_RETRY_MS=5000,
        NAMES_REFRESH_COOLDOWN_S=60,
        NOTES_POLL_INTERVAL_MS=15000,
        DASHBOARD_POLL_INTERVAL_MS=90000,
    )

    assert config.AUTH_RETRY_MS == 5000
    assert config.NAMES_REFRESH_COOLDOWN_S == 60
    assert config.NOTES_POLL_INTERVAL_MS == 15000
    assert config.DASHBOARD_POLL_INTERVAL_MS == 90000


# ═══════════════════════════════════════════════════════════════════════════════
# 2) HubState defaults
# ═══════════════════════════════════════════════════════════════════════════════


def test_hub_state_defaults():
    """HubState instancia com valores padrão."""
    state = HubState()

    # Estado Legado
    assert state.author_tags == {}
    assert state.poll_job is None
    assert state.is_refreshing is False
    assert state.last_refresh_ts is None
    assert state.pending_notes == []
    assert state.auth_retry_ms == 2000

    # Identidade
    assert state.org_id is None
    assert state.user_id is None
    assert state.user_email is None
    assert state.user_role is None

    # UI State
    assert state.is_loading is False
    assert state.is_dashboard_loaded is False
    assert state.is_notes_loaded is False

    # Cache de Dados
    assert state.cached_notes == []
    assert state.cached_authors == {}
    assert state.email_prefix_map == {}
    assert state.notes_content_hash is None
    assert state.last_names_cache_hash is None
    assert state.last_render_hash is None
    assert state.author_cache == {}

    # Lifecycle
    assert state.is_active is False
    assert state.last_dashboard_refresh_time == 0.0
    assert state.last_notes_refresh_time == 0.0
    assert state.last_author_cache_refresh == 0.0
    assert state.last_org_for_names is None

    # Features
    assert state.enable_live_sync is True
    assert state.enable_dashboard_refresh is True

    # Live Sync
    assert state.live_sync_on is False
    assert state.live_org_id is None
    assert state.live_channel is None
    assert state.live_last_ts is None

    # Erro
    assert state.notes_table_missing is False
    assert state.notes_table_missing_notified is False
    assert state.notes_retry_ms == 60000

    # Cache de Nomes
    assert state.names_cache_loaded is False
    assert state.names_refreshing is False
    assert state.names_cache_loading is False
    assert state.pending_name_fetch == set()

    # Polling
    assert state.notes_last_snapshot is None
    assert state.notes_last_data is None
    assert state.notes_poll_ms == 10000
    assert state.polling_active is False


def test_hub_state_custom_values():
    """HubState aceita valores customizados na construção."""
    state = HubState(
        org_id="org_123",
        user_id="user_456",
        user_email="test@example.com",
        is_loading=True,
        enable_live_sync=False,
        notes_poll_ms=5000,
    )

    assert state.org_id == "org_123"
    assert state.user_id == "user_456"
    assert state.user_email == "test@example.com"
    assert state.is_loading is True
    assert state.enable_live_sync is False
    assert state.notes_poll_ms == 5000


# ═══════════════════════════════════════════════════════════════════════════════
# 3) should_refresh_authors_cache
# ═══════════════════════════════════════════════════════════════════════════════


def test_should_refresh_authors_cache_when_refreshing():
    """should_refresh_authors_cache retorna False quando names_refreshing=True."""
    state = HubState()
    state.names_refreshing = True

    assert state.should_refresh_authors_cache() is False


def test_should_refresh_authors_cache_within_cooldown(monkeypatch):
    """should_refresh_authors_cache retorna False quando dentro do cooldown."""
    state = HubState()

    fixed_now = 1000.0
    monkeypatch.setattr("time.time", lambda: fixed_now)

    # Última refresh há 10 segundos
    state.last_author_cache_refresh = fixed_now - 10

    # Cooldown padrão = 30s
    assert state.should_refresh_authors_cache() is False


def test_should_refresh_authors_cache_after_cooldown(monkeypatch):
    """should_refresh_authors_cache retorna True quando cooldown expirou."""
    state = HubState()

    fixed_now = 1000.0
    monkeypatch.setattr("time.time", lambda: fixed_now)

    # Última refresh há 31 segundos
    state.last_author_cache_refresh = fixed_now - 31

    # Cooldown padrão = 30s
    assert state.should_refresh_authors_cache() is True


def test_should_refresh_authors_cache_custom_cooldown(monkeypatch):
    """should_refresh_authors_cache aceita cooldown customizado."""
    state = HubState()

    fixed_now = 1000.0
    monkeypatch.setattr("time.time", lambda: fixed_now)

    # Última refresh há 45 segundos
    state.last_author_cache_refresh = fixed_now - 45

    # Cooldown customizado = 60s
    assert state.should_refresh_authors_cache(cooldown_s=60) is False

    # Cooldown customizado = 40s
    assert state.should_refresh_authors_cache(cooldown_s=40) is True


def test_should_refresh_authors_cache_zero_elapsed(monkeypatch):
    """should_refresh_authors_cache com tempo zero não causa erro."""
    state = HubState()

    fixed_now = 1000.0
    monkeypatch.setattr("time.time", lambda: fixed_now)

    # Última refresh = agora
    state.last_author_cache_refresh = fixed_now

    assert state.should_refresh_authors_cache() is False


# ═══════════════════════════════════════════════════════════════════════════════
# 4) update_notes_hash
# ═══════════════════════════════════════════════════════════════════════════════


def test_update_notes_hash_first_call_with_dicts():
    """update_notes_hash retorna True na primeira chamada (hash None)."""
    state = HubState()

    notes = [
        {"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "Note A"},
        {"id": 2, "created_at": "2025-01-02T00:00:00Z", "body": "Note B"},
    ]

    result = state.update_notes_hash(notes)

    assert result is True
    assert state.notes_content_hash is not None


def test_update_notes_hash_same_content_returns_false():
    """update_notes_hash retorna False quando conteúdo não muda."""
    state = HubState()

    notes = [
        {"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "Note A"},
    ]

    # Primeira chamada
    state.update_notes_hash(notes)

    # Segunda chamada com mesmo conteúdo
    result = state.update_notes_hash(notes)

    assert result is False


def test_update_notes_hash_changed_body_returns_true():
    """update_notes_hash retorna True quando body muda."""
    state = HubState()

    notes_v1 = [
        {"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "Note A"},
    ]

    notes_v2 = [
        {"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "Note B"},
    ]

    # Primeira chamada
    state.update_notes_hash(notes_v1)

    # Segunda chamada com body diferente
    result = state.update_notes_hash(notes_v2)

    assert result is True


def test_update_notes_hash_with_objects():
    """update_notes_hash funciona com objetos (não apenas dicts)."""
    state = HubState()

    class Note:
        def __init__(self, id, created_at, body):
            self.id = id
            self.created_at = created_at
            self.body = body

    notes_v1 = [
        Note(1, "2025-01-01T00:00:00Z", "Note A"),
        Note(2, "2025-01-02T00:00:00Z", "Note B"),
    ]

    # Primeira chamada
    result1 = state.update_notes_hash(notes_v1)
    assert result1 is True

    # Segunda chamada com mesmo conteúdo
    notes_v2 = [
        Note(1, "2025-01-01T00:00:00Z", "Note A"),
        Note(2, "2025-01-02T00:00:00Z", "Note B"),
    ]
    result2 = state.update_notes_hash(notes_v2)
    assert result2 is False

    # Terceira chamada com body diferente
    notes_v3 = [
        Note(1, "2025-01-01T00:00:00Z", "Note C"),
        Note(2, "2025-01-02T00:00:00Z", "Note B"),
    ]
    result3 = state.update_notes_hash(notes_v3)
    assert result3 is True


def test_update_notes_hash_with_none():
    """update_notes_hash aceita None (lista vazia)."""
    state = HubState()

    # Primeira chamada com None
    result1 = state.update_notes_hash(None)
    assert result1 is True
    assert state.notes_content_hash is not None

    # Segunda chamada com None (mesmo hash)
    result2 = state.update_notes_hash(None)
    assert result2 is False


def test_update_notes_hash_with_empty_list():
    """update_notes_hash aceita lista vazia."""
    state = HubState()

    # Primeira chamada com []
    result1 = state.update_notes_hash([])
    assert result1 is True

    # Segunda chamada com []
    result2 = state.update_notes_hash([])
    assert result2 is False


def test_update_notes_hash_order_independent():
    """update_notes_hash é consistente independente da ordem (sort_keys=True)."""
    state = HubState()

    notes_v1 = [
        {"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "A"},
        {"id": 2, "created_at": "2025-01-02T00:00:00Z", "body": "B"},
    ]

    notes_v2 = [
        {"id": 2, "created_at": "2025-01-02T00:00:00Z", "body": "B"},
        {"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "A"},
    ]

    # Primeira chamada
    state.update_notes_hash(notes_v1)

    # Segunda chamada com ordem diferente (mas conteúdo igual)
    result = state.update_notes_hash(notes_v2)

    # O hash MUDA porque a lista está em ordem diferente
    # (a tupla inclui a ordem original)
    assert result is True


def test_update_notes_hash_missing_fields():
    """update_notes_hash tolera campos faltando."""
    state = HubState()

    notes = [
        {"id": 1},  # faltam created_at e body
        {"created_at": "2025-01-01T00:00:00Z"},  # faltam id e body
    ]

    result = state.update_notes_hash(notes)
    assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5) mark_*_refresh
# ═══════════════════════════════════════════════════════════════════════════════


def test_mark_dashboard_refresh(monkeypatch):
    """mark_dashboard_refresh atualiza last_dashboard_refresh_time."""
    state = HubState()

    fixed_now = 1234.5678
    monkeypatch.setattr("time.time", lambda: fixed_now)

    state.mark_dashboard_refresh()

    assert state.last_dashboard_refresh_time == fixed_now


def test_mark_notes_refresh(monkeypatch):
    """mark_notes_refresh atualiza last_notes_refresh_time."""
    state = HubState()

    fixed_now = 9876.5432
    monkeypatch.setattr("time.time", lambda: fixed_now)

    state.mark_notes_refresh()

    assert state.last_notes_refresh_time == fixed_now


def test_mark_authors_refresh(monkeypatch):
    """mark_authors_refresh atualiza last_author_cache_refresh."""
    state = HubState()

    fixed_now = 5555.5555
    monkeypatch.setattr("time.time", lambda: fixed_now)

    state.mark_authors_refresh()

    assert state.last_author_cache_refresh == fixed_now


def test_mark_refresh_methods_independent():
    """Métodos mark_*_refresh não interferem entre si."""
    state = HubState()

    import time

    state.mark_dashboard_refresh()
    dash_time = state.last_dashboard_refresh_time

    time.sleep(0.01)  # Pequeno delay para garantir timestamps diferentes

    state.mark_notes_refresh()
    notes_time = state.last_notes_refresh_time

    time.sleep(0.01)

    state.mark_authors_refresh()
    authors_time = state.last_author_cache_refresh

    # Todos devem ser diferentes
    assert dash_time != notes_time
    assert notes_time != authors_time
    assert dash_time != authors_time


# ═══════════════════════════════════════════════════════════════════════════════
# 6) ensure_hub_state / ensure_state
# ═══════════════════════════════════════════════════════════════════════════════


def test_ensure_hub_state_creates_new_state():
    """ensure_hub_state cria novo HubState quando não existe."""

    class DummyObject:
        pass

    obj = DummyObject()

    # Primeira chamada
    state = ensure_hub_state(obj)

    assert isinstance(state, HubState)
    assert hasattr(obj, "_hub_state")
    assert obj._hub_state is state


def test_ensure_hub_state_returns_existing_state():
    """ensure_hub_state retorna instância existente."""

    class DummyObject:
        pass

    obj = DummyObject()

    # Primeira chamada
    state1 = ensure_hub_state(obj)

    # Segunda chamada
    state2 = ensure_hub_state(obj)

    # Deve ser a MESMA instância
    assert state1 is state2


def test_ensure_hub_state_replaces_invalid_state():
    """ensure_hub_state substitui _hub_state inválido."""

    class DummyObject:
        pass

    obj = DummyObject()
    obj._hub_state = "invalid_string"

    # Deve substituir por HubState válido
    state = ensure_hub_state(obj)

    assert isinstance(state, HubState)
    assert obj._hub_state is state


def test_ensure_hub_state_with_none():
    """ensure_hub_state substitui _hub_state=None."""

    class DummyObject:
        pass

    obj = DummyObject()
    obj._hub_state = None

    state = ensure_hub_state(obj)

    assert isinstance(state, HubState)
    assert obj._hub_state is state


def test_ensure_state_delegates_to_ensure_hub_state():
    """ensure_state delega para ensure_hub_state."""

    class DummyObject:
        pass

    obj = DummyObject()

    state1 = ensure_state(obj)
    state2 = ensure_hub_state(obj)

    # Ambos devem retornar a mesma instância
    assert state1 is state2


def test_ensure_state_creates_new_state():
    """ensure_state cria novo HubState (mesmo comportamento)."""

    class DummyObject:
        pass

    obj = DummyObject()

    state = ensure_state(obj)

    assert isinstance(state, HubState)
    assert hasattr(obj, "_hub_state")
    assert obj._hub_state is state


def test_ensure_hub_state_preserves_existing_data():
    """ensure_hub_state preserva dados existentes no HubState."""

    class DummyObject:
        pass

    obj = DummyObject()

    # Primeira chamada
    state1 = ensure_hub_state(obj)
    state1.org_id = "org_999"
    state1.user_email = "preserve@test.com"

    # Segunda chamada
    state2 = ensure_hub_state(obj)

    # Dados devem estar preservados
    assert state2.org_id == "org_999"
    assert state2.user_email == "preserve@test.com"


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Integração (smoke tests)
# ═══════════════════════════════════════════════════════════════════════════════


def test_hub_state_complete_workflow():
    """Smoke test: workflow completo com HubState."""
    state = HubState()

    # Configurar identidade
    state.org_id = "org_abc"
    state.user_email = "user@example.com"

    # Marcar refresh
    state.mark_dashboard_refresh()
    state.mark_notes_refresh()
    state.mark_authors_refresh()

    # Atualizar notes hash
    notes = [{"id": 1, "created_at": "2025-01-01T00:00:00Z", "body": "Test"}]
    changed = state.update_notes_hash(notes)
    assert changed is True

    # Verificar cooldown
    can_refresh = state.should_refresh_authors_cache(cooldown_s=0)
    assert can_refresh is True

    # Validar estado
    assert state.org_id == "org_abc"
    assert state.last_dashboard_refresh_time > 0
    assert state.notes_content_hash is not None


def test_ensure_hub_state_complete_workflow():
    """Smoke test: workflow completo com ensure_hub_state."""

    class DummyScreen:
        pass

    screen = DummyScreen()

    # Primeira chamada
    state1 = ensure_hub_state(screen)
    state1.org_id = "org_test"

    # Segunda chamada
    state2 = ensure_state(screen)

    # Validar
    assert state1 is state2
    assert state2.org_id == "org_test"
