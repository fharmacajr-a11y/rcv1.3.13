"""Testes unitários para AnvisaClientLookupController.

Testa o controller de lookup com mocks, sem acesso real ao Supabase.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

from src.modules.anvisa.controllers.anvisa_client_lookup_controller import (
    AnvisaClientLookupController,
)


def _create_fake_supabase_module(
    *,
    fake_data: list[dict] | None = None,
) -> types.ModuleType:
    """Cria módulo fake para infra.supabase_client."""
    fake_module = types.ModuleType("supabase_client")

    def get_supabase() -> MagicMock:
        mock_sb = MagicMock()
        mock_response = MagicMock()
        mock_response.data = fake_data if fake_data is not None else []

        # Configurar chain de chamadas
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        return mock_sb

    fake_module.get_supabase = get_supabase  # type: ignore[attr-defined]

    return fake_module


class TestLookupClientCnpjRazao:
    """Testes para lookup_client_cnpj_razao."""

    def test_returns_cnpj_razao_when_data_found(self) -> None:
        """Deve retornar cnpj e razao quando cliente encontrado."""
        expected_cnpj = "12.345.678/0001-90"
        expected_razao = "Empresa Teste LTDA"

        fake_module = _create_fake_supabase_module(fake_data=[{"cnpj": expected_cnpj, "razao_social": expected_razao}])

        original = sys.modules.get("src.infra.supabase_client")
        sys.modules["src.infra.supabase_client"] = fake_module

        try:
            controller = AnvisaClientLookupController()
            cnpj, razao = controller.lookup_client_cnpj_razao(
                org_id="org-123",
                client_id="client-456",
            )

            assert cnpj == expected_cnpj
            assert razao == expected_razao
        finally:
            if original is not None:
                sys.modules["src.infra.supabase_client"] = original
            else:
                sys.modules.pop("src.infra.supabase_client", None)

    def test_returns_none_empty_when_data_not_found(self) -> None:
        """Deve retornar (None, '') quando cliente não encontrado."""
        fake_module = _create_fake_supabase_module(fake_data=[])

        original = sys.modules.get("src.infra.supabase_client")
        sys.modules["src.infra.supabase_client"] = fake_module

        try:
            controller = AnvisaClientLookupController()
            cnpj, razao = controller.lookup_client_cnpj_razao(
                org_id="org-123",
                client_id="client-inexistente",
            )

            assert cnpj is None
            assert razao == ""
        finally:
            if original is not None:
                sys.modules["src.infra.supabase_client"] = original
            else:
                sys.modules.pop("src.infra.supabase_client", None)

    def test_returns_none_empty_on_exception(self) -> None:
        """Deve retornar (None, '') quando ocorre exceção."""
        fake_module = types.ModuleType("supabase_client")

        def get_supabase_error() -> MagicMock:
            mock_sb = MagicMock()
            mock_sb.table.side_effect = Exception("Connection error")
            return mock_sb

        fake_module.get_supabase = get_supabase_error  # type: ignore[attr-defined]

        original = sys.modules.get("src.infra.supabase_client")
        sys.modules["src.infra.supabase_client"] = fake_module

        try:
            controller = AnvisaClientLookupController()
            cnpj, razao = controller.lookup_client_cnpj_razao(
                org_id="org-123",
                client_id="client-456",
            )

            assert cnpj is None
            assert razao == ""
        finally:
            if original is not None:
                sys.modules["src.infra.supabase_client"] = original
            else:
                sys.modules.pop("src.infra.supabase_client", None)


class TestControllerInit:
    """Testes para inicialização do controller."""

    def test_controller_accepts_custom_logger(self) -> None:
        """Controller deve aceitar logger customizado."""
        custom_logger = MagicMock()
        controller = AnvisaClientLookupController(logger=custom_logger)

        assert controller._log is custom_logger

    def test_controller_uses_default_logger_when_none(self) -> None:
        """Controller deve usar logger padrão quando não especificado."""
        controller = AnvisaClientLookupController()

        assert controller._log is not None
        assert "anvisa_client_lookup_controller" in controller._log.name
