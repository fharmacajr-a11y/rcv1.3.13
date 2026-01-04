# -*- coding: utf-8 -*-
"""Unit tests for tasks service (create_task function)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.data.domain_types import RCTaskRow
from src.features.tasks.service import create_task


@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase para testes."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()

    # Configura o encadeamento de chamadas
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute

    return mock_client, mock_execute


def test_create_task_minimal_params(mock_supabase_client):
    """Testa criação de tarefa com parâmetros mínimos."""
    mock_client, mock_execute = mock_supabase_client

    # Simula resposta do Supabase com datetime real
    created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    expected_task: RCTaskRow = {
        "id": "task-123",
        "org_id": "org-456",
        "created_by": "user-789",
        "title": "Minha tarefa",
        "description": None,
        "priority": "normal",
        "due_date": date.today(),
        "assigned_to": None,
        "client_id": None,
        "status": "pending",
        "created_at": created_at,
        "updated_at": updated_at,
        "completed_at": None,
    }
    mock_execute.data = [expected_task]

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        result = create_task(
            org_id="org-456",
            created_by="user-789",
            title="Minha tarefa",
        )

    # Verifica que insert foi chamado com os dados corretos
    mock_client.table.assert_called_once_with("rc_tasks")

    call_args = mock_client.table().insert.call_args
    assert call_args is not None
    insert_data = call_args[0][0]

    assert insert_data["org_id"] == "org-456"
    assert insert_data["created_by"] == "user-789"
    assert insert_data["title"] == "Minha tarefa"
    assert insert_data["priority"] == "normal"
    assert insert_data["status"] == "pending"
    assert insert_data["due_date"] == date.today().isoformat()

    # Verifica retorno
    assert result == expected_task


def test_create_task_all_params(mock_supabase_client):
    """Testa criação de tarefa com todos os parâmetros."""
    mock_client, mock_execute = mock_supabase_client

    # Simula resposta do Supabase com datetime real
    created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    test_due_date = date(2024, 12, 31)
    expected_task: RCTaskRow = {
        "id": "task-abc",
        "org_id": "org-xyz",
        "created_by": "user-123",
        "title": "Tarefa completa",
        "description": "Descrição detalhada",
        "priority": "high",
        "due_date": test_due_date,
        "assigned_to": "user-456",
        "client_id": 789,
        "status": "pending",
        "created_at": created_at,
        "updated_at": updated_at,
        "completed_at": None,
    }
    mock_execute.data = [expected_task]

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        result = create_task(
            org_id="org-xyz",
            created_by="user-123",
            title="Tarefa completa",
            description="Descrição detalhada",
            priority="high",
            due_date=test_due_date,
            assigned_to="user-456",
            client_id=789,
        )

    # Verifica que insert foi chamado com os dados corretos
    call_args = mock_client.table().insert.call_args
    assert call_args is not None
    insert_data = call_args[0][0]

    assert insert_data["org_id"] == "org-xyz"
    assert insert_data["created_by"] == "user-123"
    assert insert_data["title"] == "Tarefa completa"
    assert insert_data["description"] == "Descrição detalhada"
    assert insert_data["priority"] == "high"
    assert insert_data["due_date"] == test_due_date.isoformat()
    assert insert_data["assigned_to"] == "user-456"
    assert insert_data["client_id"] == 789
    assert insert_data["status"] == "pending"

    # Verifica retorno
    assert result == expected_task


def test_create_task_empty_title_raises_error():
    """Testa que título vazio levanta ValueError."""
    with pytest.raises(ValueError, match="Título da tarefa não pode ser vazio"):
        create_task(
            org_id="org-123",
            created_by="user-456",
            title="",
        )

    with pytest.raises(ValueError, match="Título da tarefa não pode ser vazio"):
        create_task(
            org_id="org-123",
            created_by="user-456",
            title="   ",  # Apenas espaços
        )


def test_create_task_priority_normalization(mock_supabase_client):
    """Testa normalização de prioridades."""
    mock_client, mock_execute = mock_supabase_client

    test_cases = [
        ("low", "low"),
        ("LOW", "low"),
        ("baixa", "low"),
        ("normal", "normal"),
        ("NORMAL", "normal"),
        ("high", "high"),
        ("HIGH", "high"),
        ("alta", "high"),
        ("urgent", "urgent"),
        ("URGENT", "urgent"),
        ("urgente", "urgent"),
    ]

    for input_priority, expected_priority in test_cases:
        # Reseta mocks
        mock_client.reset_mock()

        created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        mock_execute.data = [
            {
                "id": "task-test",
                "org_id": "org-test",
                "created_by": "user-test",
                "title": "Test",
                "priority": expected_priority,
                "status": "pending",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        ]

        with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
            create_task(
                org_id="org-test",
                created_by="user-test",
                title="Test",
                priority=input_priority,
            )

        call_args = mock_client.table().insert.call_args
        insert_data = call_args[0][0]
        assert (
            insert_data["priority"] == expected_priority
        ), f"Failed for input '{input_priority}', expected '{expected_priority}'"


def test_create_task_invalid_priority_raises_error():
    """Testa que prioridade inválida levanta ValueError."""
    with pytest.raises(ValueError, match="Prioridade .* inválida"):
        create_task(
            org_id="org-123",
            created_by="user-456",
            title="Test",
            priority="invalid_priority",
        )


def test_create_task_strips_title_and_description(mock_supabase_client):
    """Testa que título e descrição são stripped."""
    mock_client, mock_execute = mock_supabase_client

    created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    mock_execute.data = [
        {
            "id": "task-test",
            "org_id": "org-test",
            "created_by": "user-test",
            "title": "Título limpo",
            "description": "Descrição limpa",
            "priority": "normal",
            "status": "pending",
            "created_at": created_at,
            "updated_at": updated_at,
        }
    ]

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        create_task(
            org_id="org-test",
            created_by="user-test",
            title="  Título limpo  ",
            description="  Descrição limpa  ",
        )

    call_args = mock_client.table().insert.call_args
    insert_data = call_args[0][0]

    assert insert_data["title"] == "Título limpo"
    assert insert_data["description"] == "Descrição limpa"


def test_create_task_default_due_date(mock_supabase_client):
    """Testa que due_date usa hoje como default."""
    mock_client, mock_execute = mock_supabase_client

    created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    updated_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    mock_execute.data = [
        {
            "id": "task-test",
            "org_id": "org-test",
            "created_by": "user-test",
            "title": "Test",
            "priority": "normal",
            "due_date": date.today(),
            "status": "pending",
            "created_at": created_at,
            "updated_at": updated_at,
        }
    ]

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        create_task(
            org_id="org-test",
            created_by="user-test",
            title="Test",
        )

    call_args = mock_client.table().insert.call_args
    insert_data = call_args[0][0]

    assert insert_data["due_date"] == date.today().isoformat()


def test_create_task_supabase_error_raises_runtime_error(mock_supabase_client):
    """Testa que erros do Supabase são convertidos em RuntimeError."""
    mock_client, mock_execute = mock_supabase_client

    # Simula erro do Supabase
    from src.features.tasks.service import PostgrestAPIError

    mock_client.table().insert().execute.side_effect = PostgrestAPIError({"message": "Database error", "code": "500"})

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Erro ao criar tarefa"):
            create_task(
                org_id="org-test",
                created_by="user-test",
                title="Test",
            )


def test_create_task_no_data_returned_raises_error(mock_supabase_client):
    """Testa que falta de dados retornados levanta RuntimeError."""
    mock_client, mock_execute = mock_supabase_client

    # Simula resposta vazia
    mock_execute.data = []

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Nenhum dado retornado"):
            create_task(
                org_id="org-test",
                created_by="user-test",
                title="Test",
            )


def test_create_task_rls_error_raises_friendly_message(mock_supabase_client):
    """Testa que erros de RLS geram mensagem amigável."""
    mock_client, mock_execute = mock_supabase_client

    # Simula erro RLS do Supabase (código 42501)
    from src.features.tasks.service import PostgrestAPIError

    mock_client.table().insert().execute.side_effect = PostgrestAPIError(
        {"message": 'new row violates row-level security policy for table "rc_tasks"', "code": "42501"}
    )

    with patch("src.features.tasks.service.get_supabase_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="permissão negada pela política de segurança"):
            create_task(
                org_id="org-test",
                created_by="user-test",
                title="Test",
            )
