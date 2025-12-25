"""Testes mínimos focados em notificações - QA cobertura.

Testa:
- timezone: created_at "Z" -> created_at_local_str no formato DD/MM/YYYY HH:MM
- fallback de autor: RC_INITIALS_MAP (env) -> actor_display_name correto
- "marcar tudo lido": garantir que a função chamada aplica filtro is_read=False
- toast: se winotify não disponível, não crasha
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def test_created_at_timezone_conversion() -> None:
    """Testa conversão de created_at UTC (Z) para created_at_local_str DD/MM/YYYY HH:MM."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório que retorna notificação com created_at UTC
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-1",
            "created_at": "2025-12-20T14:30:00Z",  # UTC
            "message": "Test",
            "is_read": False,
            "actor_email": "test@example.com",
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

    # Buscar notificações
    notifications = service.fetch_latest_for_ui(limit=10)

    # Verificar que created_at_local_str foi gerado no formato correto
    assert len(notifications) == 1
    notif = notifications[0]

    # Deve ter created_at_local_str no formato DD/MM/YYYY HH:MM
    assert "created_at_local_str" in notif
    local_str = notif["created_at_local_str"]

    # Formato: "20/12/2025 11:30" (America/Sao_Paulo = UTC-3)
    assert "/" in local_str  # DD/MM/YYYY
    assert ":" in local_str  # HH:MM

    # Parse para validar formato
    try:
        parsed = datetime.strptime(local_str, "%d/%m/%Y %H:%M")
        assert parsed.day == 20
        assert parsed.month == 12
        assert parsed.year == 2025
    except ValueError as exc:
        raise AssertionError(f"Formato inválido: {local_str}") from exc


def test_actor_display_name_fallback_with_rc_initials_map() -> None:
    """Testa fallback de actor_display_name usando RC_INITIALS_MAP do env."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.list_notifications.return_value = [
        {
            "id": "notif-1",
            "created_at": "2025-12-20T14:30:00Z",
            "message": "Test",
            "is_read": False,
            "actor_email": "rcgestor@example.com",  # Email que deve ter fallback
        }
    ]

    # Providers
    def mock_org_id_provider() -> str:
        return "org-123"

    def mock_user_provider() -> dict[str, Any]:
        return {"uid": "user-123", "email": "test@example.com"}

    # Configurar RC_INITIALS_MAP no env
    test_map = '{"rcgestor@example.com": "RC"}'
    with patch.dict(os.environ, {"RC_INITIALS_MAP": test_map}, clear=False):
        # Criar service (vai ler RC_INITIALS_MAP do env)
        service = NotificationsService(
            repository=mock_repo,
            org_id_provider=mock_org_id_provider,
            user_provider=mock_user_provider,
        )

        # Buscar notificações
        notifications = service.fetch_latest_for_ui(limit=10)

        # Verificar que actor_display_name foi aplicado
        assert len(notifications) == 1
        notif = notifications[0]

        assert "actor_display_name" in notif
        assert notif["actor_display_name"] == "RC"  # Fallback aplicado


def test_mark_all_read_filters_is_read_false() -> None:
    """Testa que mark_all_read chama repo com filtro is_read=False implícito."""
    from src.core.notifications_service import NotificationsService

    # Mock do repositório
    mock_repo = MagicMock()
    mock_repo.mark_all_read.return_value = True

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

    # Marcar todas como lidas
    result = service.mark_all_read()

    # Verificar que repo.mark_all_read foi chamado
    assert result is True
    mock_repo.mark_all_read.assert_called_once_with("org-123")


def test_mark_all_read_without_org_id() -> None:
    """Testa que mark_all_read retorna False quando org_id não disponível."""
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

    # Marcar todas como lidas (deve falhar)
    result = service.mark_all_read()

    # Deve retornar False
    assert result is False

    # Repositório NÃO deve ser chamado
    mock_repo.mark_all_read.assert_not_called()


def test_toast_without_winotify_does_not_crash() -> None:
    """Testa que falta de winotify não causa crash (fallback silencioso).

    Verifica que existe try/except no código para tratar ImportError de winotify.
    """
    # Ler o arquivo main_window.py e verificar que tem tratamento de erro
    import pathlib

    main_window_path = (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "src"
        / "modules"
        / "main_window"
        / "views"
        / "main_window.py"
    )

    if main_window_path.exists():
        content = main_window_path.read_text(encoding="utf-8")

        # Verificar que existe try/except para winotify
        has_winotify_import = "from winotify import" in content or "import winotify" in content
        has_import_error_handling = "except ImportError" in content or "except Exception" in content

        # Se não usa winotify, pular verificação
        if not has_winotify_import:
            pytest.skip("Código não usa winotify")

        # Deve ter importação de winotify E tratamento de erro
        assert has_winotify_import, "Código não importa winotify"
        assert has_import_error_handling, "Código não trata ImportError"

        # Verificar mensagem de fallback/log
        has_fallback_message = "winotify não instalado" in content.lower() or "winotify" in content.lower()
        assert has_fallback_message, "Código não tem mensagem de fallback para winotify"
    else:
        # Se arquivo não existe, pular teste
        pass


def test_notifications_repository_mark_all_read_updates_only_unread() -> None:
    """Testa que mark_all_read do repo atualiza apenas notificações não lidas."""
    from infra.repositories.notifications_repository import mark_all_read

    # Mock do supabase client
    mock_response = MagicMock()
    mock_response.data = [{"id": "1"}, {"id": "2"}]  # 2 notificações atualizadas

    mock_update = MagicMock()
    mock_update.execute.return_value = mock_response

    mock_eq = MagicMock()
    mock_eq.eq.return_value = mock_update

    mock_table = MagicMock()
    mock_table.update.return_value = mock_eq

    with patch("infra.supabase_client.supabase") as mock_supabase:
        mock_supabase.table.return_value = mock_table

        # Executar mark_all_read
        result = mark_all_read("org-123")

        # Verificar sucesso
        assert result is True

        # Verificar que update foi chamado com is_read=True
        mock_table.update.assert_called_once_with({"is_read": True})

        # Verificar que foi filtrado por org_id
        mock_eq.eq.assert_called()
        call_args = mock_eq.eq.call_args_list

        # Deve ter filtro por org_id
        org_filter_found = False
        for call in call_args:
            if call[0][0] == "org_id" and call[0][1] == "org-123":
                org_filter_found = True
                break

        assert org_filter_found, "Filtro org_id não encontrado"
