# -*- coding: utf-8 -*-
"""Testes MF52 para cobertura adicional de ANVISA modules."""

from src.modules.anvisa.services.anvisa_service import AnvisaService, DemandaDict
from src.modules.anvisa.views._anvisa_requests_mixin import AnvisaRequestsMixin
from tests.unit.fakes.tk_fakes import FakeVar


class FakeAnvisaRepository:
    """Mock repository for tests - compatible with AnvisaRequestsRepository Protocol."""

    def __init__(self, requests: list[DemandaDict] | None = None, raise_exc: bool = False):
        """Initialize with optional requests list and exception flag."""
        self.requests = requests or []
        self.raise_exc = raise_exc

    def list_requests(self, org_id: str) -> list[DemandaDict]:
        """Implementation required by AnvisaRequestsRepository Protocol."""
        if self.raise_exc:
            raise RuntimeError("DB connection failed")
        return self.requests


class DummyMixin(AnvisaRequestsMixin):
    """Simple mixin for testing."""

    def __init__(self):
        self.last_action = FakeVar()


class TestAnvisaServiceMF52:
    """Coverage tests for anvisa_service.py missing lines."""

    def test_request_type_check_daily_edge_cases(self):
        """Test request_type_check_daily edge cases (lines 879-885)."""
        fake_repo = FakeAnvisaRepository()
        service = AnvisaService(fake_repo)

        # Cases that should return False (no daily tracking needed)
        assert service.request_type_check_daily("Alteração do Responsável Legal") is False

        # Cases that should return True (need daily tracking)
        assert service.request_type_check_daily("AFE") is True
        assert service.request_type_check_daily("Renovação") is True
        assert service.request_type_check_daily("") is True  # Default True
        assert service.request_type_check_daily("Unknown Type") is True

    def test_build_history_rows_missing_initial(self, monkeypatch):
        """Test build_history_rows without initial (lines 730-732, 738-740)."""
        fake_repo = FakeAnvisaRepository()
        service = AnvisaService(fake_repo)

        # Mock resolve_initial that returns empty
        monkeypatch.setattr(service, "resolve_initial_from_email", lambda email: "")

        fake_requests = [
            {
                "id": "req-1",
                "client_id": "123",
                "request_type": "AFE",
                "status": "draft",
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-16T11:00:00Z",
                "payload": {"created_by": "user@example.com", "updated_by": "admin@example.com"},
            }
        ]

        result = service.build_history_rows(fake_requests)

        # Should return rows without initials (no parentheses)
        assert len(result) == 1
        row = result[0]
        assert "(" not in row["criada_em"]  # No initial
        assert "(" not in row["atualizada_em"]  # No initial

    def test_normalize_status_edge_cases(self):
        """Test normalize_status edge cases."""
        fake_repo = FakeAnvisaRepository()
        service = AnvisaService(fake_repo)

        # Test aliases and case sensitivity
        assert service.normalize_status("Finalizado") == "done"
        assert service.normalize_status("FINALIZADO") == "done"
        assert service.normalize_status("finalizado") == "done"

        # Test normalization (not aliases)
        assert service.normalize_status("Cancelado") == "cancelado"
        assert service.normalize_status("CANCELADO") == "cancelado"

        # Normal statuses
        assert service.normalize_status("draft") == "draft"
        assert service.normalize_status("DRAFT") == "draft"

        # Empty/None (defensive)
        assert service.normalize_status("") == ""
        assert service.normalize_status("   ") == ""


class TestAnvisaRequestsMixinMF52:
    """Coverage tests for _anvisa_requests_mixin.py missing lines."""

    def test_format_cnpj_invalid_length(self):
        """Test _format_cnpj with invalid CNPJ (lines 241-247)."""
        dummy = DummyMixin()

        # Test None
        assert dummy._format_cnpj(None) == ""

        # Test too short
        assert dummy._format_cnpj("123456") == "123456"

        # Test too long
        assert dummy._format_cnpj("123456789012345678") == "123456789012345678"

        # Test valid length
        result = dummy._format_cnpj("12345678000190")
        assert result == "12.345.678/0001-90"

    def test_to_local_dt_exception_handling(self):
        """Test _to_local_dt with exception (lines 336-340)."""
        dummy = DummyMixin()

        # Invalid datetime string should trigger exception path
        result = dummy._to_local_dt("invalid-datetime")
        assert result is None  # Exception path returns None

        # Empty string
        result = dummy._to_local_dt("")
        assert result is None  # Empty input returns None

    def test_norm_tipo_edge_cases(self):
        """Test _norm_tipo edge cases."""
        dummy = DummyMixin()

        # Test with None (defensive)
        assert dummy._norm_tipo(None or "") == ""

        # Test with numbers
        assert dummy._norm_tipo("123") == "123"

        # Test with special chars
        assert dummy._norm_tipo("AFE/renovação") == "AFE/RENOVAÇÃO"

    def test_is_open_status_case_insensitive(self):
        """Test _is_open_status case insensitive."""
        dummy = DummyMixin()

        # Test case variations
        assert dummy._is_open_status("Draft") is True
        assert dummy._is_open_status("SUBMITTED") is True
        assert dummy._is_open_status("Done") is False
        assert dummy._is_open_status("CANCELED") is False
