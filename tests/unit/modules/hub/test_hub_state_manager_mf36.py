# -*- coding: utf-8 -*-
"""Testes unitários para HubStateManager (MF-36).

Cobertura completa de todos os métodos públicos do HubStateManager,
incluindo setters simples, operações em cache, merge de dados,
e validação de campos desconhecidos em bulk_update.
"""

from __future__ import annotations

from typing import List

import pytest

from src.modules.hub.hub_state_manager import HubStateManager
from src.modules.hub.state import HubState


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def manager() -> HubStateManager:
    """Retorna um HubStateManager com estado inicial limpo."""
    return HubStateManager(HubState())


# ============================================================================
# Testes: Inicialização e Acesso
# ============================================================================


def test_init_and_state_access(manager: HubStateManager) -> None:
    """Manager deve armazenar e retornar o estado interno via property."""
    assert isinstance(manager.state, HubState)
    # O estado retornado deve ser exatamente o mesmo objeto interno
    assert manager.state is manager._state


def test_state_property_returns_same_instance(manager: HubStateManager) -> None:
    """Property state deve retornar sempre a mesma instância."""
    state1 = manager.state
    state2 = manager.state
    assert state1 is state2


# ============================================================================
# Testes: Flags Simples (Setters)
# ============================================================================


def test_set_loading(manager: HubStateManager) -> None:
    """set_loading deve atualizar is_loading."""
    assert manager.state.is_loading is False
    manager.set_loading(True)
    assert manager.state.is_loading is True
    manager.set_loading(False)
    assert manager.state.is_loading is False


def test_set_dashboard_loaded(manager: HubStateManager) -> None:
    """set_dashboard_loaded deve atualizar is_dashboard_loaded."""
    assert manager.state.is_dashboard_loaded is False
    manager.set_dashboard_loaded(True)
    assert manager.state.is_dashboard_loaded is True


def test_set_notes_loaded(manager: HubStateManager) -> None:
    """set_notes_loaded deve atualizar is_notes_loaded."""
    assert manager.state.is_notes_loaded is False
    manager.set_notes_loaded(True)
    assert manager.state.is_notes_loaded is True


def test_set_polling_active(manager: HubStateManager) -> None:
    """set_polling_active deve atualizar polling_active."""
    manager.set_polling_active(True)
    assert manager.state.polling_active is True
    manager.set_polling_active(False)
    assert manager.state.polling_active is False


def test_set_notes_poll_interval(manager: HubStateManager) -> None:
    """set_notes_poll_interval deve atualizar notes_poll_ms."""
    manager.set_notes_poll_interval(5000)
    assert manager.state.notes_poll_ms == 5000


def test_set_notes_table_missing(manager: HubStateManager) -> None:
    """set_notes_table_missing deve atualizar notes_table_missing."""
    manager.set_notes_table_missing(True)
    assert manager.state.notes_table_missing is True


def test_set_notes_table_missing_notified(manager: HubStateManager) -> None:
    """set_notes_table_missing_notified deve atualizar notes_table_missing_notified."""
    manager.set_notes_table_missing_notified(True)
    assert manager.state.notes_table_missing_notified is True


def test_set_live_sync_on(manager: HubStateManager) -> None:
    """set_live_sync_on deve atualizar live_sync_on."""
    manager.set_live_sync_on(True)
    assert manager.state.live_sync_on is True


def test_set_live_org_id(manager: HubStateManager) -> None:
    """set_live_org_id deve atualizar live_org_id."""
    manager.set_live_org_id("org-123")
    assert manager.state.live_org_id == "org-123"


def test_set_live_channel(manager: HubStateManager) -> None:
    """set_live_channel deve atualizar live_channel."""
    channel_mock = object()
    manager.set_live_channel(channel_mock)
    assert manager.state.live_channel is channel_mock


def test_set_live_last_ts(manager: HubStateManager) -> None:
    """set_live_last_ts deve atualizar live_last_ts."""
    ts = "2025-01-15T10:00:00Z"
    manager.set_live_last_ts(ts)
    assert manager.state.live_last_ts == ts


def test_set_active(manager: HubStateManager) -> None:
    """set_active deve atualizar is_active."""
    manager.set_active(True)
    assert manager.state.is_active is True


