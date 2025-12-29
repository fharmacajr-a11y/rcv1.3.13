"""Testes unitários para helpers de payload no AnvisaService.

Testa métodos headless (sem UI):
- parse_due_date_br: conversão de data brasileira para ISO
- build_payload_for_new_request: construção de payload com request_type, due_date_iso e notes
- request_type_check_daily: regra de acompanhamento diário
- default_due_date_iso_for_type: prazo padrão por tipo
"""

from __future__ import annotations

import pytest


class FakeRepository:
    """Repositório fake mínimo para satisfazer o __init__ do AnvisaService."""

    def list_requests(self, org_id: str) -> list[dict]:
        """Retorna lista vazia (não usado nos testes de payload)."""
        return []


@pytest.fixture
def anvisa_service():
    """Fixture que cria instância do AnvisaService com repo fake."""
    from src.modules.anvisa.services.anvisa_service import AnvisaService

    return AnvisaService(repository=FakeRepository())


# ========== parse_due_date_br ==========


class TestParseDueDateBr:
    """Testes para parse_due_date_br."""

    def test_empty_string_returns_none(self, anvisa_service):
        """String vazia deve retornar None."""
        assert anvisa_service.parse_due_date_br("") is None

    def test_whitespace_only_returns_none(self, anvisa_service):
        """String com apenas espaços deve retornar None."""
        assert anvisa_service.parse_due_date_br("   ") is None

    def test_none_value_returns_none(self, anvisa_service):
        """Valor None (cast para string) deve retornar None."""
        # O método faz (value or ""), então None vira ""
        assert anvisa_service.parse_due_date_br(None) is None  # type: ignore[arg-type]

    def test_valid_date_converts_to_iso(self, anvisa_service):
        """Data válida dd/mm/aaaa deve converter para aaaa-mm-dd."""
        assert anvisa_service.parse_due_date_br("27/12/2025") == "2025-12-27"

    def test_valid_date_with_leading_zeros(self, anvisa_service):
        """Data com zeros à esquerda deve funcionar."""
        assert anvisa_service.parse_due_date_br("01/01/2026") == "2026-01-01"

    def test_valid_date_with_whitespace(self, anvisa_service):
        """Data com espaços ao redor deve funcionar (strip aplicado)."""
        assert anvisa_service.parse_due_date_br("  15/06/2025  ") == "2025-06-15"

    def test_invalid_date_format_returns_none(self, anvisa_service):
        """Formato inválido deve retornar None."""
        assert anvisa_service.parse_due_date_br("99/99/9999") is None

    def test_american_format_returns_none(self, anvisa_service):
        """Formato americano (mm/dd/yyyy) não é aceito."""
        # 12/31/2025 seria 31 de dezembro no formato BR, mas mês 31 não existe
        assert anvisa_service.parse_due_date_br("12/31/2025") is None

    def test_iso_format_returns_none(self, anvisa_service):
        """Formato ISO (yyyy-mm-dd) não é aceito."""
        assert anvisa_service.parse_due_date_br("2025-12-27") is None

    def test_partial_date_returns_none(self, anvisa_service):
        """Data parcial deve retornar None."""
        assert anvisa_service.parse_due_date_br("27/12") is None

    def test_text_returns_none(self, anvisa_service):
        """Texto arbitrário deve retornar None."""
        assert anvisa_service.parse_due_date_br("não é uma data") is None


# ========== build_payload_for_new_request ==========


