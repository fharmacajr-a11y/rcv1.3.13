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


def test_notifications_service_fetch_latest_for_ui_includes_own_notifications() -> None:
    """Testa que fetch_latest_for_ui inclui as próprias notificações (include_self=True)."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "1",
            "message": "x",
            "created_at": "2025-12-21T10:00:00Z",
            "actor_email": "me@example.com",
        }
    ]
    # Mockar métodos de hidden
    mock_repo.get_user_hidden_before.return_value = None
    mock_repo.list_hidden_notification_ids.return_value = []

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "me@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    _ = service.fetch_latest_for_ui(limit=10)

    # O repo deve ser chamado com exclude_actor_email=None (incluir próprias notificações)
    mock_repo.list_notifications.assert_called_once_with("org-123", 30, exclude_actor_email=None)


def test_fetch_unread_count_include_self_calls_repo_without_exclude() -> None:
    """Testa que fetch_unread_count com include_self=True passa exclude_actor_email=None."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    mock_repo.count_unread.return_value = 3

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "u1", "email": "me@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    _ = service.fetch_unread_count(include_self=True)

    mock_repo.count_unread.assert_called_once_with("org-123", exclude_actor_email=None)


def test_fetch_unread_count_default_excludes_self() -> None:
    """Testa que fetch_unread_count sem parâmetros exclui próprias notificações."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    mock_repo.count_unread.return_value = 3

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "u1", "email": "me@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    _ = service.fetch_unread_count()

    mock_repo.count_unread.assert_called_once_with("org-123", exclude_actor_email="me@example.com")


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


def test_notifications_service_resolve_display_name() -> None:
    """Testa resolve_display_name com RC_INITIALS_MAP."""
    import os
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()

    # Mock dos providers
    def mock_org_id_provider() -> str:
        return "org-test-123"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    # Configurar RC_INITIALS_MAP (mock do .env)
    original_env = os.getenv("RC_INITIALS_MAP")
    try:
        os.environ["RC_INITIALS_MAP"] = '{"farmacajr@gmail.com":"Junior","test@example.com":"Testador"}'

        # Criar service
        service = NotificationsService(
            repository=mock_repo,
            org_id_provider=mock_org_id_provider,
            user_provider=mock_user_provider,
        )

        # Testar resolução de nome via RC_INITIALS_MAP
        assert service.resolve_display_name("farmacajr@gmail.com") == "Junior"
        assert service.resolve_display_name("test@example.com") == "Testador"

        # Testar fallback (email não mapeado)
        assert service.resolve_display_name("unknown@example.com") == "Unknown"

        # Testar email vazio
        assert service.resolve_display_name(None) == "?"
        assert service.resolve_display_name("") == "?"

    finally:
        # Restaurar env original
        if original_env:
            os.environ["RC_INITIALS_MAP"] = original_env
        elif "RC_INITIALS_MAP" in os.environ:
            del os.environ["RC_INITIALS_MAP"]


def test_notifications_service_fetch_latest_excludes_own_notifications() -> None:
    """Testa que fetch_latest exclui notificações do próprio usuário."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {"id": "1", "message": "Notif 1"},
        {"id": "2", "message": "Notif 2"},
    ]

    # Mock dos providers
    def mock_org_id_provider() -> str:
        return "org-test-123"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "current_user@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Buscar notificações
    notifications = service.fetch_latest(limit=10)

    # Verificar que repo foi chamado com exclude_actor_email
    mock_repo.list_notifications.assert_called_once_with(
        "org-test-123", 10, exclude_actor_email="current_user@example.com"
    )

    assert len(notifications) == 2


def test_notifications_service_fetch_unread_count_excludes_own_notifications() -> None:
    """Testa que fetch_unread_count exclui notificações do próprio usuário."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.count_unread.return_value = 5
    # Mocks para hidden (sem ocultas)
    mock_repo.get_user_hidden_before.return_value = None
    mock_repo.list_hidden_notification_ids.return_value = []

    # Mock dos providers
    def mock_org_id_provider() -> str:
        return "org-test-123"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "current_user@example.com"}

    # Criar service
    service = NotificationsService(
        repository=mock_repo,
        org_id_provider=mock_org_id_provider,
        user_provider=mock_user_provider,
    )

    # Contar não lidas
    count = service.fetch_unread_count()

    # Verificar que repo foi chamado com exclude_actor_email
    mock_repo.count_unread.assert_called_once_with("org-test-123", exclude_actor_email="current_user@example.com")

    assert count == 5


# ==================== Testes para hide_notification_for_me ====================


def test_hide_notification_for_me_success() -> None:
    """Testa que hide_notification_for_me chama o repositório corretamente."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    mock_repo.hide_notification_for_user.return_value = True

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    result = service.hide_notification_for_me("notif-abc-123")

    assert result is True
    mock_repo.hide_notification_for_user.assert_called_once_with(
        "org-123",
        "user-123",
        "notif-abc-123",
    )


