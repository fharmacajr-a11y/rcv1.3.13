"""Testes unitários para AnvisaService (headless).

Testa lógica de negócio de:
- Validação de duplicados (mesmo tipo + status aberto)
- Listagem e filtragem por cliente
- Normalização de tipos e status (case-insensitive + aliases)
"""

from __future__ import annotations

import pytest
from typing import Any

from src.modules.anvisa.services.anvisa_service import AnvisaService


class FakeAnvisaRepository:
    """Mock do repository para testes headless."""

    def __init__(self) -> None:
        """Inicializa com dados de teste."""
        self.requests: list[dict[str, Any]] = [
            # Cliente 123: 3 demandas (2 abertas, 1 fechada)
            {
                "id": "req-1",
                "client_id": "123",
                "request_type": "Alteração do Responsável Legal",
                "status": "draft",
            },
            {
                "id": "req-2",
                "client_id": "123",
                "request_type": "Alteração do Responsável Técnico",
                "status": "submitted",
            },
            {
                "id": "req-3",
                "client_id": "123",
                "request_type": "Alteração da Razão Social",
                "status": "done",
            },
            # Cliente 456: 2 demandas (1 aberta, 1 fechada)
            {
                "id": "req-4",
                "client_id": "456",
                "request_type": "Alteração de Porte",
                "status": "in_progress",
            },
            {
                "id": "req-5",
                "client_id": "456",
                "request_type": "Associação ao SNGPC",
                "status": "canceled",
            },
        ]

    def list_requests(self, org_id: str) -> list[dict[str, Any]]:
        """Lista todas as demandas (mock)."""
        return self.requests


@pytest.fixture
def fake_repo() -> FakeAnvisaRepository:
    """Fixture do repository fake."""
    return FakeAnvisaRepository()


@pytest.fixture
def service(fake_repo: FakeAnvisaRepository) -> AnvisaService:
    """Fixture do service com repository injetado."""
    return AnvisaService(repository=fake_repo)


# ===== Testes de list_requests_for_client =====


def test_list_requests_for_client_filters_correctly(service: AnvisaService) -> None:
    """Deve filtrar demandas por client_id."""
    requests_123 = service.list_requests_for_client("org-1", "123")
    assert len(requests_123) == 3
    assert all(str(r["client_id"]) == "123" for r in requests_123)

    requests_456 = service.list_requests_for_client("org-1", "456")
    assert len(requests_456) == 2
    assert all(str(r["client_id"]) == "456" for r in requests_456)


def test_list_requests_for_client_no_requests(service: AnvisaService) -> None:
    """Deve retornar lista vazia se cliente não tem demandas."""
    requests = service.list_requests_for_client("org-1", "999")
    assert requests == []


# ===== Testes de check_duplicate_open_request =====


def test_check_duplicate_blocks_same_type_open_draft(service: AnvisaService) -> None:
    """Deve bloquear demanda do mesmo tipo com status draft."""
    dup = service.check_duplicate_open_request("org-1", "123", "Alteração do Responsável Legal")
    assert dup is not None
    assert dup["id"] == "req-1"
    assert dup["status"] == "draft"


def test_check_duplicate_blocks_same_type_open_submitted(service: AnvisaService) -> None:
    """Deve bloquear demanda do mesmo tipo com status submitted."""
    dup = service.check_duplicate_open_request("org-1", "123", "Alteração do Responsável Técnico")
    assert dup is not None
    assert dup["id"] == "req-2"
    assert dup["status"] == "submitted"


def test_check_duplicate_blocks_same_type_open_in_progress(service: AnvisaService) -> None:
    """Deve bloquear demanda do mesmo tipo com status in_progress."""
    dup = service.check_duplicate_open_request("org-1", "456", "Alteração de Porte")
    assert dup is not None
    assert dup["id"] == "req-4"
    assert dup["status"] == "in_progress"


def test_check_duplicate_allows_same_type_closed_done(service: AnvisaService) -> None:
    """Deve permitir demanda do mesmo tipo se anterior está finalizada."""
    dup = service.check_duplicate_open_request("org-1", "123", "Alteração da Razão Social")
    assert dup is None


def test_check_duplicate_allows_same_type_closed_canceled(service: AnvisaService) -> None:
    """Deve permitir demanda do mesmo tipo se anterior está cancelada."""
    dup = service.check_duplicate_open_request("org-1", "456", "Associação ao SNGPC")
    assert dup is None


def test_check_duplicate_allows_different_type(service: AnvisaService) -> None:
    """Deve permitir demanda de tipo diferente."""
    dup = service.check_duplicate_open_request("org-1", "123", "Cancelamento de AFE")
    assert dup is None


def test_check_duplicate_no_requests_for_client(service: AnvisaService) -> None:
    """Deve retornar None se cliente não tem demandas."""
    dup = service.check_duplicate_open_request("org-1", "999", "Alteração de Porte")
    assert dup is None


# ===== Testes de normalização =====


def test_check_duplicate_normalizes_case(service: AnvisaService) -> None:
    """Deve normalizar case do tipo para comparação."""
    # req-1 é "Alteração do Responsável Legal"
    dup = service.check_duplicate_open_request("org-1", "123", "alteração do responsável legal")
    assert dup is not None
    assert dup["id"] == "req-1"

    dup2 = service.check_duplicate_open_request("org-1", "123", "ALTERAÇÃO DO RESPONSÁVEL LEGAL")
    assert dup2 is not None
    assert dup2["id"] == "req-1"