class TestBuildPayloadForNewRequest:
    """Testes para build_payload_for_new_request."""

    def test_builds_payload_with_all_fields(self, anvisa_service):
        """Deve incluir due_date, check_daily e notes no payload."""
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Alteração de Nome Fantasia",
            due_date_iso="2025-12-27",
            notes="Observação importante",
        )
        assert payload == {
            "due_date": "2025-12-27",
            "check_daily": True,  # Nome Fantasia precisa acompanhamento
            "notes": "Observação importante",
        }

    def test_empty_notes_excluded(self, anvisa_service):
        """Notes vazio não deve aparecer no payload."""
        payload = anvisa_service.build_payload_for_new_request(
            request_type="AFE ANVISA",
            due_date_iso="2025-12-27",
            notes="",
        )
        assert payload == {
            "due_date": "2025-12-27",
            "check_daily": True,
        }

    def test_whitespace_notes_excluded(self, anvisa_service):
        """Notes apenas com espaços não deve aparecer no payload."""
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Concessão de AE Manipulação",
            due_date_iso="2026-01-15",
            notes="   ",
        )
        assert payload == {
            "due_date": "2026-01-15",
            "check_daily": True,
        }

    def test_notes_stripped(self, anvisa_service):
        """Notes com espaços ao redor deve ter strip aplicado."""
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Alteração de Porte",
            due_date_iso="2025-12-30",
            notes="  texto com espaços  ",
        )
        assert payload["notes"] == "texto com espaços"

    def test_notes_truncated_at_500_chars(self, anvisa_service):
        """Notes maior que 500 caracteres deve ser truncado."""
        long_notes = "x" * 600
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Cancelamento de AFE",
            due_date_iso="2025-12-27",
            notes=long_notes,
        )
        assert len(payload["notes"]) == 500  # type: ignore[arg-type]
        assert payload["notes"] == "x" * 500

    def test_notes_exactly_500_chars_not_truncated(self, anvisa_service):
        """Notes com exatamente 500 caracteres não deve ser truncado."""
        exact_notes = "y" * 500
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Ampliação de Atividades",
            due_date_iso="2025-12-27",
            notes=exact_notes,
        )
        assert payload["notes"] == exact_notes

    def test_multiline_notes(self, anvisa_service):
        """Notes com múltiplas linhas deve ser preservado."""
        multiline = "Linha 1\nLinha 2\nLinha 3"
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Redução de Atividades",
            due_date_iso="2025-12-27",
            notes=multiline,
        )
        assert payload == {
            "due_date": "2025-12-27",
            "check_daily": True,
            "notes": "Linha 1\nLinha 2\nLinha 3",
        }

    def test_instant_type_check_daily_false(self, anvisa_service):
        """Tipos instantâneos devem ter check_daily=False."""
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Alteração do Responsável Legal",
            due_date_iso="2025-12-27",
            notes="",
        )
        assert payload == {
            "due_date": "2025-12-27",
            "check_daily": False,
        }

    def test_non_instant_type_check_daily_true(self, anvisa_service):
        """Tipos não instantâneos devem ter check_daily=True."""
        payload = anvisa_service.build_payload_for_new_request(
            request_type="Alteração de Nome Fantasia",
            due_date_iso="2025-12-28",
            notes="",
        )
        assert payload == {
            "due_date": "2025-12-28",
            "check_daily": True,
        }


# ========== request_type_check_daily ==========


class TestRequestTypeCheckDaily:
    """Testes para request_type_check_daily."""

    def test_instant_types_return_false(self, anvisa_service):
        """Tipos instantâneos não precisam acompanhamento diário."""
        instant_types = [
            "Alteração do Responsável Legal",
            "Alteração do Responsável Técnico",
            "Associação ao SNGPC",
            "Importação de Cannabidiol",
        ]
        for req_type in instant_types:
            assert anvisa_service.request_type_check_daily(req_type) is False

    def test_non_instant_types_return_true(self, anvisa_service):
        """Tipos não instantâneos precisam acompanhamento diário."""
        non_instant_types = [
            "AFE ANVISA",
            "Alteração da Razão Social",
            "Alteração de Endereço",
            "Alteração de Nome Fantasia",
            "Alteração de Porte",
            "Ampliação de Atividades",
            "Cancelamento de AFE",
            "Concessão de AE Manipulação",
            "Concessão de AFE (Inicial)",
            "Redução de Atividades",
        ]
        for req_type in non_instant_types:
            assert anvisa_service.request_type_check_daily(req_type) is True


# ========== default_due_date_iso_for_type ==========


class TestDefaultDueDateIsoForType:
    """Testes para default_due_date_iso_for_type."""

    def test_instant_type_default_today(self, anvisa_service):
        """Tipos instantâneos devem ter prazo default = hoje."""
        from datetime import date

        today = date(2025, 12, 27)
        result = anvisa_service.default_due_date_iso_for_type(
            "Alteração do Responsável Legal",
            today,
        )
        assert result == "2025-12-27"

    def test_non_instant_type_default_tomorrow(self, anvisa_service):
        """Tipos não instantâneos devem ter prazo default = hoje + 1."""
        from datetime import date

        today = date(2025, 12, 27)
        result = anvisa_service.default_due_date_iso_for_type(
            "Alteração de Nome Fantasia",
            today,
        )
        assert result == "2025-12-28"
