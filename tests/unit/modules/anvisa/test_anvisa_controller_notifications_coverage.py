"""Testes para aumentar cobertura do anvisa_controller - branches de notificações.

Foca em cobrir:
- notifications_service = None
- publish retorna True
- publish retorna False
- publish lança Exception

Testa as operações:
- create_request
- set_status
- delete_request
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_repo():
    """Mock do repositório ANVISA."""
    repo = MagicMock()
    repo.create_request.return_value = "req-uuid-123"
    repo.update_request_status.return_value = True
    repo.delete_request.return_value = True
    return repo


@pytest.fixture
def mock_notifications_service_success():
    """Mock do NotificationsService que retorna True."""
    service = MagicMock()
    service.publish.return_value = True
    return service


@pytest.fixture
def mock_notifications_service_false():
    """Mock do NotificationsService que retorna False."""
    service = MagicMock()
    service.publish.return_value = False
    return service


@pytest.fixture
def mock_notifications_service_exception():
    """Mock do NotificationsService que lança exceção."""
    service = MagicMock()
    service.publish.side_effect = RuntimeError("Notification service down")
    return service


# ========== CREATE_REQUEST ==========


def test_create_request_without_notifications_service(mock_repo):
    """Testa create_request quando notifications_service é None."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    # Controller SEM notifications_service
    controller = AnvisaController(repository=mock_repo, logger=logger, notifications_service=None)

    # Executar create
    result = controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="ALTERACAO_RAZAO_SOCIAL",
    )

    # Deve retornar o request_id
    assert result == "req-uuid-123"

    # Repo deve ter sido chamado
    mock_repo.create_request.assert_called_once()


def test_create_request_with_notifications_service_success(mock_repo, mock_notifications_service_success):
    """Testa create_request quando publish retorna True."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar create
    result = controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="ALTERACAO_RAZAO_SOCIAL",
    )

    # Deve retornar o request_id
    assert result == "req-uuid-123"

    # Notifications service deve ter sido chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args[1]
    assert call_kwargs["module"] == "anvisa"
    assert call_kwargs["event"] == "created"
    assert "request_type" in call_kwargs.get("metadata", {})


def test_create_request_with_notifications_service_returns_false(mock_repo, mock_notifications_service_false, caplog):
    """Testa create_request quando publish retorna False.

    Comportamento correto: retorna request_id (repo teve sucesso), falha no publish não afeta.
    """
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para capturar logs com caplog
    logger = logging.getLogger("src.modules.anvisa.controllers.anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_false
    )

    with caplog.at_level(logging.WARNING):
        # Executar create (não deve travar)
        result = controller.create_request(
            org_id="org-123",
            client_id="456",
            request_type="ALTERACAO_RAZAO_SOCIAL",
        )

    # Repo teve sucesso, publish falhou mas não afeta retorno
    assert result == "req-uuid-123"

    # Publish foi chamado (mas retornou False)
    mock_notifications_service_false.publish.assert_called_once()

    # Deve logar warning sobre publish retornar False
    assert any("Publish de criação retornou False" in record.message for record in caplog.records)


def test_create_request_with_notifications_service_exception(mock_repo, mock_notifications_service_exception, caplog):
    """Testa create_request quando publish lança exceção.

    Comportamento correto: retorna request_id (repo teve sucesso), exceção no publish não afeta.
    """
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para capturar logs com caplog
    logger = logging.getLogger("src.modules.anvisa.controllers.anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_exception
    )

    with caplog.at_level(logging.ERROR):
        # Executar create (não deve propagar exceção)
        result = controller.create_request(
            org_id="org-123",
            client_id="456",
            request_type="ALTERACAO_RAZAO_SOCIAL",
        )

    # Repo teve sucesso, exceção no publish não afeta retorno
    assert result == "req-uuid-123"

    # Publish foi chamado (mas levantou exceção)
    mock_notifications_service_exception.publish.assert_called_once()

    # Deve logar exception
    assert any("EXCEPTION ao publicar notificação de criação" in record.message for record in caplog.records)


# ========== SET_STATUS ==========


def test_set_status_without_notifications_service(mock_repo):
    """Testa set_status quando notifications_service é None."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(repository=mock_repo, logger=logger, notifications_service=None)

    # Executar set_status
    result = controller.set_status("req-789", "done")

    # Deve retornar True
    assert result is True

    # Repo deve ter sido chamado
    mock_repo.update_request_status.assert_called_once_with("req-789", "done")