def test_check_duplicate_normalizes_whitespace(service: AnvisaService) -> None:
    """Deve normalizar espaços extras do tipo."""
    dup = service.check_duplicate_open_request("org-1", "123", "  Alteração do Responsável Legal  ")
    assert dup is not None
    assert dup["id"] == "req-1"


def test_is_open_status_with_legacy_alias(service: AnvisaService, fake_repo: FakeAnvisaRepository) -> None:
    """Deve reconhecer status legado como aberto via STATUS_ALIASES."""
    # Adicionar demanda com status legado "aberta" (alias para "draft")
    fake_repo.requests.append(
        {
            "id": "req-legacy",
            "client_id": "789",
            "request_type": "Alteração de Porte",
            "status": "aberta",  # Alias legado
        }
    )

    dup = service.check_duplicate_open_request("org-1", "789", "Alteração de Porte")
    assert dup is not None
    assert dup["id"] == "req-legacy"
    assert dup["status"] == "aberta"


def test_is_open_status_with_em_andamento_alias(service: AnvisaService, fake_repo: FakeAnvisaRepository) -> None:
    """Deve reconhecer 'em andamento' como aberto via STATUS_ALIASES."""
    fake_repo.requests.append(
        {
            "id": "req-em-andamento",
            "client_id": "888",
            "request_type": "Associação ao SNGPC",
            "status": "em andamento",
        }
    )

    dup = service.check_duplicate_open_request("org-1", "888", "Associação ao SNGPC")
    assert dup is not None
    assert dup["id"] == "req-em-andamento"


# ===== Testes de robustez =====


def test_list_requests_handles_repository_exception(fake_repo: FakeAnvisaRepository) -> None:
    """Deve retornar lista vazia se repository lança exceção."""

    class BrokenRepository:
        def list_requests(self, org_id: str) -> list[dict[str, Any]]:
            raise RuntimeError("Database error")

    service = AnvisaService(repository=BrokenRepository())  # type: ignore[arg-type]
    requests = service.list_requests_for_client("org-1", "123")
    assert requests == []


def test_check_duplicate_handles_repository_exception() -> None:
    """Deve retornar None se repository lança exceção."""

    class BrokenRepository:
        def list_requests(self, org_id: str) -> list[dict[str, Any]]:
            raise RuntimeError("Database error")

    service = AnvisaService(repository=BrokenRepository())  # type: ignore[arg-type]
    dup = service.check_duplicate_open_request("org-1", "123", "Alteração de Porte")
    assert dup is None


def test_normalize_type_internal(service: AnvisaService) -> None:
    """Testa método interno _normalize_type."""
    assert service._normalize_type("  Alteração de Porte  ") == "ALTERAÇÃO DE PORTE"
    assert service._normalize_type("alteração de porte") == "ALTERAÇÃO DE PORTE"
    assert service._normalize_type("ALTERAÇÃO DE PORTE") == "ALTERAÇÃO DE PORTE"


def test_is_open_status_internal(service: AnvisaService) -> None:
    """Testa método interno _is_open_status."""
    # Status abertos
    assert service._is_open_status("draft") is True
    assert service._is_open_status("submitted") is True
    assert service._is_open_status("in_progress") is True
    assert service._is_open_status("aberta") is True  # Alias
    assert service._is_open_status("em andamento") is True  # Alias

    # Status fechados
    assert service._is_open_status("done") is False
    assert service._is_open_status("canceled") is False
    assert service._is_open_status("finalizada") is False  # Alias

    # Case-insensitive
    assert service._is_open_status("DRAFT") is True
    assert service._is_open_status("DONE") is False


# ===== Testes de group_by_client =====


def test_group_by_client_groups_correctly(service: AnvisaService, fake_repo: FakeAnvisaRepository) -> None:
    """Deve agrupar demandas por client_id."""
    requests = fake_repo.list_requests("org-1")
    grouped = service.group_by_client(requests)

    assert len(grouped) == 2
    assert "123" in grouped
    assert "456" in grouped
    assert len(grouped["123"]) == 3
    assert len(grouped["456"]) == 2


def test_group_by_client_empty_list(service: AnvisaService) -> None:
    """Deve retornar dicionário vazio para lista vazia."""
    grouped = service.group_by_client([])
    assert grouped == {}


def test_group_by_client_single_client(service: AnvisaService) -> None:
    """Deve agrupar corretamente quando todas as demandas são de um cliente."""
    requests = [
        {"client_id": "999", "request_type": "Tipo A", "status": "draft"},
        {"client_id": "999", "request_type": "Tipo B", "status": "done"},
    ]
    grouped = service.group_by_client(requests)

    assert len(grouped) == 1
    assert "999" in grouped
    assert len(grouped["999"]) == 2


# ===== Testes de check_duplicate_open_in_memory =====


def test_check_duplicate_in_memory_finds_draft(service: AnvisaService) -> None:
    """Deve encontrar duplicado com status draft."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "draft"},
        {"id": "req-2", "request_type": "Alteração de RL", "status": "done"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "Alteração de RT")
    assert dup is not None
    assert dup["id"] == "req-1"


def test_check_duplicate_in_memory_finds_submitted(service: AnvisaService) -> None:
    """Deve encontrar duplicado com status submitted."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "submitted"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "Alteração de RT")
    assert dup is not None
    assert dup["id"] == "req-1"


