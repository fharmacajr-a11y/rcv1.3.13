"""Testes unitários para AnvisaController headless.

Testa operações de delete e close sem dependências de GUI.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest


class FakeAnvisaRepository:
    """Repository fake para testes do controller."""

    def __init__(self) -> None:
        """Inicializa repository fake com dados em memória."""
        self.requests: dict[str, dict[str, Any]] = {
            "uuid-123": {"id": "uuid-123", "status": "ABERTA", "tipo": "Alteração RL"},
            "uuid-456": {"id": "uuid-456", "status": "EM_ANDAMENTO", "tipo": "Alteração RT"},
        }
        self.deleted: list[str] = []
        self.status_updates: list[tuple[str, str]] = []
        self.created_requests: list[dict[str, Any]] = []

        # Controle de falhas simuladas
        self.should_fail_delete = False
        self.should_fail_update = False
        self.should_fail_create = False
        self.next_uuid = "uuid-789"

    def delete_request(self, request_id: str) -> bool:
        """Simula exclusão de demanda.

        Args:
            request_id: UUID da demanda

        Returns:
            True se encontrou e excluiu, False caso contrário
        """
        if self.should_fail_delete:
            raise RuntimeError("Falha simulada no delete")

        if request_id in self.requests:
            del self.requests[request_id]
            self.deleted.append(request_id)
            return True
        return False

    def update_request_status(self, request_id: str, new_status: str) -> bool:
        """Simula atualização de status.

        Args:
            request_id: UUID da demanda
            new_status: Novo status

        Returns:
            True se encontrou e atualizou, False caso contrário
        """
        if self.should_fail_update:
            raise RuntimeError("Falha simulada no update")

        if request_id in self.requests:
            self.requests[request_id]["status"] = new_status
            self.status_updates.append((request_id, new_status))
            return True
        return False

    def create_request(
        self,
        *,
        org_id: str,
        client_id: int,
        request_type: str,
        status: str,
        created_by: str | None = None,
        payload: dict | None = None,
    ) -> str | None:
        """Simula criação de demanda.

        Args:
            org_id: ID da organização
            client_id: ID do cliente
            request_type: Tipo da demanda
            status: Status inicial
            created_by: ID do usuário (opcional)
            payload: Dados adicionais (opcional)

        Returns:
            UUID da demanda criada, ou None se falhar
        """
        if self.should_fail_create:
            raise RuntimeError("Falha simulada no create")

        # Criar registro
        new_id = self.next_uuid
        request_data = {
            "id": new_id,
            "org_id": org_id,
            "client_id": client_id,
            "request_type": request_type,
            "status": status,
            "created_by": created_by,
            "payload": payload,
        }

        self.requests[new_id] = request_data
        self.created_requests.append(request_data)

        return new_id


@pytest.fixture
def fake_repo() -> FakeAnvisaRepository:
    """Fixture que retorna repository fake."""
    return FakeAnvisaRepository()


@pytest.fixture
def controller(fake_repo: FakeAnvisaRepository):
    """Fixture que retorna controller com repository fake."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    return AnvisaController(repository=fake_repo, logger=logger)


def test_controller_delete_request_success(controller, fake_repo):
    """Testa exclusão bem-sucedida via controller."""
    # Arrange
    request_id = "uuid-123"
    assert request_id in fake_repo.requests

    # Act
    result = controller.delete_request(request_id)

    # Assert
    assert result is True
    assert request_id not in fake_repo.requests
    assert request_id in fake_repo.deleted


def test_controller_delete_request_not_found(controller, fake_repo):
    """Testa exclusão de demanda inexistente."""
    # Arrange
    request_id = "uuid-nao-existe"
    assert request_id not in fake_repo.requests

    # Act
    result = controller.delete_request(request_id)

    # Assert
    assert result is False
    assert request_id not in fake_repo.deleted


