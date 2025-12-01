"""
TESTE_1 - infra/repositories/passwords_repository

Objetivo: aumentar a cobertura de infra/repositories/passwords_repository.py na fase 53,
cobrindo leitura/escrita de senhas, filtros e delegação ao supabase_repo.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import infra.repositories.passwords_repository as repo


def test_get_passwords_sem_filtro_retorna_lista(monkeypatch):
    dados = [
        {"client_name": "ACME", "service": "Gmail", "username": "user"},
        {"client_name": "Beta", "service": "AWS", "username": "root"},
    ]
    monkeypatch.setattr("data.supabase_repo.list_passwords", lambda org_id: dados)

    result = repo.get_passwords("org-1")

    assert result == dados


def test_get_passwords_filtra_por_search_e_cliente(monkeypatch):
    dados = [
        {"client_name": "ACME", "service": "Gmail", "username": "user"},
        {"client_name": "Beta", "service": "AWS", "username": "root"},
        {"client_name": "ACME", "service": "Slack", "username": "team"},
    ]
    monkeypatch.setattr("data.supabase_repo.list_passwords", lambda org_id: dados)

    result = repo.get_passwords("org-1", search_text="aws", client_filter="Beta")

    assert result == [{"client_name": "Beta", "service": "AWS", "username": "root"}]


def test_get_passwords_client_filter_todos_nao_filtra(monkeypatch):
    dados = [{"client_name": "X", "service": "S", "username": "u"}]
    monkeypatch.setattr("data.supabase_repo.list_passwords", lambda org_id: dados)

    result = repo.get_passwords("org-1", client_filter="Todos")

    assert result == dados


def test_create_password_chama_supabase_repo(monkeypatch):
    called = {}

    def fake_add(org_id, client_name, service, username, password_plain, notes, created_by, client_id=None):
        called["args"] = (org_id, client_name, service, username, password_plain, notes, created_by, client_id)
        return {"id": "pwd-1"}

    monkeypatch.setattr("data.supabase_repo.add_password", fake_add)

    out = repo.create_password("org", "Cli", "Srv", "user", "pw", "note", "creator")

    assert out["id"] == "pwd-1"
    assert called["args"] == ("org", "Cli", "Srv", "user", "pw", "note", "creator", None)


def test_update_password_by_id_chama_supabase_repo(monkeypatch):
    called = {}

    def fake_update(password_id, client_name, service, username, password_plain, notes, client_id=None):
        called["args"] = (password_id, client_name, service, username, password_plain, notes, client_id)
        return {"id": password_id, "username": username}

    monkeypatch.setattr("data.supabase_repo.update_password", fake_update)

    out = repo.update_password_by_id("pwd-9", username="new", notes=None)

    assert out["id"] == "pwd-9"
    assert called["args"] == ("pwd-9", None, None, "new", None, None, None)


def test_delete_password_by_id_chama_supabase_repo(monkeypatch):
    mock_delete = MagicMock()
    monkeypatch.setattr("data.supabase_repo.delete_password", mock_delete)

    repo.delete_password_by_id("pwd-2")

    mock_delete.assert_called_once_with("pwd-2")