def test_check_duplicate_in_memory_finds_in_progress(service: AnvisaService) -> None:
    """Deve encontrar duplicado com status in_progress."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "in_progress"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "Alteração de RT")
    assert dup is not None


def test_check_duplicate_in_memory_ignores_done(service: AnvisaService) -> None:
    """Não deve encontrar duplicado se status é done."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "done"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "Alteração de RT")
    assert dup is None


def test_check_duplicate_in_memory_ignores_canceled(service: AnvisaService) -> None:
    """Não deve encontrar duplicado se status é canceled."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "canceled"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "Alteração de RT")
    assert dup is None


def test_check_duplicate_in_memory_normalizes_type(service: AnvisaService) -> None:
    """Deve normalizar tipo para comparação case-insensitive."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "draft"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "alteração de rt")
    assert dup is not None

    dup2 = service.check_duplicate_open_in_memory(demandas, "  ALTERAÇÃO DE RT  ")
    assert dup2 is not None


def test_check_duplicate_in_memory_with_legacy_status(service: AnvisaService) -> None:
    """Deve reconhecer status legado 'aberta' como aberto."""
    demandas = [
        {"id": "req-1", "request_type": "Alteração de RT", "status": "aberta"},
    ]

    dup = service.check_duplicate_open_in_memory(demandas, "Alteração de RT")
    assert dup is not None


def test_check_duplicate_in_memory_empty_list(service: AnvisaService) -> None:
    """Deve retornar None para lista vazia."""
    dup = service.check_duplicate_open_in_memory([], "Alteração de RT")
    assert dup is None


# ===== Testes de summarize_demands =====


def test_summarize_demands_empty(service: AnvisaService) -> None:
    """Deve retornar strings vazias para lista vazia."""
    label, dt = service.summarize_demands([])
    assert label == ""
    assert dt is None


def test_summarize_demands_single(service: AnvisaService) -> None:
    """Deve retornar tipo da demanda para lista com 1 item."""
    demandas = [
        {
            "request_type": "Alteração de RT",
            "status": "draft",
            "updated_at": "2024-01-16T13:00:00+00:00",
        }
    ]

    label, dt = service.summarize_demands(demandas)
    assert label == "Alteração de RT"
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 16


def test_summarize_demands_multiple_all_open(service: AnvisaService) -> None:
    """Deve mostrar '2 demandas (2 em aberto)' quando todas abertas."""
    demandas = [
        {"request_type": "Tipo A", "status": "draft", "updated_at": "2024-01-15T10:00:00Z"},
        {"request_type": "Tipo B", "status": "submitted", "updated_at": "2024-01-16T12:00:00Z"},
    ]

    label, dt = service.summarize_demands(demandas)
    assert label == "2 demandas (2 em aberto)"
    assert dt is not None
    # Deve pegar a data mais recente (16/01)
    assert dt.day == 16


def test_summarize_demands_multiple_mixed(service: AnvisaService) -> None:
    """Deve mostrar '3 demandas (1 em aberto)' quando mix de aberta/fechada."""
    demandas = [
        {"request_type": "Tipo A", "status": "draft", "updated_at": "2024-01-15T10:00:00Z"},
        {"request_type": "Tipo B", "status": "done", "updated_at": "2024-01-16T12:00:00Z"},
        {"request_type": "Tipo C", "status": "canceled", "updated_at": "2024-01-14T08:00:00Z"},
    ]

    label, dt = service.summarize_demands(demandas)
    assert label == "3 demandas (1 em aberto)"
    assert dt is not None


def test_summarize_demands_multiple_all_closed(service: AnvisaService) -> None:
    """Deve mostrar '2 demandas (finalizadas)' quando todas fechadas."""
    demandas = [
        {"request_type": "Tipo A", "status": "done", "updated_at": "2024-01-15T10:00:00Z"},
        {"request_type": "Tipo B", "status": "canceled", "updated_at": "2024-01-16T12:00:00Z"},
    ]

    label, dt = service.summarize_demands(demandas)
    assert label == "2 demandas (finalizadas)"
    assert dt is not None


def test_summarize_demands_uses_created_at_fallback(service: AnvisaService) -> None:
    """Deve usar created_at quando updated_at não existe."""
    demandas = [
        {"request_type": "Tipo A", "status": "draft", "created_at": "2024-01-15T10:00:00Z"},
    ]

    label, dt = service.summarize_demands(demandas)
    assert label == "Tipo A"
    assert dt is not None
    assert dt.day == 15


def test_summarize_demands_handles_z_suffix(service: AnvisaService) -> None:
    """Deve parsear corretamente datetime com sufixo Z."""
    demandas = [
        {"request_type": "Tipo A", "status": "draft", "updated_at": "2024-01-16T13:00:00Z"},
    ]

    label, dt = service.summarize_demands(demandas)
    assert dt is not None
    # Z = UTC, deve ser parseado corretamente
    assert dt.hour == 13
    assert dt.tzinfo is not None


def test_summarize_demands_with_legacy_status(service: AnvisaService) -> None:
    """Deve contar status legado 'aberta' como aberto."""
    demandas = [
        {"request_type": "Tipo A", "status": "aberta", "updated_at": "2024-01-15T10:00:00Z"},
        {"request_type": "Tipo B", "status": "done", "updated_at": "2024-01-16T12:00:00Z"},
    ]

    label, dt = service.summarize_demands(demandas)
    assert label == "2 demandas (1 em aberto)"


# ===== Testes de build_main_rows =====


def test_build_main_rows_empty(service: AnvisaService) -> None:
    """Deve retornar dicts vazios para lista vazia."""
    requests_by_client, rows = service.build_main_rows([])
    assert requests_by_client == {}
    assert rows == []


