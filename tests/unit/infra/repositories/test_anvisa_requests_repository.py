"""Testes do repositório anvisa_requests_repository.

Valida operações CRUD com mocks do Supabase.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


def test_list_requests_returns_data(monkeypatch):
    """list_requests deve retornar lista de demandas do Supabase."""
    from infra.repositories.anvisa_requests_repository import list_requests

    # Mock do supabase
    mock_response = Mock()
    mock_response.data = [
        {
            "id": 1,
            "client_id": 100,
            "request_type": "Alteração do Responsável Legal",
            "status": "draft",
            "clients": {
                "razao_social": "Farmácia ABC",
                "cnpj": "11.222.333/0001-44",
            },
        },
        {
            "id": 2,
            "client_id": 200,
            "request_type": "Alteração de Porte",
            "status": "in_progress",
            "clients": {
                "razao_social": "Drogaria XYZ",
                "cnpj": "55.666.777/0001-88",
            },
        },
    ]

    mock_execute = Mock(return_value=mock_response)
    mock_order = Mock(return_value=Mock(execute=mock_execute))
    mock_eq = Mock(return_value=Mock(order=mock_order))
    mock_select = Mock(return_value=Mock(eq=mock_eq))
    mock_table = Mock(return_value=Mock(select=mock_select))

    # Mock do módulo supabase_client
    import infra.supabase_client as supabase_module

    mock_supabase = Mock()
    mock_supabase.table = mock_table
    monkeypatch.setattr(supabase_module, "supabase", mock_supabase)

    # Chamar função
    result = list_requests("org-test-123")

    # Verificar resultado
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["client_id"] == 100
    assert result[0]["clients"]["razao_social"] == "Farmácia ABC"
    assert result[1]["id"] == 2
    assert result[1]["request_type"] == "Alteração de Porte"

    # Verificar que chamou table e métodos corretos
    mock_table.assert_called_once_with("client_anvisa_requests")
    mock_select.assert_called_once()
    mock_eq.assert_called_once_with("org_id", "org-test-123")


def test_create_request_inserts_and_returns_data(monkeypatch):
    """create_request deve inserir demanda e retornar registro criado."""
    from infra.repositories.anvisa_requests_repository import create_request

    # Mock do supabase
    mock_response = Mock()
    mock_response.data = [
        {
            "id": 999,
            "org_id": "org-test-456",
            "client_id": 789,
            "request_type": "Alteração da Razão Social",
            "status": "draft",
        }
    ]

    mock_execute = Mock(return_value=mock_response)
    mock_insert = Mock(return_value=Mock(execute=mock_execute))
    mock_table = Mock(return_value=Mock(insert=mock_insert))

    # Mock do módulo supabase_client
    import infra.supabase_client as supabase_module

    mock_supabase = Mock()
    mock_supabase.table = mock_table
    monkeypatch.setattr(supabase_module, "supabase", mock_supabase)

    # Chamar função
    result = create_request(
        org_id="org-test-456",
        client_id=789,
        request_type="Alteração da Razão Social",
        status="draft",
    )

    # Verificar resultado
    assert result["id"] == 999
    assert result["client_id"] == 789
    assert result["request_type"] == "Alteração da Razão Social"
    assert result["status"] == "draft"

    # Verificar que chamou insert com dados corretos
    mock_table.assert_called_once_with("client_anvisa_requests")
    mock_insert.assert_called_once()

    # Verificar payload do insert
    insert_call_args = mock_insert.call_args[0][0]
    assert insert_call_args["org_id"] == "org-test-456"
    assert insert_call_args["client_id"] == 789  # BIGINT
    assert insert_call_args["request_type"] == "Alteração da Razão Social"
    assert insert_call_args["status"] == "draft"


def test_create_request_raises_on_empty_data(monkeypatch):
    """create_request deve lançar exceção se insert retornar vazio (RLS)."""
    from infra.repositories.anvisa_requests_repository import create_request

    # Mock do supabase - retorna data vazia (bloqueado por RLS)
    mock_response = Mock()
    mock_response.data = []

    mock_execute = Mock(return_value=mock_response)
    mock_insert = Mock(return_value=Mock(execute=mock_execute))
    mock_table = Mock(return_value=Mock(insert=mock_insert))

    # Mock do módulo supabase_client
    import infra.supabase_client as supabase_module

    mock_supabase = Mock()
    mock_supabase.table = mock_table
    monkeypatch.setattr(supabase_module, "supabase", mock_supabase)

    # Chamar função e verificar exceção
    with pytest.raises(RuntimeError) as exc_info:
        create_request(
            org_id="org-test-789",
            client_id=999,
            request_type="Teste",
            status="draft",
        )

    assert "INSERT bloqueado por RLS" in str(exc_info.value)


def test_update_request_status_updates_and_returns(monkeypatch):
    """update_request_status deve atualizar status da demanda."""
    from infra.repositories.anvisa_requests_repository import update_request_status

    # Mock do response do Supabase
    mock_response = Mock()
    mock_response.data = [{"id": "req-555", "status": "done"}]
    mock_response.count = 1

    # Mock do chain: table().update().eq().eq().execute()
    mock_execute = Mock()
    mock_execute.execute.return_value = mock_response

    mock_eq2 = Mock()
    mock_eq2.eq.return_value = mock_execute

    mock_eq1 = Mock()
    mock_eq1.eq.return_value = mock_eq2

    mock_update = Mock()
    mock_update.update.return_value = mock_eq1

    mock_table = Mock()
    mock_table.table.return_value = mock_update

    # Mock do módulo supabase_client
    import infra.supabase_client as supabase_module

    monkeypatch.setattr(supabase_module, "supabase", mock_table)

    # Mock das funções auxiliares
    import infra.repositories.anvisa_requests_repository as repo_module

    monkeypatch.setattr(repo_module, "_get_supabase_and_user", lambda: (mock_table, "user-123"))
    monkeypatch.setattr(repo_module, "_resolve_org_id", lambda user_id: "org-456")

    # Chamar função com status válido
    result = update_request_status("req-555", "done")

    # Verificar resultado (retorna bool!)
    assert result is True

    # Verificar chamadas
    mock_table.table.assert_called_once_with("client_anvisa_requests")
    mock_update.update.assert_called_once_with({"status": "done"})

    # Verificar que os dois eq foram chamados (id e depois org_id)
    mock_eq1.eq.assert_called_once_with("id", "req-555")
    mock_eq2.eq.assert_called_once_with("org_id", "org-456")


def test_get_supabase_and_user_returns_tuple(monkeypatch):
    """_get_supabase_and_user deve retornar tupla (supabase, user_id)."""
    from infra.repositories.anvisa_requests_repository import _get_supabase_and_user

    # Mock do supabase auth
    mock_user = Mock()
    mock_user.id = "user-abc-123"

    mock_auth_response = Mock()
    mock_auth_response.user = mock_user

    mock_auth = Mock()
    mock_auth.get_user = Mock(return_value=mock_auth_response)

    # Mock do módulo supabase_client
    import infra.supabase_client as supabase_module

    mock_supabase = Mock()
    mock_supabase.auth = mock_auth
    monkeypatch.setattr(supabase_module, "supabase", mock_supabase)

    # Chamar função
    supabase, user_id = _get_supabase_and_user()

    # Verificar resultado
    assert user_id == "user-abc-123"
    assert supabase is mock_supabase


def test_resolve_org_id_returns_org_id(monkeypatch):
    """_resolve_org_id deve retornar org_id do usuário via memberships."""
    from infra.repositories.anvisa_requests_repository import _resolve_org_id

    # Mock do supabase
    mock_response = Mock()
    mock_response.data = [{"org_id": "org-xyz-999"}]

    mock_execute = Mock(return_value=mock_response)
    mock_limit = Mock(return_value=Mock(execute=mock_execute))
    mock_eq = Mock(return_value=Mock(limit=mock_limit))
    mock_select = Mock(return_value=Mock(eq=mock_eq))
    mock_table = Mock(return_value=Mock(select=mock_select))

    # Mock do módulo supabase_client
    import infra.supabase_client as supabase_module

    mock_supabase = Mock()
    mock_supabase.table = mock_table
    monkeypatch.setattr(supabase_module, "supabase", mock_supabase)

    # Chamar função
    org_id = _resolve_org_id("user-test-456")

    # Verificar resultado
    assert org_id == "org-xyz-999"

    # Verificar chamadas
    mock_table.assert_called_once_with("memberships")
    mock_select.assert_called_once_with("org_id")
    mock_eq.assert_called_once_with("user_id", "user-test-456")
    mock_limit.assert_called_once_with(1)
