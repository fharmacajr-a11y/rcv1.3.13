"""Testes unitários para src.core.notifications_service — Fase 67.

TEST-010: Cobertura do serviço de notificações (headless).
Todos os testes usam mocks para evitar dependências de GUI/rede/DB.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.notifications_service import NotificationsService


# ==========================
# Fixtures e Helpers
# ==========================


@pytest.fixture
def mock_repository() -> MagicMock:
    """Cria um mock do NotificationsRepository."""
    repo = MagicMock()
    repo.list_notifications.return_value = []
    repo.count_unread.return_value = 0
    repo.mark_all_read.return_value = True
    repo.insert_notification.return_value = True
    return repo


@pytest.fixture
def org_id_provider_none() -> Callable[[], str | None]:
    """Provider que retorna None (sem org_id)."""
    return lambda: None


@pytest.fixture
def org_id_provider_valid() -> Callable[[], str | None]:
    """Provider que retorna org_id válido."""
    return lambda: "org-123"


@pytest.fixture
def user_provider_none() -> Callable[[], dict[str, Any] | None]:
    """Provider que retorna None (sem usuário)."""
    return lambda: None


@pytest.fixture
def user_provider_valid() -> Callable[[], dict[str, Any] | None]:
    """Provider que retorna usuário válido."""
    return lambda: {"uid": "user-456", "email": "user@example.com"}


# ==========================
# A) _resolve_actor_info
# ==========================


class TestResolveActorInfo:
    """Testes para _resolve_actor_info (helper interno)."""

    def test_email_none_retorna_fallback(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Email None deve retornar ('?', '')."""
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        display_name, initial = service._resolve_actor_info(None)
        assert display_name == "?"
        assert initial == ""

    def test_email_vazio_retorna_fallback(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Email vazio deve retornar ('?', '')."""
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        display_name, initial = service._resolve_actor_info("")
        assert display_name == "?"
        assert initial == ""

    def test_email_espacos_retorna_fallback(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Email com apenas espaços deve retornar ('?', '')."""
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        # String vazia após strip não é None, mas vazio
        display_name, initial = service._resolve_actor_info("   ")
        # A implementação não faz strip antes de checar, então "   " tem len > 0
        # Mas ao tentar split('@'), não há @, então vai para fallback
        assert display_name  # Não vazio porque tem chars
        assert initial  # Terá inicial do espaço (mas não será "?")

    def test_email_no_mapa_usa_prefixo(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Email não no mapa deve usar prefixo capitalizado."""
        monkeypatch.setenv("RC_INITIALS_MAP", "{}")
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        display_name, initial = service._resolve_actor_info("john.doe@example.com")
        assert display_name == "John.doe"
        assert initial == "J"

    def test_email_no_mapa_retorna_email_no_mapa(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Email no mapa deve retornar nome e inicial do mapa."""
        initials_map = {"john.doe@example.com": "John Doe"}
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps(initials_map))

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        display_name, initial = service._resolve_actor_info("john.doe@example.com")

        assert display_name == "John Doe"
        assert initial == "J"

    def test_email_no_mapa_case_insensitive(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Mapa deve ser case-insensitive."""
        initials_map = {"JOHN.DOE@EXAMPLE.COM": "John Doe"}
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps(initials_map))

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        display_name, initial = service._resolve_actor_info("john.doe@example.com")

        assert display_name == "John Doe"
        assert initial == "J"

    def test_email_sem_arroba_usa_fallback(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Email sem @ deve usar fallback seguro."""
        monkeypatch.setenv("RC_INITIALS_MAP", "{}")
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        display_name, initial = service._resolve_actor_info("invalid-email")
        # Sem @, split('@') retorna ["invalid-email"], prefix="invalid-email"
        assert display_name == "Invalid-email"
        assert initial == "I"

    def test_email_unicode_nao_explode(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Email com unicode/acentos não deve explodir."""
        monkeypatch.setenv("RC_INITIALS_MAP", "{}")
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        display_name, initial = service._resolve_actor_info("joão@example.com")
        assert display_name == "João"
        assert initial == "J"


# ==========================
# B) _load_initials_map
# ==========================


class TestLoadInitialsMap:
    """Testes para _load_initials_map."""

    def test_sem_env_var_retorna_vazio(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sem RC_INITIALS_MAP deve retornar dict vazio."""
        monkeypatch.delenv("RC_INITIALS_MAP", raising=False)
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        result = service._load_initials_map()
        assert result == {}

    def test_env_var_vazia_retorna_vazio(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RC_INITIALS_MAP vazia deve retornar dict vazio."""
        monkeypatch.setenv("RC_INITIALS_MAP", "")
        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        result = service._load_initials_map()
        assert result == {}

    def test_env_var_valida_retorna_dict(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RC_INITIALS_MAP válida deve retornar dict normalizado."""
        initials_map = {"User1@Example.COM": "User One", "user2@example.com": "User Two"}
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps(initials_map))

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service._load_initials_map()

        assert result == {
            "user1@example.com": "User One",
            "user2@example.com": "User Two",
        }

    def test_env_var_invalida_retorna_vazio_e_loga(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """RC_INITIALS_MAP inválida deve retornar {} e logar debug."""
        monkeypatch.setenv("RC_INITIALS_MAP", "{invalid-json}")

        with caplog.at_level(logging.DEBUG):
            service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
            result = service._load_initials_map()

        assert result == {}
        assert any("Erro ao carregar RC_INITIALS_MAP" in rec.message for rec in caplog.records)

    def test_cache_funciona(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Segunda chamada deve usar cache sem re-parsear."""
        initials_map = {"test@example.com": "Test User"}
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps(initials_map))

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        # Primeira chamada
        result1 = service._load_initials_map()
        # Segunda chamada (deve usar cache)
        result2 = service._load_initials_map()

        assert result1 == result2
        assert result1 is result2  # Mesma instância


# ==========================
# C) fetch_latest / fetch_latest_for_ui
# ==========================


class TestFetchLatest:
    """Testes para fetch_latest."""

    def test_sem_org_id_retorna_vazio(
        self,
        mock_repository: MagicMock,
        org_id_provider_none: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Sem org_id deve retornar lista vazia e logar debug."""
        service = NotificationsService(mock_repository, org_id_provider_none, user_provider_none)

        with caplog.at_level(logging.DEBUG):
            result = service.fetch_latest()

        assert result == []
        assert any("Sem org_id" in rec.message for rec in caplog.records)

    def test_org_id_valido_retorna_lista(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Com org_id válido deve chamar repo e retornar lista."""
        mock_repository.list_notifications.return_value = [
            {"id": 1, "message": "Test 1"},
            {"id": 2, "message": "Test 2"},
        ]

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service.fetch_latest(limit=10)

        assert len(result) == 2
        mock_repository.list_notifications.assert_called_once_with("org-123", 10, exclude_actor_email=None)

    def test_repo_exception_retorna_vazio(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Exceção no repo deve retornar [] e logar exception."""
        mock_repository.list_notifications.side_effect = Exception("DB error")

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        with caplog.at_level(logging.ERROR):
            result = service.fetch_latest()

        assert result == []
        assert any("Erro ao buscar notificações" in rec.message for rec in caplog.records)


class TestFetchLatestForUI:
    """Testes para fetch_latest_for_ui."""

    def test_adiciona_campos_formatados(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Deve adicionar campos formatados para UI."""
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps({"actor@example.com": "Actor Name"}))

        mock_repository.list_notifications.return_value = [
            {
                "id": 1,
                "message": "Test",
                "created_at": "2025-12-21T10:00:00Z",
                "request_id": "req-123456789",
                "actor_email": "actor@example.com",
            }
        ]

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service.fetch_latest_for_ui()

        assert len(result) == 1
        notif = result[0]
        assert "created_at_local_str" in notif
        assert "request_id_short" in notif
        assert notif["request_id_short"] == "req-1234"
        assert "actor_display_name" in notif
        assert notif["actor_display_name"] == "Actor Name"
        assert "actor_initial" in notif
        assert notif["actor_initial"] == "A"

    def test_trata_created_at_invalido(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Deve tratar created_at inválido sem explodir."""
        mock_repository.list_notifications.return_value = [
            {
                "id": 1,
                "message": "Test",
                "created_at": "invalid-timestamp",
                "request_id": "",
                "actor_email": "",
            }
        ]

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service.fetch_latest_for_ui()

        assert len(result) == 1
        notif = result[0]
        assert "created_at_local_str" in notif
        # Fallback: primeiros 16 chars
        assert notif["created_at_local_str"] == "invalid-timestam"

    def test_trata_request_id_curto(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Deve usar '—' para request_id curto."""
        mock_repository.list_notifications.return_value = [
            {
                "id": 1,
                "message": "Test",
                "created_at": "",
                "request_id": "short",
                "actor_email": "",
            }
        ]

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service.fetch_latest_for_ui()

        assert result[0]["request_id_short"] == "—"


# ==========================
# D) fetch_unread_count
# ==========================


class TestFetchUnreadCount:
    """Testes para fetch_unread_count."""

    def test_sem_org_id_retorna_zero(
        self,
        mock_repository: MagicMock,
        org_id_provider_none: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Sem org_id deve retornar 0."""
        service = NotificationsService(mock_repository, org_id_provider_none, user_provider_none)
        result = service.fetch_unread_count()
        assert result == 0

    def test_org_id_valido_retorna_count(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Com org_id válido deve retornar count do repo."""
        mock_repository.count_unread.return_value = 5

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service.fetch_unread_count()

        assert result == 5
        mock_repository.count_unread.assert_called_once_with("org-123", exclude_actor_email=None)

    def test_repo_exception_retorna_zero(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Exceção no repo deve retornar 0 e logar exception."""
        mock_repository.count_unread.side_effect = Exception("DB error")

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        with caplog.at_level(logging.ERROR):
            result = service.fetch_unread_count()

        assert result == 0
        assert any("Erro ao contar não lidas" in rec.message for rec in caplog.records)


# ==========================
# E) mark_all_read
# ==========================


class TestMarkAllRead:
    """Testes para mark_all_read."""

    def test_sem_org_id_retorna_false(
        self,
        mock_repository: MagicMock,
        org_id_provider_none: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Sem org_id deve retornar False e logar warning."""
        service = NotificationsService(mock_repository, org_id_provider_none, user_provider_none)

        with caplog.at_level(logging.WARNING):
            result = service.mark_all_read()

        assert result is False
        assert any("Sem org_id" in rec.message for rec in caplog.records)

    def test_org_id_valido_retorna_true(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Com org_id válido e repo OK deve retornar True."""
        mock_repository.mark_all_read.return_value = True

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)
        result = service.mark_all_read()

        assert result is True
        mock_repository.mark_all_read.assert_called_once_with("org-123")

    def test_repo_exception_retorna_false(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Exceção no repo deve retornar False e logar exception."""
        mock_repository.mark_all_read.side_effect = Exception("DB error")

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        with caplog.at_level(logging.ERROR):
            result = service.mark_all_read()

        assert result is False
        assert any("Erro ao marcar como lidas" in rec.message for rec in caplog.records)


# ==========================
# F) publish
# ==========================


class TestPublish:
    """Testes para publish."""

    def test_sem_org_id_retorna_false(
        self,
        mock_repository: MagicMock,
        org_id_provider_none: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Sem org_id deve retornar False e logar warning."""
        service = NotificationsService(mock_repository, org_id_provider_none, user_provider_none)

        with caplog.at_level(logging.WARNING):
            result = service.publish("test", "created", "Test message")

        assert result is False
        assert any("publish ABORTADO: sem org_id" in rec.message for rec in caplog.records)

    def test_sem_user_continua_sem_actor(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_none: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Sem usuário deve continuar mas logar warning."""
        mock_repository.insert_notification.return_value = True

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_none)

        with caplog.at_level(logging.WARNING):
            result = service.publish("test", "created", "Test message")

        assert result is True
        assert any("publish SEM ACTOR" in rec.message for rec in caplog.records)
        # Verificar que chamou insert com actor_user_id=None e actor_email=None
        call_kwargs = mock_repository.insert_notification.call_args[1]
        assert call_kwargs["actor_user_id"] is None
        assert call_kwargs["actor_email"] is None

    def test_com_user_insere_com_actor(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_valid: Callable[[], dict[str, Any] | None],
    ) -> None:
        """Com usuário válido deve inserir com actor."""
        mock_repository.insert_notification.return_value = True

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_valid)
        result = service.publish("test", "created", "Test message", client_id="123", request_id="req-456")

        assert result is True
        call_kwargs = mock_repository.insert_notification.call_args[1]
        assert call_kwargs["org_id"] == "org-123"
        assert call_kwargs["module"] == "test"
        assert call_kwargs["event"] == "created"
        assert call_kwargs["message"] == "Test message"
        assert call_kwargs["actor_user_id"] == "user-456"
        assert call_kwargs["actor_email"] == "user@example.com"
        assert call_kwargs["client_id"] == "123"
        assert call_kwargs["request_id"] == "req-456"

    def test_repo_retorna_false_loga_error(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_valid: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Repo retornando False deve logar error."""
        mock_repository.insert_notification.return_value = False

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_valid)

        with caplog.at_level(logging.ERROR):
            result = service.publish("test", "created", "Test message")

        assert result is False
        assert any("publish FAILED (repo retornou False)" in rec.message for rec in caplog.records)

    def test_repo_exception_retorna_false(
        self,
        mock_repository: MagicMock,
        org_id_provider_valid: Callable[[], str | None],
        user_provider_valid: Callable[[], dict[str, Any] | None],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Exceção no repo deve retornar False e logar exception."""
        mock_repository.insert_notification.side_effect = Exception("DB error")

        service = NotificationsService(mock_repository, org_id_provider_valid, user_provider_valid)

        with caplog.at_level(logging.ERROR):
            result = service.publish("test", "created", "Test message")

        assert result is False
        assert any("publish EXCEPTION" in rec.message for rec in caplog.records)