def test_set_last_dashboard_refresh_time(manager: HubStateManager) -> None:
    """set_last_dashboard_refresh_time deve atualizar last_dashboard_refresh_time."""
    ts = 1234567890.0
    manager.set_last_dashboard_refresh_time(ts)
    assert manager.state.last_dashboard_refresh_time == ts


def test_set_last_notes_refresh_time(manager: HubStateManager) -> None:
    """set_last_notes_refresh_time deve atualizar last_notes_refresh_time."""
    ts = 9876543210.0
    manager.set_last_notes_refresh_time(ts)
    assert manager.state.last_notes_refresh_time == ts


def test_set_last_author_cache_refresh(manager: HubStateManager) -> None:
    """set_last_author_cache_refresh deve atualizar last_author_cache_refresh."""
    ts = 1111111111.0
    manager.set_last_author_cache_refresh(ts)
    assert manager.state.last_author_cache_refresh == ts


def test_set_last_org_for_names(manager: HubStateManager) -> None:
    """set_last_org_for_names deve atualizar last_org_for_names."""
    org_id = "org-456"
    manager.set_last_org_for_names(org_id)
    assert manager.state.last_org_for_names == org_id


# ============================================================================
# Testes: Legacy Setters
# ============================================================================


def test_set_author_tags(manager: HubStateManager) -> None:
    """set_author_tags deve atualizar author_tags."""
    tags = {"user1@example.com": "blue", "user2@example.com": "red"}
    manager.set_author_tags(tags)
    assert manager.state.author_tags == tags


def test_set_poll_job(manager: HubStateManager) -> None:
    """set_poll_job deve atualizar poll_job."""
    manager.set_poll_job("job-123")
    assert manager.state.poll_job == "job-123"


def test_set_refreshing(manager: HubStateManager) -> None:
    """set_refreshing deve atualizar is_refreshing."""
    manager.set_refreshing(True)
    assert manager.state.is_refreshing is True


def test_set_last_refresh_ts(manager: HubStateManager) -> None:
    """set_last_refresh_ts deve atualizar last_refresh_ts."""
    ts = 2222222222.0
    manager.set_last_refresh_ts(ts)
    assert manager.state.last_refresh_ts == ts


# ============================================================================
# Testes: set_org_context
# ============================================================================


def test_set_org_context_atualiza_todos_campos_fornecidos(manager: HubStateManager) -> None:
    """set_org_context deve atualizar todos os campos não-None."""
    manager.set_org_context(
        org_id="org-789",
        user_id="user-123",
        user_email="test@example.com",
        user_role="admin",
    )
    assert manager.state.org_id == "org-789"
    assert manager.state.user_id == "user-123"
    assert manager.state.user_email == "test@example.com"
    assert manager.state.user_role == "admin"


def test_set_org_context_nao_sobrescreve_com_none(manager: HubStateManager) -> None:
    """set_org_context com None não deve sobrescrever valores existentes."""
    # Define valores iniciais
    manager.set_org_context(
        org_id="org-original",
        user_id="user-original",
        user_email="original@example.com",
        user_role="user",
    )

    # Tenta sobrescrever com None
    manager.set_org_context(org_id=None, user_id=None, user_email=None, user_role=None)

    # Valores originais devem permanecer
    assert manager.state.org_id == "org-original"
    assert manager.state.user_id == "user-original"
    assert manager.state.user_email == "original@example.com"
    assert manager.state.user_role == "user"


def test_set_org_context_atualiza_apenas_campos_especificados(manager: HubStateManager) -> None:
    """set_org_context deve atualizar apenas os campos fornecidos."""
    # Define valor inicial
    manager.set_org_context(org_id="org-1", user_email="old@example.com")

    # Atualiza apenas user_id
    manager.set_org_context(user_id="user-new")

    # org_id e user_email devem permanecer, user_id deve ser atualizado
    assert manager.state.org_id == "org-1"
    assert manager.state.user_id == "user-new"
    assert manager.state.user_email == "old@example.com"


# ============================================================================
# Testes: Cache de Autores / Nomes
# ============================================================================


