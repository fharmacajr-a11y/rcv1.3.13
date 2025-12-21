"""Testes unitários para aumentar cobertura do notifications_service.

Cobre edge cases:
- parse de created_at com "Z" e com "+00:00"
- created_at ausente/inválido -> fallback não quebra
- RC_INITIALS_MAP inválido (JSON quebrado) -> não quebra e faz fallback
- actor_email None/vazio -> actor_display_name/initial coerentes
- request_id_short quando request_id curto/vazio
- fetch_latest retorna lista vazia quando sem org_id
- count_unread retorna 0 quando sem org_id
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch


def test_fetch_latest_for_ui_created_at_with_z() -> None:
    """Testa parse de created_at com formato ISO 8601 terminando em Z."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-1",
            "created_at": "2025-12-20T14:30:00Z",  # Com Z
            "message": "Test",
            "is_read": False,
            "actor_email": "test@example.com",
            "request_id": "req-12345678",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-123"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações com formatação UI
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar que created_at_local_str foi gerado
    assert len(notifications) == 1
    notif = notifications[0]
    assert "created_at_local_str" in notif
    assert "/" in notif["created_at_local_str"]  # Formato DD/MM/YYYY
    assert ":" in notif["created_at_local_str"]  # Formato HH:MM


def test_fetch_latest_for_ui_created_at_with_offset() -> None:
    """Testa parse de created_at com formato ISO 8601 com offset (+00:00)."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-2",
            "created_at": "2025-12-20T14:30:00+00:00",  # Com +00:00
            "message": "Test offset",
            "is_read": False,
            "actor_email": "test2@example.com",
            "request_id": "req-87654321",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-456"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-456", "email": "test2@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar parse correto
    assert len(notifications) == 1
    notif = notifications[0]
    assert "created_at_local_str" in notif
    assert notif["created_at_local_str"] != "—"  # Não deve usar fallback


def test_fetch_latest_for_ui_created_at_missing() -> None:
    """Testa comportamento quando created_at está ausente."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório (created_at ausente)
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-3",
            "message": "No timestamp",
            "is_read": False,
            "actor_email": "test3@example.com",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-789"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-789", "email": "test3@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar fallback
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif["created_at_local_str"] == "—"  # Fallback quando ausente


def test_fetch_latest_for_ui_created_at_invalid() -> None:
    """Testa comportamento quando created_at é inválido."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório (created_at inválido)
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-4",
            "created_at": "invalid-timestamp-format",
            "message": "Invalid time",
            "is_read": False,
            "actor_email": "test4@example.com",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-abc"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-abc", "email": "test4@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações (não deve crashar)
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar que retornou com fallback
    assert len(notifications) == 1
    notif = notifications[0]
    assert "created_at_local_str" in notif
    # Deve usar fallback (primeiros 16 chars do timestamp inválido)
    assert notif["created_at_local_str"] == "invalid-timestam"


def test_fetch_latest_for_ui_rc_initials_map_invalid_json() -> None:
    """Testa que JSON inválido no RC_INITIALS_MAP não quebra o serviço."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-5",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "Test JSON broken",
            "is_read": False,
            "actor_email": "rcgestor@example.com",
            "request_id": "req-xyz",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-def"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-def", "email": "test@example.com"}

    # Configurar RC_INITIALS_MAP inválido no env
    with patch.dict(os.environ, {"RC_INITIALS_MAP": "invalid-json-{[}"}, clear=False):
        # Criar service (deve lidar com JSON quebrado)
        service = NotificationsService(
            repository=mock_repo,
            org_id_provider=mock_org_id_provider,
            user_provider=mock_user_provider,
        )

        # Buscar notificações (não deve crashar)
        notifications = service.fetch_latest_for_ui(limit=10)

        # Verificar que retornou com fallback
        assert len(notifications) == 1
        notif = notifications[0]

        # Deve usar fallback do email (prefixo antes do @)
        assert "actor_display_name" in notif
        assert notif["actor_display_name"] == "Rcgestor"  # Capitalizado