def test_build_main_rows_single_client_single_demand(service: AnvisaService) -> None:
    """Deve criar 1 row para 1 cliente com 1 demanda."""
    requests = [
        {
            "client_id": "123",
            "request_type": "Alteração de RT",
            "status": "draft",
            "updated_at": "2024-01-16T13:00:00Z",
            "clients": {
                "razao_social": "Farmácia ABC",
                "cnpj": "12345678000190",
            },
        }
    ]

    requests_by_client, rows = service.build_main_rows(requests)

    assert len(requests_by_client) == 1
    assert "123" in requests_by_client
    assert len(rows) == 1

    row = rows[0]
    assert row["client_id"] == "123"
    assert row["razao_social"] == "Farmácia ABC"
    assert row["cnpj"] == "12345678000190"
    assert row["demanda_label"] == "Alteração de RT"
    assert row["last_update_dt"] is not None


def test_build_main_rows_single_client_multiple_demands(service: AnvisaService) -> None:
    """Deve criar 1 row com resumo para 1 cliente com múltiplas demandas."""
    requests = [
        {
            "client_id": "123",
            "request_type": "Tipo A",
            "status": "draft",
            "updated_at": "2024-01-15T10:00:00Z",
            "clients": {"razao_social": "Farmácia ABC", "cnpj": "12345678000190"},
        },
        {
            "client_id": "123",
            "request_type": "Tipo B",
            "status": "done",
            "updated_at": "2024-01-16T12:00:00Z",
            "clients": {"razao_social": "Farmácia ABC", "cnpj": "12345678000190"},
        },
    ]

    requests_by_client, rows = service.build_main_rows(requests)

    assert len(rows) == 1
    row = rows[0]
    assert row["demanda_label"] == "2 demandas (1 em aberto)"
    # Deve pegar última atualização (16/01)
    assert row["last_update_dt"].day == 16


def test_build_main_rows_multiple_clients(service: AnvisaService) -> None:
    """Deve criar múltiplos rows para múltiplos clientes."""
    requests = [
        {
            "client_id": "123",
            "request_type": "Tipo A",
            "status": "draft",
            "updated_at": "2024-01-15T10:00:00Z",
            "clients": {"razao_social": "Farmácia ABC", "cnpj": "111"},
        },
        {
            "client_id": "456",
            "request_type": "Tipo B",
            "status": "done",
            "updated_at": "2024-01-16T12:00:00Z",
            "clients": {"razao_social": "Farmácia XYZ", "cnpj": "222"},
        },
    ]

    requests_by_client, rows = service.build_main_rows(requests)

    assert len(requests_by_client) == 2
    assert len(rows) == 2

    # Verificar que ambos os clientes estão nos rows
    client_ids = [r["client_id"] for r in rows]
    assert "123" in client_ids
    assert "456" in client_ids


def test_build_main_rows_sorts_by_razao_social(service: AnvisaService) -> None:
    """Deve ordenar rows por razão social (A→Z)."""
    requests = [
        {
            "client_id": "123",
            "request_type": "Tipo A",
            "status": "draft",
            "updated_at": "2024-01-15T10:00:00Z",
            "clients": {"razao_social": "Zebra Farmácia", "cnpj": "111"},
        },
        {
            "client_id": "456",
            "request_type": "Tipo B",
            "status": "done",
            "updated_at": "2024-01-16T12:00:00Z",
            "clients": {"razao_social": "Alpha Farmácia", "cnpj": "222"},
        },
        {
            "client_id": "789",
            "request_type": "Tipo C",
            "status": "submitted",
            "updated_at": "2024-01-17T14:00:00Z",
            "clients": {"razao_social": "Beta Farmácia", "cnpj": "333"},
        },
    ]

    requests_by_client, rows = service.build_main_rows(requests)

    assert len(rows) == 3
    # Verificar ordem alfabética
    assert rows[0]["razao_social"] == "Alpha Farmácia"
    assert rows[1]["razao_social"] == "Beta Farmácia"
    assert rows[2]["razao_social"] == "Zebra Farmácia"


def test_build_main_rows_handles_missing_clients_data(service: AnvisaService) -> None:
    """Deve usar fallback quando clients data não existe."""
    requests = [
        {
            "client_id": "123",
            "request_type": "Tipo A",
            "status": "draft",
            "updated_at": "2024-01-15T10:00:00Z",
            # Sem 'clients' key
        }
    ]

    requests_by_client, rows = service.build_main_rows(requests)

    assert len(rows) == 1
    row = rows[0]
    assert row["razao_social"] == "[Dados não disponíveis]"
    assert row["cnpj"] == ""


# ===== Testes de format_dt_local =====


def test_format_dt_local_with_valid_datetime(service: AnvisaService) -> None:
    """Deve formatar datetime UTC para timezone local."""
    from datetime import datetime, timezone

    dt_utc = datetime(2024, 1, 16, 13, 0, 0, tzinfo=timezone.utc)
    formatted = service.format_dt_local(dt_utc)

    # UTC 13:00 → America/Sao_Paulo 10:00 (UTC-3)
    assert formatted == "16/01/2024 10:00"


def test_format_dt_local_with_none(service: AnvisaService) -> None:
    """Deve retornar string vazia para None."""
    formatted = service.format_dt_local(None)
    assert formatted == ""


