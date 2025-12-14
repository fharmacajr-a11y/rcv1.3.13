"""
Testes para src/modules/auditoria/repository.py (Microfase 9).

Foco: Aumentar cobertura de ~24.3% para ≥95%

Cenários testados:
- CRUD de auditorias (fetch, insert, update, delete)
- Fetch de clientes
- Autenticação e organização (fetch user_id, org_id)
- Tratamento de erros (registros não encontrados, dados ausentes)
- Edge cases (listas vazias, múltiplos registros, filtros)
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from src.modules.auditoria.repository import (
    delete_auditorias,
    fetch_auditorias,
    fetch_clients,
    fetch_current_user_id,
    fetch_org_id_for_user,
    insert_auditoria,
    update_auditoria,
)


# --- Testes de fetch_clients ---


def test_fetch_clients_returns_ordered_list():
    """Testa fetch_clients retorna lista ordenada de clientes."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = [
        {"id": 1, "razao_social": "Cliente A"},
        {"id": 2, "razao_social": "Cliente B"},
    ]
    mock_order.execute.return_value = mock_execute

    result = fetch_clients(mock_sb)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["razao_social"] == "Cliente B"
    mock_sb.table.assert_called_once_with("clients")
    mock_table.select.assert_called_once_with("*")
    mock_select.order.assert_called_once_with("id")


def test_fetch_clients_filters_non_dict_rows():
    """Testa que fetch_clients filtra linhas que não são dicts."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = [
        {"id": 1, "razao_social": "Cliente A"},
        "invalid",  # String não é dict
        None,  # None não é dict
        {"id": 2, "razao_social": "Cliente B"},
    ]
    mock_order.execute.return_value = mock_execute

    result = fetch_clients(mock_sb)

    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)


def test_fetch_clients_handles_empty_data():
    """Testa fetch_clients com data vazio."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = []
    mock_order.execute.return_value = mock_execute

    result = fetch_clients(mock_sb)

    assert result == []


def test_fetch_clients_handles_none_data():
    """Testa fetch_clients quando data é None."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = None
    mock_order.execute.return_value = mock_execute

    result = fetch_clients(mock_sb)

    assert result == []


def test_fetch_clients_handles_missing_data_attribute():
    """Testa fetch_clients quando response não tem atributo data."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = Mock(spec=[])  # Sem atributo data

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order
    mock_order.execute.return_value = mock_execute

    result = fetch_clients(mock_sb)

    # getattr(res, "data", None) or [] deve retornar []
    assert result == []


# --- Testes de fetch_auditorias ---


def test_fetch_auditorias_returns_ordered_list():
    """Testa fetch_auditorias retorna lista ordenada por updated_at desc."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = [
        {"id": 1, "status": "pendente", "created_at": "2024-01-01", "updated_at": "2024-01-02", "cliente_id": 10},
        {"id": 2, "status": "em_andamento", "created_at": "2024-01-03", "updated_at": "2024-01-04", "cliente_id": 20},
    ]
    mock_order.execute.return_value = mock_execute

    result = fetch_auditorias(mock_sb)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["status"] == "em_andamento"
    mock_sb.table.assert_called_once_with("auditorias")
    mock_table.select.assert_called_once_with("id, status, created_at, updated_at, cliente_id")
    mock_select.order.assert_called_once_with("updated_at", desc=True)


def test_fetch_auditorias_filters_non_dict_rows():
    """Testa que fetch_auditorias filtra linhas não-dict."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = [
        {"id": 1, "status": "pendente"},
        "invalid_string",
        123,  # Inteiro não é dict
        {"id": 2, "status": "finalizado"},
    ]
    mock_order.execute.return_value = mock_execute

    result = fetch_auditorias(mock_sb)

    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)


def test_fetch_auditorias_handles_empty_data():
    """Testa fetch_auditorias com data vazio."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = []
    mock_order.execute.return_value = mock_execute

    result = fetch_auditorias(mock_sb)

    assert result == []


def test_fetch_auditorias_handles_none_data():
    """Testa fetch_auditorias quando data é None."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    mock_execute.data = None
    mock_order.execute.return_value = mock_execute

    result = fetch_auditorias(mock_sb)

    assert result == []


# --- Testes de insert_auditoria ---


