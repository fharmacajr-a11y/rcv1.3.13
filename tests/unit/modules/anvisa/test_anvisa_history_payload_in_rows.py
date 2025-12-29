"""Testes unitários para exibição de payload no histórico de demandas.

Testa que build_history_rows inclui prazo e observações extraídos do payload.
"""

from __future__ import annotations

import pytest


class FakeRepository:
    """Repositório fake mínimo para satisfazer o __init__ do AnvisaService."""

    def list_requests(self, org_id: str) -> list[dict]:
        """Retorna lista vazia (não usado nos testes de build_history_rows)."""
        return []


@pytest.fixture
def anvisa_service():
    """Fixture que cria instância do AnvisaService com repo fake."""
    from src.modules.anvisa.services.anvisa_service import AnvisaService

    return AnvisaService(repository=FakeRepository())


# ========== format_due_date_iso_to_br ==========


class TestFormatDueDateIsoToBr:
    """Testes para format_due_date_iso_to_br."""

    def test_empty_string_returns_empty(self, anvisa_service):
        """String vazia deve retornar string vazia."""
        assert anvisa_service.format_due_date_iso_to_br("") == ""

    def test_none_returns_empty(self, anvisa_service):
        """None (cast) deve retornar string vazia."""
        assert anvisa_service.format_due_date_iso_to_br(None) == ""  # type: ignore[arg-type]

    def test_whitespace_returns_empty(self, anvisa_service):
        """Espaços em branco devem retornar string vazia."""
        assert anvisa_service.format_due_date_iso_to_br("   ") == ""

    def test_valid_iso_converts_to_br(self, anvisa_service):
        """Data ISO válida deve converter para formato brasileiro."""
        assert anvisa_service.format_due_date_iso_to_br("2025-12-27") == "27/12/2025"

    def test_iso_with_time_suffix_works(self, anvisa_service):
        """Data ISO com sufixo de hora deve funcionar (usa apenas primeiros 10 chars)."""
        assert anvisa_service.format_due_date_iso_to_br("2025-12-27T14:30:00Z") == "27/12/2025"

    def test_invalid_format_returns_empty(self, anvisa_service):
        """Formato inválido deve retornar string vazia."""
        assert anvisa_service.format_due_date_iso_to_br("27/12/2025") == ""

    def test_invalid_date_returns_empty(self, anvisa_service):
        """Data inválida deve retornar string vazia."""
        assert anvisa_service.format_due_date_iso_to_br("2025-99-99") == ""


# ========== build_history_rows com payload ==========