def test_controller_delete_request_exception(controller, fake_repo):
    """Testa tratamento de exceção no delete."""
    # Arrange
    request_id = "uuid-123"
    fake_repo.should_fail_delete = True

    # Act
    result = controller.delete_request(request_id)

    # Assert
    assert result is False
    assert request_id in fake_repo.requests  # Não foi excluído


def test_controller_close_request_success(controller, fake_repo):
    """Testa finalização bem-sucedida via controller."""
    # Arrange
    request_id = "uuid-123"
    assert fake_repo.requests[request_id]["status"] == "ABERTA"

    # Act
    result = controller.close_request(request_id)

    # Assert
    assert result is True
    assert fake_repo.requests[request_id]["status"] == "done"
    assert ("uuid-123", "done") in fake_repo.status_updates


def test_controller_close_request_not_found(controller, fake_repo):
    """Testa finalização de demanda inexistente."""
    # Arrange
    request_id = "uuid-nao-existe"
    assert request_id not in fake_repo.requests

    # Act
    result = controller.close_request(request_id)

    # Assert
    assert result is False
    assert len(fake_repo.status_updates) == 0


def test_controller_close_request_exception(controller, fake_repo):
    """Testa tratamento de exceção no close."""
    # Arrange
    request_id = "uuid-123"
    original_status = fake_repo.requests[request_id]["status"]
    fake_repo.should_fail_update = True

    # Act
    result = controller.close_request(request_id)

    # Assert
    assert result is False
    assert fake_repo.requests[request_id]["status"] == original_status  # Não mudou


def test_controller_delete_uses_string_uuid(controller, fake_repo):
    """Verifica que controller aceita UUID como string (não int)."""
    # Arrange
    request_id = "uuid-456"

    # Act
    result = controller.delete_request(request_id)

    # Assert
    assert result is True
    assert isinstance(request_id, str)  # Garantir que é string


# ===== Testes de set_status =====


def test_controller_set_status_success(controller, fake_repo):
    """Testa atualização genérica de status bem-sucedida."""
    # Arrange
    request_id = "uuid-123"
    new_status = "custom_status"

    # Act
    result = controller.set_status(request_id, new_status)

    # Assert
    assert result is True
    assert ("uuid-123", "custom_status") in fake_repo.status_updates


def test_controller_set_status_not_found(controller, fake_repo):
    """Verifica que retorna False quando demanda não existe."""
    # Arrange
    request_id = "uuid-inexistente"

    # Act
    result = controller.set_status(request_id, "done")

    # Assert
    assert result is False


def test_controller_set_status_exception(controller, fake_repo):
    """Verifica que retorna False em caso de exceção."""
    # Arrange
    request_id = "uuid-123"
    fake_repo.should_fail_update = True

    # Act
    result = controller.set_status(request_id, "done")

    # Assert
    assert result is False


# ===== Testes de close_request =====


def test_controller_close_uses_string_uuid(controller, fake_repo):
    """Verifica que controller aceita UUID como string (não int)."""
    # Arrange
    request_id = "uuid-456"

    # Act
    result = controller.close_request(request_id)

    # Assert
    assert result is True
    assert isinstance(request_id, str)  # Garantir que é string


def test_controller_close_sets_status_to_finalizada(controller, fake_repo):
    """Verifica que close_request define status como 'done'."""
    # Arrange
    request_id = "uuid-123"

    # Act
    controller.close_request(request_id)

    # Assert
    assert fake_repo.requests[request_id]["status"] == "done"


def test_controller_close_delegates_to_set_status(controller, fake_repo):
    """Verifica que close_request delega para set_status."""
    # Arrange
    request_id = "uuid-456"

    # Act
    result = controller.close_request(request_id)

    # Assert
    assert result is True
    # Verificar que update foi chamado com "done"
    assert ("uuid-456", "done") in fake_repo.status_updates


# ===== Testes de cancel_request =====