def test_insert_auditoria_success():
    """Testa inserção de auditoria com sucesso."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute

    payload = {"status": "pendente", "cliente_id": 100}
    result = insert_auditoria(mock_sb, payload)

    assert result == mock_execute
    mock_sb.table.assert_called_once_with("auditorias")
    mock_table.insert.assert_called_once_with(payload)
    mock_insert.execute.assert_called_once()


def test_insert_auditoria_with_multiple_fields():
    """Testa inserção com múltiplos campos."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute

    payload = {
        "status": "em_andamento",
        "cliente_id": 200,
        "created_at": "2024-01-01T10:00:00",
        "updated_at": "2024-01-01T10:00:00",
    }
    result = insert_auditoria(mock_sb, payload)

    assert result == mock_execute
    mock_table.insert.assert_called_once_with(payload)


def test_insert_auditoria_returns_execute_result():
    """Testa que insert_auditoria retorna resultado de execute."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = [{"id": 999}]

    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute

    payload = {"status": "pendente", "cliente_id": 100}
    result = insert_auditoria(mock_sb, payload)

    assert result.data == [{"id": 999}]


# --- Testes de update_auditoria ---


def test_update_auditoria_success():
    """Testa atualização de status de auditoria."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_select = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.select.return_value = mock_select
    mock_select.execute.return_value = mock_execute

    result = update_auditoria(mock_sb, auditoria_id="123", status="finalizado")

    assert result == mock_execute
    mock_sb.table.assert_called_once_with("auditorias")
    mock_table.update.assert_called_once_with({"status": "finalizado"})
    mock_update.eq.assert_called_once_with("id", "123")
    mock_eq.select.assert_called_once_with("status, updated_at")


def test_update_auditoria_with_different_status():
    """Testa atualização com diferentes status."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_select = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.select.return_value = mock_select
    mock_select.execute.return_value = mock_execute

    update_auditoria(mock_sb, auditoria_id="456", status="cancelado")

    mock_table.update.assert_called_once_with({"status": "cancelado"})
    mock_update.eq.assert_called_once_with("id", "456")


def test_update_auditoria_returns_execute_result():
    """Testa que update_auditoria retorna resultado completo."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_select = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = [{"status": "finalizado", "updated_at": "2024-01-10T12:00:00"}]

    mock_sb.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.select.return_value = mock_select
    mock_select.execute.return_value = mock_execute

    result = update_auditoria(mock_sb, auditoria_id="789", status="finalizado")

    assert result.data[0]["status"] == "finalizado"


# --- Testes de delete_auditorias ---


def test_delete_auditorias_with_multiple_ids():
    """Testa deleção de múltiplas auditorias."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_in = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.in_.return_value = mock_in
    mock_in.execute.return_value = mock_execute

    ids = ["1", "2", "3"]
    delete_auditorias(mock_sb, ids)

    mock_sb.table.assert_called_once_with("auditorias")
    mock_table.delete.assert_called_once()
    mock_delete.in_.assert_called_once_with("id", ["1", "2", "3"])
    mock_in.execute.assert_called_once()


def test_delete_auditorias_with_single_id():
    """Testa deleção de uma única auditoria."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_in = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.in_.return_value = mock_in
    mock_in.execute.return_value = mock_execute

    ids = ["999"]
    delete_auditorias(mock_sb, ids)

    mock_delete.in_.assert_called_once_with("id", ["999"])


def test_delete_auditorias_with_empty_list_does_nothing():
    """Testa que lista vazia não executa delete."""
    mock_sb = MagicMock()

    delete_auditorias(mock_sb, [])

    # Não deve chamar nenhum método do sb
    mock_sb.table.assert_not_called()