class TestBuildHistoryRowsPayload:
    """Testes para build_history_rows com foco em prazo/observações."""

    def test_payload_with_due_date_and_notes(self, anvisa_service):
        """Payload com due_date e notes deve popular prazo e observacoes."""
        demandas = [
            {
                "id": "req-123",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-27T10:00:00Z",
                "updated_at": "2025-12-27T12:00:00Z",
                "payload": {
                    "due_date": "2025-12-27",
                    "notes": "Observação de teste",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == "27/12/2025"
        assert rows[0]["observacoes"] == "Observação de teste"

    def test_payload_empty_returns_empty_strings(self, anvisa_service):
        """Payload vazio deve retornar strings vazias para prazo/observacoes."""
        demandas = [
            {
                "id": "req-456",
                "request_type": "Associação ao SNGPC",
                "status": "done",
                "created_at": "2025-12-26T10:00:00Z",
                "updated_at": "2025-12-26T12:00:00Z",
                "payload": {},
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == ""
        assert rows[0]["observacoes"] == ""

    def test_payload_none_returns_empty_strings(self, anvisa_service):
        """Payload None deve retornar strings vazias para prazo/observacoes."""
        demandas = [
            {
                "id": "req-789",
                "request_type": "Cancelamento de AFE",
                "status": "in_progress",
                "created_at": "2025-12-25T10:00:00Z",
                "updated_at": "2025-12-25T12:00:00Z",
                "payload": None,
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == ""
        assert rows[0]["observacoes"] == ""

    def test_payload_missing_returns_empty_strings(self, anvisa_service):
        """Demanda sem campo payload deve retornar strings vazias."""
        demandas = [
            {
                "id": "req-abc",
                "request_type": "Alteração da Razão Social",
                "status": "submitted",
                "created_at": "2025-12-24T10:00:00Z",
                "updated_at": "2025-12-24T12:00:00Z",
                # sem payload
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == ""
        assert rows[0]["observacoes"] == ""

    def test_invalid_due_date_returns_empty_prazo(self, anvisa_service):
        """Data inválida no payload deve retornar prazo vazio."""
        demandas = [
            {
                "id": "req-def",
                "request_type": "Alteração do Responsável Legal",
                "status": "draft",
                "created_at": "2025-12-23T10:00:00Z",
                "updated_at": "2025-12-23T12:00:00Z",
                "payload": {
                    "due_date": "data-invalida",
                    "notes": "Nota válida",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == ""
        assert rows[0]["observacoes"] == "Nota válida"

    def test_payload_only_due_date(self, anvisa_service):
        """Payload apenas com due_date deve ter observacoes vazia."""
        demandas = [
            {
                "id": "req-ghi",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-22T10:00:00Z",
                "updated_at": "2025-12-22T12:00:00Z",
                "payload": {
                    "due_date": "2026-01-15",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == "15/01/2026"
        assert rows[0]["observacoes"] == ""

    def test_payload_only_notes(self, anvisa_service):
        """Payload apenas com notes deve ter prazo vazio."""
        demandas = [
            {
                "id": "req-jkl",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-21T10:00:00Z",
                "updated_at": "2025-12-21T12:00:00Z",
                "payload": {
                    "notes": "Apenas observação",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == ""
        assert rows[0]["observacoes"] == "Apenas observação"

    def test_payload_not_dict_returns_empty(self, anvisa_service):
        """Payload que não é dict deve retornar strings vazias."""
        demandas = [
            {
                "id": "req-mno",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-20T12:00:00Z",
                "payload": "string-instead-of-dict",
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        assert rows[0]["prazo"] == ""
        assert rows[0]["observacoes"] == ""


# ========== format_dt_local_dash ==========


class TestFormatDtLocalDash:
    """Testes para format_dt_local_dash."""

    def test_none_returns_empty(self, anvisa_service):
        """None deve retornar string vazia."""
        assert anvisa_service.format_dt_local_dash(None) == ""

    def test_datetime_returns_dash_format(self, anvisa_service):
        """Datetime deve retornar formato com tracinho."""
        from datetime import datetime, timezone

        dt = datetime(2025, 12, 27, 15, 30, 0, tzinfo=timezone.utc)
        result = anvisa_service.format_dt_local_dash(dt)
        # Resultado esperado: "DD/MM/AAAA - HH:MM" (horário local)
        assert " - " in result
        assert result.count(" - ") == 1


# ========== resolve_initial_from_email ==========


class TestResolveInitialFromEmail:
    """Testes para resolve_initial_from_email."""

    def test_empty_email_returns_empty(self, anvisa_service):
        """Email vazio deve retornar string vazia."""
        assert anvisa_service.resolve_initial_from_email("") == ""

    def test_none_email_returns_empty(self, anvisa_service):
        """None deve retornar string vazia."""
        assert anvisa_service.resolve_initial_from_email(None) == ""  # type: ignore[arg-type]

    def test_email_returns_first_letter(self, anvisa_service):
        """Email sem mapa deve retornar primeira letra uppercase."""
        result = anvisa_service.resolve_initial_from_email("usuario@example.com")
        assert result == "U"

    def test_email_with_whitespace(self, anvisa_service):
        """Email com espaços deve ser normalizado."""
        result = anvisa_service.resolve_initial_from_email("  teste@example.com  ")
        assert result == "T"


class TestBuildHistoryRowsDateFormat:
    """Testes para formato de data com tracinho em build_history_rows."""

    def test_dates_have_dash_format(self, anvisa_service):
        """Datas devem conter tracinho entre data e hora."""
        demandas = [
            {
                "id": "req-date-test",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-27T10:00:00Z",
                "updated_at": "2025-12-27T12:00:00Z",
                "payload": {},
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        # Verificar que ambas as datas têm o formato com tracinho
        assert " - " in rows[0]["criada_em"]
        assert " - " in rows[0]["atualizada_em"]

    def test_updated_by_adds_initial(self, anvisa_service, monkeypatch):
        """updated_by no payload deve adicionar inicial no atualizada_em."""
        # Monkeypatch para simular RC_INITIALS_MAP
        monkeypatch.setenv("RC_INITIALS_MAP", '{"user@example.com":"Fulano"}')

        # Limpar cache do load_env_author_names se existir
        try:
            from src.modules.hub.services.authors_service import load_env_author_names

            if hasattr(load_env_author_names, "cache_clear"):
                load_env_author_names.cache_clear()
        except Exception:
            pass

        demandas = [
            {
                "id": "req-updated-by",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-27T10:00:00Z",
                "updated_at": "2025-12-27T12:00:00Z",
                "payload": {
                    "updated_by": "user@example.com",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        # Deve terminar com "(F)" - inicial de "Fulano"
        assert rows[0]["atualizada_em"].endswith("(F)")
        assert " - " in rows[0]["atualizada_em"]

    def test_updated_by_fallback_first_letter(self, anvisa_service, monkeypatch):
        """updated_by sem mapa deve usar primeira letra do email."""
        # Garantir que RC_INITIALS_MAP está vazio
        monkeypatch.setenv("RC_INITIALS_MAP", "{}")

        try:
            from src.modules.hub.services.authors_service import load_env_author_names

            if hasattr(load_env_author_names, "cache_clear"):
                load_env_author_names.cache_clear()
        except Exception:
            pass

        demandas = [
            {
                "id": "req-fallback",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-27T10:00:00Z",
                "updated_at": "2025-12-27T12:00:00Z",
                "payload": {
                    "updated_by": "xpto@example.com",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        # Deve terminar com "(X)" - primeira letra do email
        assert rows[0]["atualizada_em"].endswith("(X)")

    def test_no_updated_by_no_initial(self, anvisa_service):
        """Sem updated_by no payload, não deve adicionar inicial."""
        demandas = [
            {
                "id": "req-no-updated-by",
                "request_type": "Alteração de Porte",
                "status": "draft",
                "created_at": "2025-12-27T10:00:00Z",
                "updated_at": "2025-12-27T12:00:00Z",
                "payload": {},
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        # Não deve ter parênteses no final
        assert not rows[0]["atualizada_em"].endswith(")")

    def test_created_by_adds_initial_to_criada_em(self, anvisa_service, monkeypatch):
        """Deve adicionar inicial do criador em criada_em quando created_by está presente."""
        monkeypatch.setenv("RC_INITIALS_MAP", '{"farmacajr@gmail.com":"Junior"}')

        demandas = [
            {
                "id": "req-created-by",
                "request_type": "Alteração de RT",
                "status": "draft",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "payload": {
                    "created_by": "farmacajr@gmail.com",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        # Deve ter tracinho e inicial em criada_em
        assert " - " in rows[0]["criada_em"]
        assert rows[0]["criada_em"].endswith("(J)")
        # Atualizada_em também deve ter (J) por fallback para created_by
        assert " - " in rows[0]["atualizada_em"]
        assert rows[0]["atualizada_em"].endswith("(J)")

    def test_updated_by_overrides_created_by_in_atualizada_em(self, anvisa_service, monkeypatch):
        """Quando ambos created_by e updated_by existem, updated_by deve aparecer em atualizada_em."""
        monkeypatch.setenv("RC_INITIALS_MAP", '{"creator@example.com":"Creator","updater@example.com":"Updater"}')

        demandas = [
            {
                "id": "req-both-authors",
                "request_type": "Alteração de Porte",
                "status": "submitted",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-16T14:00:00Z",
                "payload": {
                    "created_by": "creator@example.com",
                    "updated_by": "updater@example.com",
                },
            }
        ]

        rows = anvisa_service.build_history_rows(demandas)

        assert len(rows) == 1
        # Criada_em deve ter (C) do creator
        assert rows[0]["criada_em"].endswith("(C)")
        # Atualizada_em deve ter (U) do updater
        assert rows[0]["atualizada_em"].endswith("(U)")
