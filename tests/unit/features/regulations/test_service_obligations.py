# -*- coding: utf-8 -*-
"""Unit tests for regulations service."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from data.domain_types import RegObligationRow
from src.features.regulations.service import (
    create_obligation,
    delete_obligation,
    list_obligations_for_client,
    update_obligation,
)


@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase para testes."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_update = MagicMock()
    mock_delete = MagicMock()
    mock_execute = MagicMock()

    # Configura o encadeamento de chamadas
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_table.update.return_value = mock_update
    mock_table.delete.return_value = mock_delete
    mock_insert.execute.return_value = mock_execute
    mock_update.eq.return_value = mock_update
    mock_update.execute.return_value = mock_execute
    mock_delete.eq.return_value = mock_delete
    mock_delete.execute.return_value = mock_execute

    return mock_client, mock_execute


def test_list_obligations_for_client():
    """Testa listagem de obrigações filtradas por cliente."""
    mock_obligations: list[RegObligationRow] = [
        {
            "id": "obl-1",
            "org_id": "org-123",
            "client_id": 1,
            "kind": "SNGPC",
            "title": "SNGPC Mensal",
            "due_date": date(2025, 12, 10),
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
        },
        {
            "id": "obl-2",
            "org_id": "org-123",
            "client_id": 2,
            "kind": "FARMACIA_POPULAR",
            "title": "FP Trimestral",
            "due_date": date(2025, 12, 15),
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
        },
        {
            "id": "obl-3",
            "org_id": "org-123",
            "client_id": 1,
            "kind": "SIFAP",
            "title": "SIFAP Anual",
            "due_date": date(2025, 12, 20),
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
        },
    ]

    with patch("src.features.regulations.service.list_obligations_for_org", return_value=mock_obligations):
        result = list_obligations_for_client("org-123", 1)

    # Deve retornar apenas obrigações do client_id=1
    assert len(result) == 2
    assert result[0]["id"] == "obl-1"
    assert result[1]["id"] == "obl-3"
    assert all(obl["client_id"] == 1 for obl in result)


def test_create_obligation_minimal_params(mock_supabase_client):
    """Testa criação de obrigação com parâmetros mínimos."""
    mock_client, mock_execute = mock_supabase_client

    test_due_date = date(2025, 12, 31)
    created_at = datetime(2025, 12, 1, 10, 0, 0, tzinfo=timezone.utc)

    expected_obligation: RegObligationRow = {
        "id": "obl-abc",
        "org_id": "org-123",
        "client_id": 5,
        "kind": "SNGPC",
        "title": "Envio SNGPC Dezembro",
        "due_date": test_due_date,
        "status": "pending",
        "created_by": "user-456",
        "created_at": created_at,
        "updated_at": created_at,
    }
    mock_execute.data = [expected_obligation]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        result = create_obligation(
            org_id="org-123",
            created_by="user-456",
            client_id=5,
            kind="SNGPC",
            title="Envio SNGPC Dezembro",
            due_date=test_due_date,
        )

    # Verifica que insert foi chamado
    mock_client.table.assert_called_once_with("reg_obligations")

    call_args = mock_client.table().insert.call_args
    assert call_args is not None
    insert_data = call_args[0][0]

    assert insert_data["org_id"] == "org-123"
    assert insert_data["client_id"] == 5
    assert insert_data["kind"] == "SNGPC"
    assert insert_data["title"] == "Envio SNGPC Dezembro"
    assert insert_data["due_date"] == test_due_date.isoformat()
    assert insert_data["status"] == "pending"
    assert insert_data["created_by"] == "user-456"

    # Verifica retorno
    assert result == expected_obligation


def test_create_obligation_all_params(mock_supabase_client):
    """Testa criação de obrigação com todos os parâmetros."""
    mock_client, mock_execute = mock_supabase_client

    test_due_date = date(2025, 12, 31)
    ref_start = date(2025, 12, 1)
    ref_end = date(2025, 12, 31)
    created_at = datetime(2025, 12, 1, 10, 0, 0, tzinfo=timezone.utc)

    expected_obligation: RegObligationRow = {
        "id": "obl-xyz",
        "org_id": "org-456",
        "client_id": 10,
        "kind": "FARMACIA_POPULAR",
        "title": "Relatório FP Q4",
        "reference_start": ref_start,
        "reference_end": ref_end,
        "due_date": test_due_date,
        "status": "pending",
        "created_by": "user-789",
        "created_at": created_at,
        "updated_at": created_at,
        "notes": "Importante: verificar estoque",
    }
    mock_execute.data = [expected_obligation]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        result = create_obligation(
            org_id="org-456",
            created_by="user-789",
            client_id=10,
            kind="FARMACIA_POPULAR",
            title="Relatório FP Q4",
            due_date=test_due_date,
            status="pending",
            reference_start=ref_start,
            reference_end=ref_end,
            notes="Importante: verificar estoque",
        )

    call_args = mock_client.table().insert.call_args
    insert_data = call_args[0][0]

    assert insert_data["reference_start"] == ref_start.isoformat()
    assert insert_data["reference_end"] == ref_end.isoformat()
    assert insert_data["notes"] == "Importante: verificar estoque"
    assert result == expected_obligation


def test_create_obligation_normalizes_kind(mock_supabase_client):
    """Testa que kind é normalizado para uppercase."""
    mock_client, mock_execute = mock_supabase_client

    mock_execute.data = [
        {
            "id": "obl-1",
            "org_id": "org-1",
            "client_id": 1,
            "kind": "SNGPC",
            "title": "Test",
            "due_date": date.today(),
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        from typing import cast
        from src.features.regulations.service import ObligationKind

        create_obligation(
            org_id="org-1",
            created_by="user-1",
            client_id=1,
            kind=cast(ObligationKind, "sngpc"),  # lowercase - será normalizado
            title="Test",
            due_date=date.today(),
        )

    call_args = mock_client.table().insert.call_args
    insert_data = call_args[0][0]
    assert insert_data["kind"] == "SNGPC"


def test_update_obligation_single_field(mock_supabase_client):
    """Testa atualização de um único campo."""
    mock_client, mock_execute = mock_supabase_client

    updated_obligation: RegObligationRow = {
        "id": "obl-123",
        "org_id": "org-456",
        "client_id": 5,
        "kind": "SNGPC",
        "title": "Título atualizado",
        "due_date": date(2025, 12, 31),
        "status": "pending",
        "created_by": "user-1",
        "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 12, 2, tzinfo=timezone.utc),
    }
    mock_execute.data = [updated_obligation]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        result = update_obligation(
            org_id="org-456",
            obligation_id="obl-123",
            title="Título atualizado",
        )

    # Verifica chamadas
    mock_client.table.assert_called_once_with("reg_obligations")
    mock_update = mock_client.table().update
    mock_update.assert_called_once()

    update_data = mock_update.call_args[0][0]
    assert "title" in update_data
    assert update_data["title"] == "Título atualizado"
    assert "updated_at" in update_data

    # Verifica retorno
    assert result == updated_obligation


def test_update_obligation_status_to_done_sets_completed_at(mock_supabase_client):
    """Testa que atualizar status para 'done' define completed_at."""
    mock_client, mock_execute = mock_supabase_client

    mock_execute.data = [
        {
            "id": "obl-123",
            "org_id": "org-456",
            "client_id": 5,
            "kind": "SNGPC",
            "title": "Test",
            "due_date": date.today(),
            "status": "done",
            "created_by": "user-1",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
        }
    ]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        update_obligation(
            org_id="org-456",
            obligation_id="obl-123",
            status="done",
        )

    update_data = mock_client.table().update.call_args[0][0]
    assert update_data["status"] == "done"
    assert "completed_at" in update_data


def test_delete_obligation(mock_supabase_client):
    """Testa exclusão de obrigação."""
    mock_client, mock_execute = mock_supabase_client

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        delete_obligation("org-123", "obl-456")

    # Verifica chamadas
    mock_client.table.assert_called_once_with("reg_obligations")
    mock_delete = mock_client.table().delete
    mock_delete.assert_called_once()

    # Verifica filtros eq
    assert mock_delete().eq.call_count == 2


def test_create_obligation_normalizes_status_portuguese(mock_supabase_client):
    """Testa que create_obligation normaliza status PT-BR para inglês."""
    mock_client, mock_execute = mock_supabase_client

    test_due_date = date(2025, 12, 31)
    mock_execute.data = [
        {
            "id": "obl-new",
            "org_id": "org-123",
            "client_id": 10,
            "kind": "SNGPC",
            "title": "Teste PT-BR",
            "due_date": test_due_date,
            "status": "pending",  # Deve ser normalizado
            "created_by": "user-1",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        result = create_obligation(
            org_id="org-123",
            created_by="user-1",
            client_id=10,
            kind="SNGPC",
            title="Teste PT-BR",
            due_date=test_due_date,
            status="Pendente",  # PT-BR
        )

    # Verifica que insert foi chamado com status normalizado
    insert_data = mock_client.table().insert.call_args[0][0]
    assert insert_data["status"] == "pending"
    assert result["status"] == "pending"


def test_create_obligation_normalizes_status_variations(mock_supabase_client):
    """Testa normalização de várias variações de status PT-BR."""
    mock_client, mock_execute = mock_supabase_client

    test_cases = [
        ("Concluída", "done"),
        ("Concluido", "done"),
        ("CONCLUIDA", "done"),
        ("Atrasada", "overdue"),
        ("ATRASADA", "overdue"),
        ("Cancelada", "canceled"),
        ("CANCELADO", "canceled"),
    ]

    for pt_status, expected_en in test_cases:
        mock_execute.data = [
            {
                "id": "obl-test",
                "org_id": "org-123",
                "client_id": 10,
                "kind": "SNGPC",
                "title": "Test",
                "due_date": date.today(),
                "status": expected_en,
                "created_by": "user-1",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]

        with patch("src.features.regulations.service._get_client", return_value=mock_client):
            create_obligation(
                org_id="org-123",
                created_by="user-1",
                client_id=10,
                kind="SNGPC",
                title="Test",
                due_date=date.today(),
                status=pt_status,
            )

        insert_data = mock_client.table().insert.call_args[0][0]
        assert insert_data["status"] == expected_en, f"Failed for {pt_status}"


def test_create_obligation_normalizes_kind_portuguese(mock_supabase_client):
    """Testa que create_obligation normaliza kind PT-BR para canônico."""
    mock_client, mock_execute = mock_supabase_client

    test_due_date = date(2025, 12, 31)
    mock_execute.data = [
        {
            "id": "obl-new",
            "org_id": "org-123",
            "client_id": 10,
            "kind": "FARMACIA_POPULAR",  # Deve ser normalizado
            "title": "Teste Kind PT-BR",
            "due_date": test_due_date,
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        result = create_obligation(
            org_id="org-123",
            created_by="user-1",
            client_id=10,
            kind="Farmácia Popular",  # PT-BR
            title="Teste Kind PT-BR",
            due_date=test_due_date,
            status="pending",
        )

    # Verifica que insert foi chamado com kind normalizado
    insert_data = mock_client.table().insert.call_args[0][0]
    assert insert_data["kind"] == "FARMACIA_POPULAR"
    assert result["kind"] == "FARMACIA_POPULAR"


def test_create_obligation_normalizes_kind_variations(mock_supabase_client):
    """Testa normalização de várias variações de kind PT-BR."""
    mock_client, mock_execute = mock_supabase_client

    test_cases = [
        ("Farmácia Popular", "FARMACIA_POPULAR"),
        ("Farmacia Popular", "FARMACIA_POPULAR"),
        ("FARMACIA POPULAR", "FARMACIA_POPULAR"),
        ("Sifap", "SIFAP"),
        ("sifap", "SIFAP"),
        ("Licença Sanitária", "LICENCA_SANITARIA"),
        ("Licenca Sanitaria", "LICENCA_SANITARIA"),
        ("Outro", "OUTRO"),
        ("outro", "OUTRO"),
    ]

    for pt_kind, expected_en in test_cases:
        mock_execute.data = [
            {
                "id": "obl-test",
                "org_id": "org-123",
                "client_id": 10,
                "kind": expected_en,
                "title": "Test",
                "due_date": date.today(),
                "status": "pending",
                "created_by": "user-1",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]

        with patch("src.features.regulations.service._get_client", return_value=mock_client):
            create_obligation(
                org_id="org-123",
                created_by="user-1",
                client_id=10,
                kind=pt_kind,
                title="Test",
                due_date=date.today(),
                status="pending",
            )

        insert_data = mock_client.table().insert.call_args[0][0]
        assert insert_data["kind"] == expected_en, f"Failed for {pt_kind}"


def test_update_obligation_normalizes_status_portuguese(mock_supabase_client):
    """Testa que update_obligation normaliza status PT-BR."""
    mock_client, mock_execute = mock_supabase_client

    mock_execute.data = [
        {
            "id": "obl-123",
            "org_id": "org-456",
            "client_id": 5,
            "kind": "SNGPC",
            "title": "Test",
            "due_date": date.today(),
            "status": "done",
            "created_by": "user-1",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
        }
    ]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        update_obligation(
            org_id="org-456",
            obligation_id="obl-123",
            status="Concluída",  # PT-BR
        )

    update_data = mock_client.table().update.call_args[0][0]
    assert update_data["status"] == "done"
    assert "completed_at" in update_data  # deve definir completed_at


def test_update_obligation_normalizes_kind_portuguese(mock_supabase_client):
    """Testa que update_obligation normaliza kind PT-BR."""
    mock_client, mock_execute = mock_supabase_client

    mock_execute.data = [
        {
            "id": "obl-123",
            "org_id": "org-456",
            "client_id": 5,
            "kind": "LICENCA_SANITARIA",
            "title": "Test",
            "due_date": date.today(),
            "status": "pending",
            "created_by": "user-1",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    with patch("src.features.regulations.service._get_client", return_value=mock_client):
        update_obligation(
            org_id="org-456",
            obligation_id="obl-123",
            kind="Licença Sanitária",  # PT-BR
        )

    update_data = mock_client.table().update.call_args[0][0]
    assert update_data["kind"] == "LICENCA_SANITARIA"
