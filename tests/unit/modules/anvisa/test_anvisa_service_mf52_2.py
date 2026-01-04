"""Testes adicionais para MF52.2 - subir cobertura de anvisa_service para >=90%."""

from typing import cast
from unittest.mock import Mock
from src.modules.anvisa.services.anvisa_service import AnvisaService
from datetime import datetime, date


class TestAnvisaServiceMF52Coverage:
    """Testes para cobrir linhas missing específicas em anvisa_service.py."""

    def test_check_duplicate_open_request_exception(self, monkeypatch):
        """Testa check_duplicate_open_request com exceção no repo (linhas 163-165)."""
        # Setup fake repo
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock list_requests que falha
        def raise_error(org_id):
            raise RuntimeError("DB connection failed")

        monkeypatch.setattr("src.infra.repositories.anvisa_requests_repository.list_requests", raise_error)

        # Execute
        result = service.check_duplicate_open_request("org123", "456", "AFE")

        # Deve retornar None em caso de exceção
        assert result is None

    def test_build_main_rows_with_initial_resolution(self):
        """Testa build_main_rows com resolução de iniciais (linhas 396->398)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock resolve_initial_from_email
        service.resolve_initial_from_email = Mock(return_value="A")

        fake_requests = [
            {
                "id": "req-1",
                "client_id": "123",
                "request_type": "AFE",
                "status": "done",
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-16T11:00:00Z",
                "payload": {"created_by": "admin@company.com", "updated_by": "admin@company.com"},
                "client": {"id": 123, "razao_social": "Empresa Test", "cnpj": "12345678000190"},
            }
        ]

        # Mock service methods
        service.group_by_client = Mock(return_value={"123": fake_requests})
        service.summarize_demands = Mock(return_value=("1 demanda finalizada", datetime.now()))
        service.format_dt_local = Mock(return_value="16/01 - 11:00")
        service._parse_iso_datetime = Mock(return_value=datetime.now())

        # Execute
        groups, rows = service.build_main_rows(fake_requests)

        # Deve ter resolvido inicial corretamente
        assert len(rows) == 1
        row = rows[0]
        last_update_display = row.get("last_update_display")
        assert last_update_display is not None
        assert "(A)" in last_update_display

    def test_format_due_date_iso_to_br_empty_string(self):
        """Testa format_due_date_iso_to_br com string vazia (linhas 783-787)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # String vazia deve retornar string vazia
        result = service.format_due_date_iso_to_br("")
        assert result == ""

        # String só com espaços deve retornar string vazia
        result = service.format_due_date_iso_to_br("   ")
        assert result == ""

    def test_format_due_date_iso_to_br_invalid_format(self):
        """Testa format_due_date_iso_to_br com formato inválido (exception path)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Formato inválido deve retornar string vazia
        result = service.format_due_date_iso_to_br("invalid-date")
        assert result == ""

        result = service.format_due_date_iso_to_br("2025-13-45")  # Mês/dia inválidos
        assert result == ""

    def test_format_dt_local_dash_no_space(self):
        """Testa format_dt_local_dash quando não há espaço no resultado (linha 803)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock format_dt_local que retorna string sem espaço
        service.format_dt_local = Mock(return_value="16/01")

        dt = datetime(2025, 1, 16, 11, 0)
        result = service.format_dt_local_dash(dt)

        # Deve retornar a string original (sem substituição)
        assert result == "16/01"

    def test_resolve_initial_from_email_env_map_exception(self, monkeypatch):
        """Testa resolve_initial_from_email com exceção no load_env_author_names (linhas 826->834, 828->834)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock load_env_author_names que falha
        def raise_error():
            raise ImportError("Module not found")

        monkeypatch.setattr("src.modules.hub.services.authors_service.load_env_author_names", raise_error)

        # Deve usar fallback (primeira letra do email)
        result = service.resolve_initial_from_email("admin@company.com")
        assert result == "A"

        # Email vazio deve retornar string vazia
        result = service.resolve_initial_from_email("")
        assert result == ""

    def test_parse_due_date_br_exception_path(self):
        """Testa parse_due_date_br com exceção no parsing (linha 856)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Formato inválido deve retornar None
        result = service.parse_due_date_br("invalid-date")
        assert result is None

        result = service.parse_due_date_br("45/13/2025")  # Dia/mês inválidos
        assert result is None

        # String vazia deve retornar None
        result = service.parse_due_date_br("")
        assert result is None

    def test_default_due_date_iso_for_type_non_daily_check(self):
        """Testa default_due_date_iso_for_type para tipos não-daily (linhas 904-906)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock request_type_check_daily retornando False
        service.request_type_check_daily = Mock(return_value=False)

        today = date(2025, 1, 15)
        result = service.default_due_date_iso_for_type("Alteração do Responsável Legal", today)

        # Deve retornar today.isoformat() (não tomorrow)
        assert result == "2025-01-15"

    def test_build_payload_for_new_request_with_notes(self):
        """Testa build_payload_for_new_request com notes não-vazias (linhas 925-934)."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock request_type_check_daily
        service.request_type_check_daily = Mock(return_value=True)

        # Notes longa (>500 chars)
        long_notes = "A" * 600

        result = service.build_payload_for_new_request(request_type="AFE", due_date_iso="2025-01-16", notes=long_notes)

        # Deve incluir notes truncadas
        assert "notes" in result
        notes_value = cast(str, result["notes"])
        assert len(notes_value) == 500
        assert notes_value == "A" * 500

    def test_build_payload_for_new_request_empty_notes(self):
        """Testa build_payload_for_new_request com notes vazias."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        # Mock request_type_check_daily
        service.request_type_check_daily = Mock(return_value=False)

        result = service.build_payload_for_new_request(
            request_type="Alteração do Responsável Legal", due_date_iso="2025-01-16", notes=""
        )

        # Não deve incluir notes quando vazio
        assert "notes" not in result
        assert result["due_date"] == "2025-01-16"
        assert result["check_daily"] is False

    def test_build_payload_for_new_request_whitespace_notes(self):
        """Testa build_payload_for_new_request com notes só com espaços."""
        fake_repo = Mock()
        service = AnvisaService(fake_repo)

        service.request_type_check_daily = Mock(return_value=True)

        result = service.build_payload_for_new_request(
            request_type="AFE", due_date_iso="2025-01-16", notes="   \n\t   "
        )

        # Notes só com espaços não deve ser incluída
        assert "notes" not in result