def test_fetch_latest_for_ui_actor_email_none() -> None:
    """Testa comportamento quando actor_email é None."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório (actor_email None)
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-6",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "No actor",
            "is_read": False,
            "actor_email": None,
            "request_id": "req-123",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-ghi"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-ghi", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar fallback
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif["actor_display_name"] == "?"
    assert notif["actor_initial"] == ""


def test_fetch_latest_for_ui_actor_email_empty() -> None:
    """Testa comportamento quando actor_email é string vazia."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório (actor_email vazio)
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-7",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "Empty actor",
            "is_read": False,
            "actor_email": "",
            "request_id": "req-456",
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-jkl"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-jkl", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar fallback
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif["actor_display_name"] == "?"
    assert notif["actor_initial"] == ""


def test_fetch_latest_for_ui_request_id_short() -> None:
    """Testa request_id_short quando request_id é curto (< 8 chars)."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-8",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "Short req_id",
            "is_read": False,
            "actor_email": "test@example.com",
            "request_id": "short",  # Menos de 8 caracteres
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-mno"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-mno", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar fallback
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif["request_id_short"] == "—"  # Fallback quando curto


def test_fetch_latest_for_ui_request_id_empty() -> None:
    """Testa request_id_short quando request_id está ausente ou vazio."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-9",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "No req_id",
            "is_read": False,
            "actor_email": "test@example.com",
            "request_id": "",  # Vazio
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-pqr"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-pqr", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar fallback
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif["request_id_short"] == "—"


def test_fetch_latest_without_org_id() -> None:
    """Testa fetch_latest quando org_id não disponível."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()

    # Providers (org_id retorna None)
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

    # Buscar notificações (deve retornar lista vazia)
    notifications = service.fetch_latest(limit=10)

    # Verificar lista vazia
    assert notifications == []

    # Repositório NÃO deve ser chamado
    mock_repo.list_notifications.assert_not_called()


def test_fetch_unread_count_without_org_id() -> None:
    """Testa fetch_unread_count quando org_id não disponível."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()

    # Providers (org_id retorna None)
    def mock_org_id_provider() -> None:
        return None

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-456", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Contar não lidas (deve retornar 0)
    count = service.fetch_unread_count()

    # Verificar 0
    assert count == 0

    # Repositório NÃO deve ser chamado
    mock_repo.count_unread.assert_not_called()


def test_fetch_latest_repo_exception() -> None:
    """Testa fetch_latest quando repositório lança exceção."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório que lança exceção
    mock_repo = MagicMock()
    mock_repo.list_notifications.side_effect = Exception("Database error")

    # Providers
    def mock_org_id_provider() -> str:
        return "org-error"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-error", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações (não deve propagar exceção)
    notifications = service.fetch_latest(limit=10)

    # Deve retornar lista vazia em caso de erro
    assert notifications == []


def test_fetch_unread_count_repo_exception() -> None:
    """Testa fetch_unread_count quando repositório lança exceção."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório que lança exceção
    mock_repo = MagicMock()
    mock_repo.count_unread.side_effect = RuntimeError("Count failed")

    # Providers
    def mock_org_id_provider() -> str:
        return "org-error2"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-error2", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Contar não lidas (não deve propagar exceção)
    count = service.fetch_unread_count()

    # Deve retornar 0 em caso de erro
    assert count == 0


def test_mark_all_read_repo_exception() -> None:
    """Testa mark_all_read quando repositório lança exceção."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório que lança exceção
    mock_repo = MagicMock()
    mock_repo.mark_all_read.side_effect = Exception("Update failed")

    # Providers
    def mock_org_id_provider() -> str:
        return "org-error3"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-error3", "email": "test@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Marcar todas como lidas (não deve propagar exceção)
    result = service.mark_all_read()

    # Deve retornar False em caso de erro
    assert result is False