def test_hide_notification_for_me_no_user() -> None:
    """Testa que hide_notification_for_me retorna False sem usuário."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> None:
        return None

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    result = service.hide_notification_for_me("notif-abc-123")

    assert result is False
    mock_repo.hide_notification_for_user.assert_not_called()


def test_hide_notification_for_me_repo_fails() -> None:
    """Testa que hide_notification_for_me retorna False quando repo falha."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    mock_repo.hide_notification_for_user.return_value = False

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    result = service.hide_notification_for_me("notif-abc-123")

    assert result is False


# ==================== Testes para hide_all_for_me ====================


def test_hide_all_for_me_success() -> None:
    """Testa que hide_all_for_me atualiza hidden_before corretamente."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    mock_repo.set_user_hidden_before.return_value = True
    mock_repo.clear_hidden_ids_for_user.return_value = True

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    result = service.hide_all_for_me()

    assert result is True
    mock_repo.set_user_hidden_before.assert_called_once()
    call_args = mock_repo.set_user_hidden_before.call_args[0]
    # Argumentos posicionais: (org_id, user_id, now_utc)
    assert call_args[0] == "org-123"
    assert call_args[1] == "user-123"
    # Verificar que hidden_before é uma string ISO válida e recente
    hidden_before_str = call_args[2]
    assert isinstance(hidden_before_str, str)
    hidden_before = datetime.fromisoformat(hidden_before_str)
    # Deve estar muito próximo ao momento atual (até 5 segundos de tolerância)
    now = datetime.now(timezone.utc)
    delta = abs((now - hidden_before).total_seconds())
    assert delta < 5


def test_hide_all_for_me_no_user() -> None:
    """Testa que hide_all_for_me retorna False sem usuário."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> None:
        return None

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    result = service.hide_all_for_me()

    assert result is False
    mock_repo.set_user_hidden_before.assert_not_called()


def test_hide_all_for_me_no_org() -> None:
    """Testa que hide_all_for_me retorna False sem org_id."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()

    def org_id_provider() -> None:
        return None

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    result = service.hide_all_for_me()

    assert result is False
    mock_repo.set_user_hidden_before.assert_not_called()


# ==================== Testes para fetch_latest_for_ui com hidden ====================


def test_fetch_latest_for_ui_filters_hidden_notifications() -> None:
    """Testa que fetch_latest_for_ui filtra notificações ocultas pelo usuário."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    # Notificações do repo
    mock_repo.list_notifications.return_value = [
        {"id": "1", "message": "Notif 1", "created_at": "2025-12-25T10:00:00Z"},
        {"id": "2", "message": "Notif 2", "created_at": "2025-12-25T11:00:00Z"},  # hidden by id
        {"id": "3", "message": "Notif 3", "created_at": "2025-12-20T10:00:00Z"},  # hidden by date
        {"id": "4", "message": "Notif 4", "created_at": "2025-12-26T12:00:00Z"},
    ]
    # Hidden individual IDs
    mock_repo.list_hidden_notification_ids.return_value = ["2"]
    # Hidden before timestamp (string ISO)
    mock_repo.get_user_hidden_before.return_value = "2025-12-24T00:00:00+00:00"

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    notifications = service.fetch_latest_for_ui(limit=10)

    # Deve retornar apenas notificações não ocultas:
    # - id="1" (ok: não oculta por id, criada em 25/12)
    # - id="2" (filtrada: oculta por id)
    # - id="3" (filtrada: criada antes de hidden_before=24/12)
    # - id="4" (ok: não oculta, criada em 26/12)
    assert len(notifications) == 2
    ids = [n["id"] for n in notifications]
    assert "1" in ids
    assert "4" in ids
    assert "2" not in ids
    assert "3" not in ids


def test_fetch_unread_count_subtracts_hidden() -> None:
    """Testa que fetch_unread_count subtrai notificações ocultas."""
    from unittest.mock import MagicMock

    from src.core.notifications_service import NotificationsService

    mock_repo = MagicMock()
    # Total de não lidas (include_self=True)
    mock_repo.count_unread.return_value = 10
    # IDs ocultos individualmente
    mock_repo.list_hidden_notification_ids.return_value = ["a", "b"]
    mock_repo.count_unread_by_ids.return_value = 2  # 2 não lidas nos IDs ocultos
    # Hidden before timestamp (string ISO)
    mock_repo.get_user_hidden_before.return_value = "2025-12-24T00:00:00+00:00"
    mock_repo.count_unread_before.return_value = 3  # 3 não lidas antes da data

    def org_id_provider() -> str:
        return "org-123"

    def user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    service = NotificationsService(mock_repo, org_id_provider, user_provider)
    # Usar include_self=True para usar a nova lógica de subtração
    count = service.fetch_unread_count(include_self=True)

    # Total=10, ocultas_por_id=2, ocultas_por_data=3
    # Resultado: max(0, 10 - 2 - 3) = 5
    assert count == 5