def test_controller_cancel_request_success(controller, fake_repo):
    """Testa cancelamento bem-sucedido de demanda."""
    # Arrange
    request_id = "uuid-123"

    # Act
    result = controller.cancel_request(request_id)

    # Assert
    assert result is True
    assert ("uuid-123", "canceled") in fake_repo.status_updates


def test_controller_cancel_request_not_found(controller, fake_repo):
    """Verifica que retorna False quando demanda não existe."""
    # Arrange
    request_id = "uuid-inexistente"

    # Act
    result = controller.cancel_request(request_id)

    # Assert
    assert result is False


def test_controller_cancel_request_exception(controller, fake_repo):
    """Verifica que retorna False em caso de exceção."""
    # Arrange
    request_id = "uuid-123"
    fake_repo.should_fail_update = True

    # Act
    result = controller.cancel_request(request_id)

    # Assert
    assert result is False


def test_controller_cancel_sets_status_to_canceled(controller, fake_repo):
    """Verifica que cancel_request define status como 'canceled'."""
    # Arrange
    request_id = "uuid-456"

    # Act
    controller.cancel_request(request_id)

    # Assert
    assert fake_repo.requests[request_id]["status"] == "canceled"


def test_controller_cancel_delegates_to_set_status(controller, fake_repo):
    """Verifica que cancel_request delega para set_status."""
    # Arrange
    request_id = "uuid-123"

    # Act
    result = controller.cancel_request(request_id)

    # Assert
    assert result is True
    # Verificar que update foi chamado com "canceled"
    assert ("uuid-123", "canceled") in fake_repo.status_updates


# ===== Testes de create_request =====


def test_controller_create_request_success(controller, fake_repo):
    """Testa criação bem-sucedida via controller."""
    # Arrange
    org_id = "org-123"
    client_id = "456"
    request_type = "Alteração de RT"

    # Act
    result = controller.create_request(
        org_id=org_id,
        client_id=client_id,
        request_type=request_type,
    )

    # Assert
    assert result == "uuid-789"
    assert len(fake_repo.created_requests) == 1
    created = fake_repo.created_requests[0]
    assert created["org_id"] == org_id
    assert created["client_id"] == 456  # Convertido para int
    assert created["request_type"] == request_type
    assert created["status"] == "draft"  # DEFAULT_CREATE_STATUS


def test_controller_create_request_with_payload(controller, fake_repo):
    """Testa criação com payload customizado."""
    # Arrange
    org_id = "org-123"
    client_id = "456"
    request_type = "Alteração de RT"
    payload = {"extra": "data"}

    # Act
    result = controller.create_request(
        org_id=org_id,
        client_id=client_id,
        request_type=request_type,
        payload=payload,
    )

    # Assert
    assert result == "uuid-789"
    created = fake_repo.created_requests[0]
    assert created["payload"] == payload


def test_controller_create_request_converts_client_id_to_int(controller, fake_repo):
    """Verifica que client_id é convertido de string para int."""
    # Act
    controller.create_request(
        org_id="org-123",
        client_id="999",
        request_type="Alteração de RT",
    )

    # Assert
    created = fake_repo.created_requests[0]
    assert created["client_id"] == 999
    assert isinstance(created["client_id"], int)


def test_controller_create_request_uses_default_status(controller, fake_repo):
    """Verifica que status padrão é DEFAULT_CREATE_STATUS."""
    # Act
    controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="Alteração de RT",
    )

    # Assert
    created = fake_repo.created_requests[0]
    assert created["status"] == "draft"


def test_controller_create_request_failure(controller, fake_repo):
    """Testa falha ao criar demanda."""
    # Arrange
    fake_repo.should_fail_create = True

    # Act
    result = controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="Alteração de RT",
    )

    # Assert
    assert result is None
    assert len(fake_repo.created_requests) == 0


def test_controller_create_request_returns_uuid_string(controller, fake_repo):
    """Verifica que retorna UUID como string."""
    # Act
    result = controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="Alteração de RT",
    )

    # Assert
    assert isinstance(result, str)
    assert result == "uuid-789"
