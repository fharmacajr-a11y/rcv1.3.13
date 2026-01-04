"""Testes unitários para AnvisaRequestsController.

Testa o controller headless com mocks, sem acesso real ao Supabase.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock

from src.modules.anvisa.controllers.anvisa_requests_controller import (
    AnvisaRequestsController,
)


def _create_fake_repo_module(
    *,
    fake_user_id: str = "user-123",
    fake_org_id: str = "org-456",
    fake_requests: list[dict[str, Any]] | None = None,
    fake_created: dict[str, Any] | None = None,
) -> types.ModuleType:
    """Cria módulo fake para infra.repositories.anvisa_requests_repository."""
    fake_module = types.ModuleType("anvisa_requests_repository")

    def _get_supabase_and_user() -> tuple[MagicMock, str]:
        return MagicMock(), fake_user_id

    def _resolve_org_id(user_id: str) -> str:
        return fake_org_id

    def list_requests(org_id: str) -> list[dict[str, Any]]:
        return fake_requests if fake_requests is not None else []

    def create_request(
        *,
        org_id: str,
        client_id: int,
        request_type: str,
        status: str,
    ) -> dict[str, Any]:
        return fake_created if fake_created is not None else {"id": 999}

    fake_module._get_supabase_and_user = _get_supabase_and_user  # type: ignore[attr-defined]
    fake_module._resolve_org_id = _resolve_org_id  # type: ignore[attr-defined]
    fake_module.list_requests = list_requests  # type: ignore[attr-defined]
    fake_module.create_request = create_request  # type: ignore[attr-defined]

    return fake_module


class TestResolveOrgId:
    """Testes para resolve_org_id."""

    def test_resolve_org_id_uses_repo_functions(self) -> None:
        """resolve_org_id deve usar funções do repositório e retornar org_id."""
        expected_org_id = "org-abc-123"

        fake_module = _create_fake_repo_module(
            fake_user_id="user-xyz",
            fake_org_id=expected_org_id,
        )

        # Injetar módulo fake
        original = sys.modules.get("src.infra.repositories.anvisa_requests_repository")
        sys.modules["src.infra.repositories.anvisa_requests_repository"] = fake_module

        try:
            controller = AnvisaRequestsController()
            result = controller.resolve_org_id()

            assert result == expected_org_id
        finally:
            # Restaurar módulo original
            if original is not None:
                sys.modules["src.infra.repositories.anvisa_requests_repository"] = original
            else:
                sys.modules.pop("src.infra.repositories.anvisa_requests_repository", None)


class TestListRequests:
    """Testes para list_requests."""

    def test_list_requests_delegates_to_repo(self) -> None:
        """list_requests deve delegar para o repositório e retornar lista."""
        expected_requests = [
            {"id": 1, "client_id": 100, "request_type": "Licença"},
            {"id": 2, "client_id": 200, "request_type": "Registro"},
        ]

        fake_module = _create_fake_repo_module(fake_requests=expected_requests)

        original = sys.modules.get("src.infra.repositories.anvisa_requests_repository")
        sys.modules["src.infra.repositories.anvisa_requests_repository"] = fake_module

        try:
            controller = AnvisaRequestsController()
            result = controller.list_requests("org-123")

            assert result == expected_requests
            assert len(result) == 2
        finally:
            if original is not None:
                sys.modules["src.infra.repositories.anvisa_requests_repository"] = original
            else:
                sys.modules.pop("src.infra.repositories.anvisa_requests_repository", None)


class TestCreateRequest:
    """Testes para create_request."""

    def test_create_request_delegates_to_repo(self) -> None:
        """create_request deve delegar para o repositório e retornar dict criado."""
        expected_created = {
            "id": 42,
            "org_id": "org-123",
            "client_id": 100,
            "request_type": "Registro",
            "status": "draft",
        }

        fake_module = _create_fake_repo_module(fake_created=expected_created)

        original = sys.modules.get("src.infra.repositories.anvisa_requests_repository")
        sys.modules["src.infra.repositories.anvisa_requests_repository"] = fake_module

        try:
            controller = AnvisaRequestsController()
            result = controller.create_request(
                org_id="org-123",
                client_id=100,
                request_type="Registro",
                status="draft",
            )

            assert result == expected_created
            assert result["id"] == 42
        finally:
            if original is not None:
                sys.modules["src.infra.repositories.anvisa_requests_repository"] = original
            else:
                sys.modules.pop("src.infra.repositories.anvisa_requests_repository", None)


class TestControllerInit:
    """Testes para inicialização do controller."""

    def test_controller_accepts_custom_logger(self) -> None:
        """Controller deve aceitar logger customizado."""
        custom_logger = MagicMock()
        controller = AnvisaRequestsController(logger=custom_logger)

        assert controller._log is custom_logger

    def test_controller_uses_default_logger_when_none(self) -> None:
        """Controller deve usar logger padrão quando não especificado."""
        controller = AnvisaRequestsController()

        assert controller._log is not None
        assert "anvisa_requests_controller" in controller._log.name