def test_delete_auditorias_converts_sequence_to_list():
    """Testa que sequence é convertida para lista."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_in = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.in_.return_value = mock_in
    mock_in.execute.return_value = mock_execute

    ids = ("10", "20", "30")  # Tuple é Sequence
    delete_auditorias(mock_sb, ids)

    # Deve converter para lista
    mock_delete.in_.assert_called_once_with("id", ["10", "20", "30"])


# --- Testes de fetch_current_user_id ---


def test_fetch_current_user_id_success():
    """Testa fetch de user_id autenticado."""
    mock_sb = MagicMock()
    mock_auth = MagicMock()
    mock_user_response = MagicMock()
    mock_user_obj = MagicMock()

    mock_sb.auth = mock_auth
    mock_auth.get_user.return_value = mock_user_response
    mock_user_response.user = mock_user_obj
    mock_user_obj.id = "user-123-abc"

    result = fetch_current_user_id(mock_sb)

    assert result == "user-123-abc"
    mock_auth.get_user.assert_called_once()


def test_fetch_current_user_id_raises_when_no_user():
    """Testa que lança erro quando não há usuário autenticado."""
    mock_sb = MagicMock()
    mock_auth = MagicMock()
    mock_user_response = MagicMock()

    mock_sb.auth = mock_auth
    mock_auth.get_user.return_value = mock_user_response
    mock_user_response.user = None  # Sem usuário

    with pytest.raises(LookupError, match="Usuario autenticado nao encontrado"):
        fetch_current_user_id(mock_sb)


def test_fetch_current_user_id_raises_when_user_has_no_id():
    """Testa que lança erro quando usuário não tem ID."""
    mock_sb = MagicMock()
    mock_auth = MagicMock()
    mock_user_response = MagicMock()
    mock_user_obj = MagicMock()

    mock_sb.auth = mock_auth
    mock_auth.get_user.return_value = mock_user_response
    mock_user_response.user = mock_user_obj
    mock_user_obj.id = None  # ID None

    with pytest.raises(LookupError, match="Usuario autenticado nao encontrado"):
        fetch_current_user_id(mock_sb)


def test_fetch_current_user_id_raises_when_user_missing_id_attribute():
    """Testa que lança erro quando user não tem atributo id."""
    mock_sb = MagicMock()
    mock_auth = MagicMock()
    mock_user_response = MagicMock()
    mock_user_obj = Mock(spec=[])  # Sem atributo id

    mock_sb.auth = mock_auth
    mock_auth.get_user.return_value = mock_user_response
    mock_user_response.user = mock_user_obj

    with pytest.raises(LookupError, match="Usuario autenticado nao encontrado"):
        fetch_current_user_id(mock_sb)


def test_fetch_current_user_id_converts_to_string():
    """Testa que user_id é convertido para string."""
    mock_sb = MagicMock()
    mock_auth = MagicMock()
    mock_user_response = MagicMock()
    mock_user_obj = MagicMock()

    mock_sb.auth = mock_auth
    mock_auth.get_user.return_value = mock_user_response
    mock_user_response.user = mock_user_obj
    mock_user_obj.id = 12345  # ID como int

    result = fetch_current_user_id(mock_sb)

    assert result == "12345"
    assert isinstance(result, str)


# --- Testes de fetch_org_id_for_user ---


def test_fetch_org_id_for_user_success():
    """Testa fetch de org_id para usuário."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.limit.return_value = mock_limit

    mock_execute.data = [{"org_id": "org-xyz-789"}]
    mock_limit.execute.return_value = mock_execute

    result = fetch_org_id_for_user(mock_sb, user_id="user-123")

    assert result == "org-xyz-789"
    mock_sb.table.assert_called_once_with("memberships")
    mock_table.select.assert_called_once_with("org_id")
    mock_select.eq.assert_called_once_with("user_id", "user-123")
    mock_eq.limit.assert_called_once_with(1)


def test_fetch_org_id_for_user_raises_when_no_membership():
    """Testa que lança erro quando não há membership."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.limit.return_value = mock_limit

    mock_execute.data = []  # Sem dados
    mock_limit.execute.return_value = mock_execute

    with pytest.raises(LookupError, match="Membership sem org_id para o usuario atual"):
        fetch_org_id_for_user(mock_sb, user_id="user-456")


def test_fetch_org_id_for_user_raises_when_org_id_empty():
    """Testa que lança erro quando org_id está vazio."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.limit.return_value = mock_limit

    mock_execute.data = [{"org_id": ""}]  # org_id vazio
    mock_limit.execute.return_value = mock_execute

    with pytest.raises(LookupError, match="Membership sem org_id para o usuario atual"):
        fetch_org_id_for_user(mock_sb, user_id="user-789")


def test_fetch_org_id_for_user_raises_when_org_id_none():
    """Testa que lança erro quando org_id é None."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.limit.return_value = mock_limit

    mock_execute.data = [{"org_id": None}]  # org_id None
    mock_limit.execute.return_value = mock_execute

    with pytest.raises(LookupError, match="Membership sem org_id para o usuario atual"):
        fetch_org_id_for_user(mock_sb, user_id="user-999")


def test_fetch_org_id_for_user_handles_none_data():
    """Testa fetch_org_id quando data é None."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.limit.return_value = mock_limit

    mock_execute.data = None  # Data None
    mock_limit.execute.return_value = mock_execute

    with pytest.raises(LookupError, match="Membership sem org_id para o usuario atual"):
        fetch_org_id_for_user(mock_sb, user_id="user-aaa")


def test_fetch_org_id_for_user_converts_to_string():
    """Testa que org_id é convertido para string."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.limit.return_value = mock_limit

    mock_execute.data = [{"org_id": 555}]  # org_id como int
    mock_limit.execute.return_value = mock_execute

    result = fetch_org_id_for_user(mock_sb, user_id="user-bbb")

    assert result == "555"
    assert isinstance(result, str)