def test_format_dt_local_with_different_timezone(service: AnvisaService) -> None:
    """Deve aceitar timezone customizado."""
    from datetime import datetime, timezone

    dt_utc = datetime(2024, 1, 16, 13, 0, 0, tzinfo=timezone.utc)
    # America/New_York é UTC-5
    formatted = service.format_dt_local(dt_utc, tz_name="America/New_York")

    # UTC 13:00 → New York 08:00 (UTC-5)
    assert formatted == "16/01/2024 08:00"


def test_format_dt_local_fallback_on_invalid_timezone(service: AnvisaService) -> None:
    """Deve usar fallback UTC-3 se timezone inválido."""
    from datetime import datetime, timezone

    dt_utc = datetime(2024, 1, 16, 13, 0, 0, tzinfo=timezone.utc)
    # Timezone inválido, deve usar fallback UTC-3
    formatted = service.format_dt_local(dt_utc, tz_name="Invalid/Timezone")

    # Fallback: UTC 13:00 → UTC-3 10:00
    assert formatted == "16/01/2024 10:00"


# ===== Testes de normalize_request_type =====


def test_normalize_request_type_exact_match(service: AnvisaService) -> None:
    """Deve retornar tipo oficial se houver match exato."""
    # Usar tipo válido: "Alteração do Responsável Técnico"
    result = service.normalize_request_type("Alteração do Responsável Técnico")
    assert result == "Alteração do Responsável Técnico"


def test_normalize_request_type_case_insensitive(service: AnvisaService) -> None:
    """Deve normalizar ignorando case."""
    # "Alteração do Responsável Técnico" está em REQUEST_TYPES
    result = service.normalize_request_type("alteração do responsável técnico")
    assert result == "Alteração do Responsável Técnico"

    result = service.normalize_request_type("ALTERAÇÃO DO RESPONSÁVEL TÉCNICO")
    assert result == "Alteração do Responsável Técnico"


def test_normalize_request_type_trims_whitespace(service: AnvisaService) -> None:
    """Deve remover espaços extras."""
    result = service.normalize_request_type("  Alteração do Responsável Técnico  ")
    assert result == "Alteração do Responsável Técnico"


def test_normalize_request_type_invalid_returns_empty(service: AnvisaService) -> None:
    """Deve retornar string vazia para tipo inválido."""
    result = service.normalize_request_type("Tipo Inválido Inexistente")
    assert result == ""


def test_normalize_request_type_empty_string(service: AnvisaService) -> None:
    """Deve retornar vazio para string vazia."""
    result = service.normalize_request_type("")
    assert result == ""


# ===== Testes de validate_new_request_in_memory =====


def test_validate_new_request_valid_no_duplicate(service: AnvisaService) -> None:
    """Deve validar com sucesso se tipo válido e sem duplicado."""
    demandas = [
        {"request_type": "Tipo A", "status": "done", "updated_at": "2024-01-15T10:00:00Z"},
    ]

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração do Responsável Técnico")

    assert ok is True
    assert dup is None
    assert msg == ""


def test_validate_new_request_invalid_type(service: AnvisaService) -> None:
    """Deve falhar se tipo inválido."""
    demandas = []

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Tipo Inválido")

    assert ok is False
    assert dup is None
    assert "inválido" in msg.lower()


def test_validate_new_request_duplicate_open(service: AnvisaService) -> None:
    """Deve falhar se existe duplicado aberto."""
    demandas = [
        {
            "id": "uuid-123",
            "request_type": "Alteração do Responsável Técnico",
            "status": "draft",
            "updated_at": "2024-01-15T10:00:00Z",
        },
    ]

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração do Responsável Técnico")

    assert ok is False
    assert dup is not None
    assert dup["id"] == "uuid-123"
    assert "ABERTA" in msg or "aberta" in msg.lower()


def test_validate_new_request_duplicate_closed_ok(service: AnvisaService) -> None:
    """Deve validar OK se duplicado está fechado."""
    demandas = [
        {
            "id": "uuid-123",
            "request_type": "Alteração do Responsável Técnico",
            "status": "done",
            "updated_at": "2024-01-15T10:00:00Z",
        },
    ]

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração do Responsável Técnico")

    assert ok is True
    assert dup is None
    assert msg == ""


def test_validate_new_request_case_insensitive_type(service: AnvisaService) -> None:
    """Deve validar com tipo case-insensitive."""
    demandas = []

    # "alteração do responsável técnico" (lowercase) deve ser válido
    ok, dup, msg = service.validate_new_request_in_memory(demandas, "alteração do responsável técnico")

    assert ok is True
    assert dup is None


def test_validate_new_request_empty_list(service: AnvisaService) -> None:
    """Deve validar OK com lista vazia de demandas."""
    ok, dup, msg = service.validate_new_request_in_memory([], "Alteração do Responsável Técnico")

    assert ok is True
    assert dup is None
    assert msg == ""


# ===== Testes de human_status =====


def test_human_status_open_statuses(service: AnvisaService) -> None:
    """Deve retornar 'Em aberto' para status abertos."""
    assert service.human_status("draft") == "Em aberto"
    assert service.human_status("submitted") == "Em aberto"
    assert service.human_status("in_progress") == "Em aberto"


def test_human_status_closed_statuses(service: AnvisaService) -> None:
    """Deve retornar 'Finalizado' para status fechados."""
    assert service.human_status("done") == "Finalizado"
    assert service.human_status("canceled") == "Finalizado"


def test_human_status_legacy_aliases(service: AnvisaService) -> None:
    """Deve suportar status legado via aliases."""
    # "aberta" -> normalizado para status aberto
    assert service.human_status("aberta") == "Em aberto"
    assert service.human_status("em andamento") == "Em aberto"

    # "finalizada" -> normalizado para status fechado
    assert service.human_status("finalizada") == "Finalizado"
    assert service.human_status("cancelada") == "Finalizado"


