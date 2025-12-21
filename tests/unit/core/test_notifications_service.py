"""Testes unitários para NotificationsService.

Testa que publish usa actor_user_id corretamente.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def test_notifications_service_publish_uses_actor_user_id() -> None:
    """Testa que NotificationsService.publish passa actor_user_id ao repositório."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.insert_notification.return_value = True

    # Mock dos providers
    def mock_org_id_provider() -> str:
        return "org-test-123"

    def mock_user_provider() -> dict[str, Any]:
        return {
            "uid": "user-uuid-789",  # UUID do usuário
            "email": "testuser@example.com",
        }

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Publicar notificação
    result = service.publish(
        module="anvisa",
        event="created",
        message="Test notification",
        client_id="client-456",
        request_id="req-xyz",
    )

    # Verificar sucesso
    assert result is True

    # Verificar que repo.insert_notification foi chamado com actor_user_id
    mock_repo.insert_notification.assert_called_once()
    call_kwargs = mock_repo.insert_notification.call_args[1]

    assert call_kwargs["org_id"] == "org-test-123"
    assert call_kwargs["module"] == "anvisa"
    assert call_kwargs["event"] == "created"
    assert call_kwargs["message"] == "Test notification"

    # CRÍTICO: deve usar actor_user_id (não actor_uid)
    assert "actor_user_id" in call_kwargs
    assert call_kwargs["actor_user_id"] == "user-uuid-789"
    assert "actor_uid" not in call_kwargs

    assert call_kwargs["actor_email"] == "testuser@example.com"
    assert call_kwargs["client_id"] == "client-456"
    assert call_kwargs["request_id"] == "req-xyz"


def test_notifications_service_publish_without_user() -> None:
    """Testa publish quando user_provider retorna None."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.insert_notification.return_value = True

    # Mock dos providers
    def mock_org_id_provider() -> str:
        return "org-test-123"

    def mock_user_provider() -> None:
        return None  # Sem usuário

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Publicar notificação
    result = service.publish(
        module="anvisa",
        event="created",
        message="Test without user",
    )

    # Deve continuar funcionando
    assert result is True

    # Verificar que repo foi chamado com actor_user_id=None
    call_kwargs = mock_repo.insert_notification.call_args[1]
    assert call_kwargs["actor_user_id"] is None
    assert call_kwargs["actor_email"] is None


def test_notifications_service_publish_without_org_id() -> None:
    """Testa que publish retorna False quando org_id não está disponível."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()

    # Mock dos providers (org_id retorna None)
    def mock_org_id_provider() -> None:
        return None

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Publicar notificação (deve falhar)
    result = service.publish(
        module="anvisa",
        event="created",
        message="Test without org_id",
    )

    # Deve retornar False
    assert result is False

    # Repositório NÃO deve ser chamado
    mock_repo.insert_notification.assert_not_called()


def test_notifications_service_publish_repo_fails() -> None:
    """Testa que publish retorna False quando repo.insert_notification falha."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório (retorna False = erro)
    mock_repo = MagicMock()
    mock_repo.insert_notification.return_value = False

    # Mock dos providers
    def mock_org_id_provider() -> str:
        return "org-test-123"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Publicar notificação
    result = service.publish(
        module="anvisa",
        event="created",
        message="Test repo failure",
    )

    # Deve retornar False
    assert result is False