def test_update_author_cache_substitui_completamente(manager: HubStateManager) -> None:
    """update_author_cache deve substituir completamente o cache."""
    cache1 = {"user1@example.com": ("User One", 1000.0)}
    manager.update_author_cache(cache1)
    assert manager.state.author_cache == cache1

    # Substituir com novo cache
    cache2 = {"user2@example.com": ("User Two", 2000.0)}
    manager.update_author_cache(cache2)
    assert manager.state.author_cache == cache2
    # user1 não deve mais existir
    assert "user1@example.com" not in manager.state.author_cache


def test_merge_author_cache_com_cache_vazio_cria_e_atualiza(manager: HubStateManager) -> None:
    """merge_author_cache com cache vazio deve criar dict e adicionar."""
    assert manager.state.author_cache == {}

    updates = {"user1@example.com": ("User One", 1000.0)}
    manager.merge_author_cache(updates)

    assert manager.state.author_cache == updates


def test_merge_author_cache_com_cache_existente_faz_merge(manager: HubStateManager) -> None:
    """merge_author_cache deve fazer merge mantendo itens antigos."""
    # Cache inicial
    manager.update_author_cache({"user1@example.com": ("User One", 1000.0)})

    # Merge com novos dados
    updates = {
        "user2@example.com": ("User Two", 2000.0),
        "user3@example.com": ("User Three", 3000.0),
    }
    manager.merge_author_cache(updates)

    # Todos os 3 devem existir
    assert len(manager.state.author_cache) == 3
    assert "user1@example.com" in manager.state.author_cache
    assert "user2@example.com" in manager.state.author_cache
    assert "user3@example.com" in manager.state.author_cache


def test_merge_author_cache_sobrescreve_valores_existentes(manager: HubStateManager) -> None:
    """merge_author_cache deve sobrescrever valores de emails duplicados."""
    # Cache inicial
    manager.update_author_cache({"user1@example.com": ("Old Name", 1000.0)})

    # Merge com mesmo email mas novo valor
    updates = {"user1@example.com": ("New Name", 2000.0)}
    manager.merge_author_cache(updates)

    # Valor deve ser atualizado
    assert manager.state.author_cache["user1@example.com"] == ("New Name", 2000.0)


def test_update_email_prefix_map(manager: HubStateManager) -> None:
    """update_email_prefix_map deve atualizar email_prefix_map."""
    prefix_map = {"user1": "user1@example.com", "user2": "user2@example.com"}
    manager.update_email_prefix_map(prefix_map)
    assert manager.state.email_prefix_map == prefix_map


def test_set_names_cache_loaded(manager: HubStateManager) -> None:
    """set_names_cache_loaded deve atualizar names_cache_loaded."""
    manager.set_names_cache_loaded(True)
    assert manager.state.names_cache_loaded is True


def test_set_names_refreshing(manager: HubStateManager) -> None:
    """set_names_refreshing deve atualizar names_refreshing."""
    manager.set_names_refreshing(True)
    assert manager.state.names_refreshing is True


def test_set_names_cache_loading(manager: HubStateManager) -> None:
    """set_names_cache_loading deve atualizar names_cache_loading."""
    manager.set_names_cache_loading(True)
    assert manager.state.names_cache_loading is True


def test_add_pending_name_fetch_com_set_vazio_cria_set(manager: HubStateManager) -> None:
    """add_pending_name_fetch deve criar set se não existir."""
    assert manager.state.pending_name_fetch == set()

    manager.add_pending_name_fetch("user1@example.com")
    assert "user1@example.com" in manager.state.pending_name_fetch


def test_add_pending_name_fetch_adiciona_multiplos_emails(manager: HubStateManager) -> None:
    """add_pending_name_fetch deve adicionar múltiplos emails."""
    manager.add_pending_name_fetch("user1@example.com")
    manager.add_pending_name_fetch("user2@example.com")
    manager.add_pending_name_fetch("user3@example.com")

    assert len(manager.state.pending_name_fetch) == 3
    assert "user1@example.com" in manager.state.pending_name_fetch
    assert "user2@example.com" in manager.state.pending_name_fetch
    assert "user3@example.com" in manager.state.pending_name_fetch


def test_remove_pending_name_fetch_remove_email_existente(manager: HubStateManager) -> None:
    """remove_pending_name_fetch deve remover email existente."""
    manager.add_pending_name_fetch("user1@example.com")
    manager.add_pending_name_fetch("user2@example.com")

    manager.remove_pending_name_fetch("user1@example.com")

    assert "user1@example.com" not in manager.state.pending_name_fetch
    assert "user2@example.com" in manager.state.pending_name_fetch