def test_human_status_case_insensitive(service: AnvisaService) -> None:
    """Deve funcionar com case diferente."""
    assert service.human_status("DRAFT") == "Em aberto"
    assert service.human_status("Done") == "Finalizado"


# ===== Testes de normalize_status =====


def test_normalize_status_legacy_to_canonical(service: AnvisaService) -> None:
    """Deve converter status legado para canônico usando aliases."""
    assert service.normalize_status("aberta") == "draft"
    assert service.normalize_status("em andamento") == "in_progress"
    assert service.normalize_status("finalizada") == "done"
    assert service.normalize_status("cancelada") == "canceled"


def test_normalize_status_already_canonical(service: AnvisaService) -> None:
    """Deve manter status já canônico."""
    assert service.normalize_status("draft") == "draft"
    assert service.normalize_status("done") == "done"
    assert service.normalize_status("canceled") == "canceled"


def test_normalize_status_with_whitespace(service: AnvisaService) -> None:
    """Deve ignorar espaços extras."""
    assert service.normalize_status("  aberta  ") == "draft"
    assert service.normalize_status("  em andamento  ") == "in_progress"


def test_allowed_actions_with_legacy_status(service: AnvisaService) -> None:
    """Deve funcionar com status legado."""
    actions = service.allowed_actions("aberta")
    assert actions["close"] is True
    assert actions["cancel"] is True
    assert actions["delete"] is True


# ===== Testes de build_history_rows =====


def test_build_history_rows_empty_list(service: AnvisaService) -> None:
    """Deve retornar lista vazia para input vazio."""
    rows = service.build_history_rows([])
    assert rows == []


def test_build_history_rows_single_demand(service: AnvisaService) -> None:
    """Deve criar row com campos corretos para uma demanda."""
    demandas = [
        {
            "id": "uuid-123",
            "request_type": "Alteração do Responsável Técnico",
            "status": "draft",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-16T12:00:00Z",
        }
    ]

    rows = service.build_history_rows(demandas)

    assert len(rows) == 1
    row = rows[0]

    assert row["request_id"] == "uuid-123"
    assert row["tipo"] == "Alteração do Responsável Técnico"
    assert row["status_humano"] == "Em aberto"
    assert row["criada_em"] != ""  # Formatado
    assert row["atualizada_em"] != ""  # Formatado
    assert row["updated_dt_utc"] is not None


def test_build_history_rows_sorts_by_updated_desc(service: AnvisaService) -> None:
    """Deve ordenar por updated_at descendente (mais recente primeiro)."""
    demandas = [
        {
            "id": "uuid-1",
            "request_type": "Tipo A",
            "status": "draft",
            "created_at": "2024-01-10T10:00:00Z",
            "updated_at": "2024-01-10T10:00:00Z",
        },
        {
            "id": "uuid-2",
            "request_type": "Tipo B",
            "status": "done",
            "created_at": "2024-01-12T10:00:00Z",
            "updated_at": "2024-01-16T10:00:00Z",  # Mais recente
        },
        {
            "id": "uuid-3",
            "request_type": "Tipo C",
            "status": "submitted",
            "created_at": "2024-01-11T10:00:00Z",
            "updated_at": "2024-01-14T10:00:00Z",
        },
    ]

    rows = service.build_history_rows(demandas)

    assert len(rows) == 3
    # Ordem esperada: uuid-2 (16/01), uuid-3 (14/01), uuid-1 (10/01)
    assert rows[0]["request_id"] == "uuid-2"
    assert rows[1]["request_id"] == "uuid-3"
    assert rows[2]["request_id"] == "uuid-1"


def test_build_history_rows_fallback_created_at(service: AnvisaService) -> None:
    """Deve usar created_at se updated_at não existir."""
    demandas = [
        {
            "id": "uuid-123",
            "request_type": "Tipo A",
            "status": "draft",
            "created_at": "2024-01-15T10:00:00Z",
            # Sem updated_at
        }
    ]

    rows = service.build_history_rows(demandas)

    assert len(rows) == 1
    row = rows[0]

    # Deve ter usado created_at
    assert row["atualizada_em"] != ""
    assert row["criada_em"] == row["atualizada_em"]


def test_build_history_rows_formats_dates(service: AnvisaService) -> None:
    """Deve formatar datas usando format_dt_local."""
    demandas = [
        {
            "id": "uuid-123",
            "request_type": "Tipo A",
            "status": "draft",
            "created_at": "2024-01-15T13:00:00Z",  # UTC
            "updated_at": "2024-01-16T13:00:00Z",  # UTC
        }
    ]

    rows = service.build_history_rows(demandas)
    row = rows[0]

    # Verificar formato DD/MM/YYYY HH:MM (não vazio)
    assert row["criada_em"] != ""
    assert row["atualizada_em"] != ""
    assert "/" in row["criada_em"]
    assert ":" in row["criada_em"]


def test_build_history_rows_multiple_statuses(service: AnvisaService) -> None:
    """Deve converter status corretamente para múltiplas demandas."""
    demandas = [
        {
            "id": "uuid-1",
            "request_type": "Tipo A",
            "status": "draft",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "uuid-2",
            "request_type": "Tipo B",
            "status": "done",
            "created_at": "2024-01-16T10:00:00Z",
            "updated_at": "2024-01-16T10:00:00Z",
        },
    ]

    rows = service.build_history_rows(demandas)

    # Ordem: uuid-2 (mais recente), uuid-1
    assert rows[0]["status_humano"] == "Finalizado"  # done
    assert rows[1]["status_humano"] == "Em aberto"  # draft