def test_set_status_with_notifications_service_success(mock_repo, mock_notifications_service_success):
    """Testa set_status quando publish retorna True."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status
    result = controller.set_status("req-789", "done")

    # Deve retornar True
    assert result is True

    # Notifications service deve ter sido chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args[1]
    assert call_kwargs["module"] == "anvisa"
    assert call_kwargs["event"] == "status_changed"
    assert call_kwargs["metadata"]["new_status"] == "done"


def test_set_status_with_notifications_service_returns_false(mock_repo, mock_notifications_service_false, caplog):
    """Testa set_status quando publish retorna False.

    Comportamento correto: retorna True (repo teve sucesso), falha no publish não afeta.
    """
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para capturar logs com caplog
    logger = logging.getLogger("src.modules.anvisa.controllers.anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_false
    )

    with caplog.at_level(logging.WARNING):
        # Executar set_status (não deve travar)
        result = controller.set_status("req-789", "done")

    # Repo teve sucesso, publish falhou mas não afeta retorno
    assert result is True

    # Publish foi chamado (mas retornou False)
    mock_notifications_service_false.publish.assert_called_once()

    # Deve logar warning sobre publish retornar False
    assert any("Publish de status retornou False" in record.message for record in caplog.records)


def test_set_status_with_notifications_service_exception(mock_repo, mock_notifications_service_exception, caplog):
    """Testa set_status quando publish lança exceção.

    Comportamento correto: retorna True (repo teve sucesso), exceção no publish não afeta.
    """
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para capturar logs com caplog
    logger = logging.getLogger("src.modules.anvisa.controllers.anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_exception
    )

    with caplog.at_level(logging.ERROR):
        # Executar set_status (não deve propagar exceção)
        result = controller.set_status("req-789", "done")

    # Repo teve sucesso, exceção no publish não afeta retorno
    assert result is True

    # Publish foi chamado (mas levantou exceção)
    mock_notifications_service_exception.publish.assert_called_once()

    # Deve logar exception
    assert any("EXCEPTION ao publicar notificação de status" in record.message for record in caplog.records)


# ========== DELETE_REQUEST ==========


def test_delete_request_without_notifications_service(mock_repo):
    """Testa delete_request quando notifications_service é None."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(repository=mock_repo, logger=logger, notifications_service=None)

    # Executar delete
    result = controller.delete_request("req-xyz")

    # Deve retornar True
    assert result is True

    # Repo deve ter sido chamado
    mock_repo.delete_request.assert_called_once_with("req-xyz")


def test_delete_request_with_notifications_service_success(mock_repo, mock_notifications_service_success):
    """Testa delete_request quando publish retorna True."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar delete
    result = controller.delete_request("req-xyz")

    # Deve retornar True
    assert result is True

    # Notifications service deve ter sido chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args[1]
    assert call_kwargs["module"] == "anvisa"
    assert call_kwargs["event"] == "deleted"


def test_delete_request_with_notifications_service_returns_false(mock_repo, mock_notifications_service_false, caplog):
    """Testa delete_request quando publish retorna False.

    Comportamento correto: retorna True (repo teve sucesso), falha no publish não afeta.
    """
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para capturar logs com caplog
    logger = logging.getLogger("src.modules.anvisa.controllers.anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_false
    )

    with caplog.at_level(logging.WARNING):
        # Executar delete (não deve travar)
        result = controller.delete_request("req-xyz")

    # Repo teve sucesso, publish falhou mas não afeta retorno
    assert result is True

    # Publish foi chamado (mas retornou False)
    mock_notifications_service_false.publish.assert_called_once()

    # Deve logar warning sobre publish retornar False
    assert any("Publish de exclusão retornou False" in record.message for record in caplog.records)


def test_delete_request_with_notifications_service_exception(mock_repo, mock_notifications_service_exception, caplog):
    """Testa delete_request quando publish lança exceção.

    Comportamento correto: retorna True (repo teve sucesso), exceção no publish não afeta.
    """
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para capturar logs com caplog
    logger = logging.getLogger("src.modules.anvisa.controllers.anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_exception
    )

    with caplog.at_level(logging.ERROR):
        # Executar delete (não deve propagar exceção)
        result = controller.delete_request("req-xyz")

    # Repo teve sucesso, exceção no publish não afeta retorno
    assert result is True

    # Publish foi chamado (mas levantou exceção)
    mock_notifications_service_exception.publish.assert_called_once()

    # Deve logar exception
    assert any("EXCEPTION ao publicar notificação de exclusão" in record.message for record in caplog.records)


# ========== EDGE CASES ==========


def test_create_request_repo_returns_none(mock_repo, mock_notifications_service_success):
    """Testa create_request quando repo retorna None (falha)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Mock repo retornando None
    mock_repo.create_request.return_value = None

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar create
    result = controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="ALTERACAO_RAZAO_SOCIAL",
    )

    # Deve retornar None
    assert result is None

    # Notifications service NÃO deve ser chamado (falhou antes)
    mock_notifications_service_success.publish.assert_not_called()


def test_set_status_repo_returns_false(mock_repo, mock_notifications_service_success):
    """Testa set_status quando repo retorna False (falha)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Mock repo retornando False
    mock_repo.update_request_status.return_value = False

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status
    result = controller.set_status("req-789", "done")

    # Deve retornar False
    assert result is False

    # Notifications service NÃO deve ser chamado (falhou antes)
    mock_notifications_service_success.publish.assert_not_called()


def test_delete_request_repo_returns_false(mock_repo, mock_notifications_service_success):
    """Testa delete_request quando repo retorna False (falha)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Mock repo retornando False
    mock_repo.delete_request.return_value = False

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar delete
    result = controller.delete_request("req-xyz")

    # Deve retornar False
    assert result is False

    # Notifications service NÃO deve ser chamado (falhou antes)
    mock_notifications_service_success.publish.assert_not_called()