def test_remove_pending_name_fetch_nao_explode_se_email_nao_existe(manager: HubStateManager) -> None:
    """remove_pending_name_fetch não deve explodir se email não existe."""
    manager.add_pending_name_fetch("user1@example.com")

    # Tentar remover email que não existe
    manager.remove_pending_name_fetch("inexistente@example.com")

    # Não deve levantar exceção e user1 deve permanecer
    assert "user1@example.com" in manager.state.pending_name_fetch


def test_clear_pending_name_fetch_zera_set(manager: HubStateManager) -> None:
    """clear_pending_name_fetch deve zerar pending_name_fetch para set()."""
    manager.add_pending_name_fetch("user1@example.com")
    manager.add_pending_name_fetch("user2@example.com")

    manager.clear_pending_name_fetch()

    assert manager.state.pending_name_fetch == set()


def test_clear_author_cache_zera_cache_e_prefix_map(manager: HubStateManager) -> None:
    """clear_author_cache deve zerar author_cache e email_prefix_map."""
    # Popula caches
    manager.update_author_cache({"user1@example.com": ("User One", 1000.0)})
    manager.update_email_prefix_map({"user1": "user1@example.com"})
    manager.set_names_cache_loaded(True)

    # Limpa
    manager.clear_author_cache()

    # Tudo deve estar zerado
    assert manager.state.author_cache == {}
    assert manager.state.email_prefix_map == {}
    assert manager.state.names_cache_loaded is False


# ============================================================================
# Testes: Notas
# ============================================================================


def test_update_notes_data_com_update_snapshot_true(manager: HubStateManager) -> None:
    """update_notes_data com update_snapshot=True deve atualizar data e snapshot."""
    notes = [
        {"id": "note-1", "created_at": "2025-01-01T00:00:00Z", "content": "Nota 1"},
        {"id": "note-2", "created_at": "2025-01-02T00:00:00Z", "content": "Nota 2"},
    ]

    manager.update_notes_data(notes, update_snapshot=True)

    # notes_last_data deve receber a lista completa
    assert manager.state.notes_last_data == notes

    # notes_last_snapshot deve ser [(id, created_at), ...]
    expected_snapshot = [
        ("note-1", "2025-01-01T00:00:00Z"),
        ("note-2", "2025-01-02T00:00:00Z"),
    ]
    assert manager.state.notes_last_snapshot == expected_snapshot


def test_update_notes_data_com_update_snapshot_false(manager: HubStateManager) -> None:
    """update_notes_data com update_snapshot=False não deve mudar snapshot."""
    # Define snapshot inicial
    initial_snapshot = [("old-1", "2024-12-01T00:00:00Z")]
    manager.set_notes_snapshot(initial_snapshot)

    # Atualiza notas sem atualizar snapshot
    notes = [{"id": "note-1", "created_at": "2025-01-01T00:00:00Z"}]
    manager.update_notes_data(notes, update_snapshot=False)

    # notes_last_data deve ser atualizado
    assert manager.state.notes_last_data == notes

    # notes_last_snapshot NÃO deve mudar
    assert manager.state.notes_last_snapshot == initial_snapshot


def test_set_notes_snapshot(manager: HubStateManager) -> None:
    """set_notes_snapshot deve definir notes_last_snapshot."""
    snapshot = [("note-1", "2025-01-01T00:00:00Z"), ("note-2", "2025-01-02T00:00:00Z")]
    manager.set_notes_snapshot(snapshot)
    assert manager.state.notes_last_snapshot == snapshot


def test_set_cached_notes(manager: HubStateManager) -> None:
    """set_cached_notes deve definir cached_notes."""
    notes = [{"id": "note-1", "content": "Cached note"}]
    manager.set_cached_notes(notes)
    assert manager.state.cached_notes == notes


# ============================================================================
# Testes: update_live_last_ts
# ============================================================================