def test_build_history_rows_includes_status_raw(service: AnvisaService) -> None:
    """Deve incluir status_raw canônico normalizado."""
    demandas = [
        {
            "id": "uuid-1",
            "request_type": "Tipo A",
            "status": "draft",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "uuid-2",
            "request_type": "Tipo B",
            "status": "done",
            "created_at": "2024-01-16T10:00:00Z",
            "updated_at": "2024-01-16T10:00:00Z",
        },
    ]

    rows = service.build_history_rows(demandas)

    # Verificar que status_raw está presente e normalizado
    assert rows[0]["status_raw"] == "done"
    assert rows[1]["status_raw"] == "draft"


def test_build_history_rows_normalizes_legacy_status(service: AnvisaService) -> None:
    """Deve normalizar status legado para canônico."""
    demandas = [
        {
            "id": "uuid-1",
            "request_type": "Tipo A",
            "status": "aberta",  # Legado
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "uuid-2",
            "request_type": "Tipo B",
            "status": "cancelada",  # Legado
            "created_at": "2024-01-16T10:00:00Z",
            "updated_at": "2024-01-16T10:00:00Z",
        },
    ]

    rows = service.build_history_rows(demandas)

    # Status legado deve ser normalizado para canônico
    assert rows[0]["status_raw"] == "canceled"  # cancelada -> canceled
    assert rows[1]["status_raw"] == "draft"  # aberta -> draft


def test_build_history_rows_includes_actions_for_open_status(service: AnvisaService) -> None:
    """Deve incluir actions com close/cancel True para status aberto."""
    demandas = [
        {
            "id": "uuid-1",
            "request_type": "Tipo A",
            "status": "draft",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "uuid-2",
            "request_type": "Tipo B",
            "status": "in_progress",
            "created_at": "2024-01-16T10:00:00Z",
            "updated_at": "2024-01-16T10:00:00Z",
        },
    ]

    rows = service.build_history_rows(demandas)

    # Ambos devem ter close/cancel True
    for row in rows:
        actions = row["actions"]
        assert actions["close"] is True
        assert actions["cancel"] is True
        assert actions["delete"] is True


def test_build_history_rows_includes_actions_for_closed_status(service: AnvisaService) -> None:
    """Deve incluir actions com close/cancel False para status fechado."""
    demandas = [
        {
            "id": "uuid-1",
            "request_type": "Tipo A",
            "status": "done",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "uuid-2",
            "request_type": "Tipo B",
            "status": "canceled",
            "created_at": "2024-01-16T10:00:00Z",
            "updated_at": "2024-01-16T10:00:00Z",
        },
    ]

    rows = service.build_history_rows(demandas)

    # Ambos devem ter close/cancel False, delete True
    for row in rows:
        actions = row["actions"]
        assert actions["close"] is False
        assert actions["cancel"] is False
        assert actions["delete"] is True


# ===== Testes adicionais de cobertura =====


def test_normalize_request_type_valid_types(service: AnvisaService) -> None:
    """Testa normalização de tipos válidos (case-insensitive)."""
    # Uppercase
    assert service.normalize_request_type("ALTERAÇÃO DO RESPONSÁVEL LEGAL") == "Alteração do Responsável Legal"
    # Lowercase
    assert service.normalize_request_type("alteração do responsável legal") == "Alteração do Responsável Legal"
    # Mixed case com espaços extras
    assert service.normalize_request_type("  Alteração do Responsável Legal  ") == "Alteração do Responsável Legal"
    # Todos os tipos oficiais
    from src.modules.anvisa.constants import REQUEST_TYPES

    for official in REQUEST_TYPES:
        assert service.normalize_request_type(official) == official
        assert service.normalize_request_type(official.upper()) == official
        assert service.normalize_request_type(official.lower()) == official


def test_normalize_request_type_invalid_type(service: AnvisaService) -> None:
    """Testa normalização de tipo inválido (retorna vazio)."""
    assert service.normalize_request_type("Tipo Inventado") == ""
    assert service.normalize_request_type("") == ""
    assert service.normalize_request_type("   ") == ""


def test_validate_new_request_in_memory_valid(service: AnvisaService) -> None:
    """Testa validação bem-sucedida de nova demanda."""
    demandas = []  # Nenhuma demanda aberta

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração de Porte")

    assert ok is True
    assert dup is None
    assert msg == ""


def test_validate_new_request_in_memory_invalid_type(service: AnvisaService) -> None:
    """Testa validação com tipo inválido."""
    demandas = []

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Tipo Errado")

    assert ok is False
    assert dup is None
    assert "inválido" in msg
    assert "Tipo Errado" in msg


def test_validate_new_request_in_memory_duplicate_blocked(service: AnvisaService) -> None:
    """Testa validação bloqueando duplicado aberto."""
    demandas = [
        {
            "id": "req-1",
            "request_type": "Alteração de Porte",
            "status": "draft",
        }
    ]

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração de Porte")

    assert ok is False
    assert dup is not None
    assert dup["id"] == "req-1"
    assert "Já existe" in msg
    assert "ABERTA" in msg
    assert "Alteração de Porte" in msg


