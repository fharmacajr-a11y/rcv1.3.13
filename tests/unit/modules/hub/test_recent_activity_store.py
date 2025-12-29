# -*- coding: utf-8 -*-
"""Testes para o store de atividades recentes."""

from src.modules.hub.recent_activity_store import (
    RecentActivityStore,
    format_anvisa_event,
    get_recent_activity_store,
)


def test_store_add_and_get_events():
    """Testa adicionar e recuperar eventos."""
    store = RecentActivityStore()
    store.clear()

    store.add_event("Evento 1")
    store.add_event("Evento 2")
    store.add_event("Evento 3")

    lines = store.get_lines()
    assert len(lines) == 3
    assert lines[0] == "Evento 3"  # Mais recente primeiro
    assert lines[1] == "Evento 2"
    assert lines[2] == "Evento 1"


def test_store_max_events():
    """Testa que o store respeita o limite máximo de eventos."""
    store = RecentActivityStore()
    store.clear()

    # Adicionar mais eventos que o limite
    for i in range(250):
        store.add_event(f"Evento {i}")

    lines = store.get_lines()
    assert len(lines) == 200  # MAX_EVENTS


def test_store_subscribe():
    """Testa o mecanismo de subscrição."""
    store = RecentActivityStore()
    store.clear()

    callback_called = []

    def callback():
        callback_called.append(True)

    unsubscribe = store.subscribe(callback)

    store.add_event("Evento 1")
    assert len(callback_called) == 1

    store.add_event("Evento 2")
    assert len(callback_called) == 2

    unsubscribe()

    store.add_event("Evento 3")
    assert len(callback_called) == 2  # Não deve ter sido chamado após unsubscribe


def test_format_anvisa_event_complete():
    """Testa formatação de evento ANVISA com todos os campos."""
    event = format_anvisa_event(
        action="Concluída",
        client_id="12345",
        cnpj="12.345.678/0001-90",
        request_type="Cancelamento de AFE",
        due_date="31/12/2025",
        user_name="João Silva",
    )

    assert "ANVISA" in event
    assert "Concluída" in event
    assert "Cliente 12345" in event
    assert "CNPJ 12.345.678/0001-90" in event
    assert "Cancelamento de AFE" in event
    assert "Prazo 31/12/2025" in event
    assert "por João Silva" in event


def test_format_anvisa_event_minimal():
    """Testa formatação de evento ANVISA com campos mínimos."""
    event = format_anvisa_event(action="Cancelada")

    assert "ANVISA" in event
    assert "Cancelada" in event
    assert "por —" in event


def test_singleton_instance():
    """Testa que get_recent_activity_store retorna sempre a mesma instância."""
    store1 = get_recent_activity_store()
    store2 = get_recent_activity_store()

    assert store1 is store2