def test_update_live_last_ts_atualiza_se_novo_maior(manager: HubStateManager) -> None:
    """update_live_last_ts deve atualizar se new_ts > current."""
    manager.set_live_last_ts("2025-01-01T00:00:00Z")

    manager.update_live_last_ts("2025-01-02T00:00:00Z")

    assert manager.state.live_last_ts == "2025-01-02T00:00:00Z"


def test_update_live_last_ts_nao_atualiza_se_novo_menor(manager: HubStateManager) -> None:
    """update_live_last_ts não deve atualizar se new_ts <= current."""
    manager.set_live_last_ts("2025-01-02T00:00:00Z")

    manager.update_live_last_ts("2025-01-01T00:00:00Z")

    # Deve permanecer com o valor maior
    assert manager.state.live_last_ts == "2025-01-02T00:00:00Z"


def test_update_live_last_ts_nao_atualiza_se_novo_igual(manager: HubStateManager) -> None:
    """update_live_last_ts não deve atualizar se new_ts == current."""
    ts = "2025-01-01T00:00:00Z"
    manager.set_live_last_ts(ts)

    manager.update_live_last_ts(ts)

    # Deve permanecer inalterado
    assert manager.state.live_last_ts == ts


def test_update_live_last_ts_com_current_none(manager: HubStateManager) -> None:
    """update_live_last_ts deve atualizar se current for None."""
    assert manager.state.live_last_ts is None

    manager.update_live_last_ts("2025-01-01T00:00:00Z")

    assert manager.state.live_last_ts == "2025-01-01T00:00:00Z"


# ============================================================================
# Testes: bulk_update
# ============================================================================


def test_bulk_update_atualiza_campos_existentes(manager: HubStateManager) -> None:
    """bulk_update deve atualizar múltiplos campos de uma vez."""
    manager.bulk_update(
        is_loading=True,
        notes_poll_ms=12345,
        org_id="org-bulk",
        is_dashboard_loaded=True,
    )

    assert manager.state.is_loading is True
    assert manager.state.notes_poll_ms == 12345
    assert manager.state.org_id == "org-bulk"
    assert manager.state.is_dashboard_loaded is True


def test_bulk_update_campo_desconhecido_nao_cria_atributo(manager: HubStateManager) -> None:
    """bulk_update com campo desconhecido não deve criar atributo."""
    manager.bulk_update(campo_invalido="valor")

    # Campo não deve existir no state
    assert not hasattr(manager.state, "campo_invalido")


def test_bulk_update_campo_desconhecido_loga_warning(
    manager: HubStateManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bulk_update com campo desconhecido deve logar warning."""
    warnings: List[str] = []

    def fake_warning(msg: str) -> None:
        warnings.append(msg)

    # Patch do logger no módulo hub_state_manager
    monkeypatch.setattr("src.modules.hub.hub_state_manager.logger.warning", fake_warning)

    manager.bulk_update(campo_inexistente="teste")

    # Deve ter logado warning
    assert len(warnings) == 1
    assert "campo_inexistente" in warnings[0]
    assert "ignorado" in warnings[0]


def test_bulk_update_mistura_campos_validos_e_invalidos(
    manager: HubStateManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bulk_update deve processar campos válidos mesmo com inválidos presentes."""
    warnings: List[str] = []
    monkeypatch.setattr(
        "src.modules.hub.hub_state_manager.logger.warning",
        lambda msg: warnings.append(msg),
    )

    manager.bulk_update(
        is_loading=True,  # válido
        campo_invalido="valor",  # inválido
        org_id="org-123",  # válido
    )

    # Campos válidos devem ser atualizados
    assert manager.state.is_loading is True
    assert manager.state.org_id == "org-123"

    # Campo inválido não deve existir
    assert not hasattr(manager.state, "campo_invalido")

    # Deve ter logado 1 warning
    assert len(warnings) == 1


# ============================================================================
# Testes: __repr__
# ============================================================================


def test_repr_contem_classe_e_state(manager: HubStateManager) -> None:
    """__repr__ deve conter 'HubStateManager' e 'state='."""
    repr_str = repr(manager)
    assert "HubStateManager" in repr_str
    assert "state=" in repr_str


def test_repr_formato_valido(manager: HubStateManager) -> None:
    """__repr__ deve ter formato válido para debug."""
    repr_str = repr(manager)
    assert repr_str.startswith("<HubStateManager state=")
    assert repr_str.endswith(">")