def test_validate_new_request_in_memory_duplicate_closed_ok(service: AnvisaService) -> None:
    """Testa validação permitindo se duplicado está fechado."""
    demandas = [
        {
            "id": "req-1",
            "request_type": "Alteração de Porte",
            "status": "done",
        }
    ]

    ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração de Porte")

    assert ok is True
    assert dup is None
    assert msg == ""


def test_parse_iso_datetime_valid(service: AnvisaService) -> None:
    """Testa parse de datetime ISO válido."""
    from datetime import timezone

    # ISO com timezone
    dt = service._parse_iso_datetime("2024-01-15T10:30:00+00:00")
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 10
    assert dt.minute == 30
    assert dt.tzinfo == timezone.utc

    # ISO com Z (deve converter para +00:00)
    dt_z = service._parse_iso_datetime("2024-01-15T10:30:00Z")
    assert dt_z is not None
    assert dt_z == dt


def test_parse_iso_datetime_naive(service: AnvisaService) -> None:
    """Testa parse de datetime sem timezone (deve assumir UTC)."""
    from datetime import timezone

    dt = service._parse_iso_datetime("2024-01-15T10:30:00")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_iso_datetime_empty(service: AnvisaService) -> None:
    """Testa parse de string vazia."""
    assert service._parse_iso_datetime("") is None
    assert service._parse_iso_datetime(None) is None  # type: ignore


def test_parse_iso_datetime_invalid(service: AnvisaService) -> None:
    """Testa parse de string inválida."""
    assert service._parse_iso_datetime("invalid-date") is None
    assert service._parse_iso_datetime("2024-99-99") is None


def test_format_dt_local_valid(service: AnvisaService) -> None:
    """Testa formatação de datetime para timezone local."""
    from datetime import datetime, timezone

    dt_utc = datetime(2024, 1, 15, 13, 30, 0, tzinfo=timezone.utc)

    # São Paulo = UTC-3
    result = service.format_dt_local(dt_utc, tz_name="America/Sao_Paulo")

    # 13:30 UTC = 10:30 BRT
    assert "15/01/2024" in result
    assert "10:30" in result


def test_format_dt_local_none(service: AnvisaService) -> None:
    """Testa formatação de None."""
    assert service.format_dt_local(None) == ""


def test_format_dt_local_fallback_on_invalid_tz(service: AnvisaService) -> None:
    """Testa fallback quando timezone inválido."""
    from datetime import datetime, timezone

    dt_utc = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

    # Timezone inválido deve usar fallback UTC-3
    result = service.format_dt_local(dt_utc, tz_name="Invalid/Timezone")

    # Deve retornar algo (fallback)
    assert "15/01/2024" in result


def test_human_status_open(service: AnvisaService) -> None:
    """Testa human_status para status abertos."""
    assert service.human_status("draft") == "Em aberto"
    assert service.human_status("submitted") == "Em aberto"
    assert service.human_status("in_progress") == "Em aberto"


def test_human_status_closed(service: AnvisaService) -> None:
    """Testa human_status para status fechados."""
    assert service.human_status("done") == "Finalizado"
    assert service.human_status("canceled") == "Finalizado"


def test_normalize_status_with_aliases(service: AnvisaService) -> None:
    """Testa normalização de status com aliases."""
    assert service.normalize_status("aberta") == "draft"
    assert service.normalize_status("finalizada") == "done"
    assert service.normalize_status("cancelada") == "canceled"
    assert service.normalize_status("em andamento") == "in_progress"


def test_normalize_status_already_normalized(service: AnvisaService) -> None:
    """Testa normalização de status já normalizado."""
    assert service.normalize_status("draft") == "draft"
    assert service.normalize_status("done") == "done"
    assert service.normalize_status("canceled") == "canceled"


def test_normalize_status_case_insensitive(service: AnvisaService) -> None:
    """Testa que normalização é case-insensitive."""
    assert service.normalize_status("ABERTA") == "draft"
    assert service.normalize_status("Finalizada") == "done"
    assert service.normalize_status("  CaNcElAdA  ") == "canceled"


def test_can_close_open_statuses(service: AnvisaService) -> None:
    """Testa can_close para status abertos."""
    assert service.can_close("draft") is True
    assert service.can_close("submitted") is True
    assert service.can_close("in_progress") is True


def test_can_close_closed_statuses(service: AnvisaService) -> None:
    """Testa can_close para status fechados."""
    assert service.can_close("done") is False
    assert service.can_close("canceled") is False


def test_can_cancel_open_statuses(service: AnvisaService) -> None:
    """Testa can_cancel para status abertos."""
    assert service.can_cancel("draft") is True
    assert service.can_cancel("submitted") is True
    assert service.can_cancel("in_progress") is True


def test_can_cancel_closed_statuses(service: AnvisaService) -> None:
    """Testa can_cancel para status fechados."""
    assert service.can_cancel("done") is False
    assert service.can_cancel("canceled") is False


def test_allowed_actions_open_status(service: AnvisaService) -> None:
    """Testa allowed_actions para status aberto."""
    actions = service.allowed_actions("draft")
    assert actions == {"close": True, "cancel": True, "delete": True}

    actions = service.allowed_actions("in_progress")
    assert actions == {"close": True, "cancel": True, "delete": True}


def test_allowed_actions_closed_status(service: AnvisaService) -> None:
    """Testa allowed_actions para status fechado."""
    actions = service.allowed_actions("done")
    assert actions == {"close": False, "cancel": False, "delete": True}

    actions = service.allowed_actions("canceled")
    assert actions == {"close": False, "cancel": False, "delete": True}
