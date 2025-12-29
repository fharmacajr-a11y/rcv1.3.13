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
    # Verifica formato padronizado: "ANVISA • Nova demanda criada: <TIPO> (Cliente <ID>)"
    assert call_kwargs["message"] == "ANVISA • Nova demanda criada: ALTERACAO_RAZAO_SOCIAL (Cliente 456)"
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

    # Executar set_status com finalização (done/CONCLUIDA)
    result = controller.set_status(
        "req-789",
        "done",
        client_id="123",
        request_type="Alteração de Porte",
    )

    # Deve retornar True
    assert result is True

    # Notifications service deve ter sido chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args[1]
    assert call_kwargs["module"] == "anvisa"
    assert call_kwargs["event"] == "status_changed"
    # Verifica formato padronizado: "ANVISA • Demanda finalizada: <TIPO> (Cliente <ID>)"
    assert call_kwargs["message"] == "ANVISA • Demanda finalizada: Alteração de Porte (Cliente 123)"
    assert call_kwargs["metadata"]["new_status"] == "done"


def test_set_status_canceled_message_format(mock_repo, mock_notifications_service_success):
    """Testa set_status com status 'canceled' - verifica mensagem correta."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Criar logger real para o controller
    logger = logging.getLogger("test_anvisa_controller")

    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status com cancelamento
    result = controller.set_status(
        "req-789",
        "canceled",
        client_id="999",
        request_type="Inclusão de Atividade",
    )

    # Deve retornar True
    assert result is True

    # Notifications service deve ter sido chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args[1]
    # Verifica formato padronizado: "ANVISA • Demanda cancelada: <TIPO> (Cliente <ID>)"
    assert call_kwargs["message"] == "ANVISA • Demanda cancelada: Inclusão de Atividade (Cliente 999)"


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

    # Executar delete com client_id e request_type
    result = controller.delete_request(
        "req-xyz",
        client_id="123",
        request_type="Alteração de Porte",
    )

    # Deve retornar True
    assert result is True

    # Notifications service deve ter sido chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args[1]
    assert call_kwargs["module"] == "anvisa"
    assert call_kwargs["event"] == "deleted"
    # Verifica formato padronizado: "ANVISA • Demanda excluída: <TIPO> (Cliente <ID>)"
    assert call_kwargs["message"] == "ANVISA • Demanda excluída: Alteração de Porte (Cliente 123)"


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


# ========== MF46: Exception handling coverage (lines 179-181, 241-249) ==========


def test_delete_request_publish_exception_does_not_break_operation(mock_repo):
    """Testa que exceção no publish não quebra o delete_request (linhas 179-181)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Mock notifications_service que lança exceção
    mock_notif = MagicMock()
    mock_notif.publish.side_effect = RuntimeError("Notification service crashed")

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(repository=mock_repo, logger=logger, notifications_service=mock_notif)

    # Executar delete - deve retornar True mesmo com exceção no publish
    result = controller.delete_request("req-123", client_id="456", request_type="AFE")

    # A operação deve ter sucesso (repo retornou True)
    assert result is True

    # Repo deve ter sido chamado
    mock_repo.delete_request.assert_called_once_with("req-123")

    # Publish foi chamado (e falhou)
    mock_notif.publish.assert_called_once()


def test_set_status_in_progress_uses_status_other_message(mock_repo, mock_notifications_service_success):
    """Testa set_status com 'in_progress' usa mensagem status_other (linhas 241-249)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status com status que não é done/canceled
    result = controller.set_status("req-123", "in_progress", client_id="456", request_type="AFE")

    assert result is True

    # Verificar que publish foi chamado com mensagem formatada corretamente
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    assert "em andamento" in call_kwargs["message"]
    assert "AFE" in call_kwargs["message"]
    assert "456" in call_kwargs["message"]


def test_set_status_submitted_uses_status_other_message(mock_repo, mock_notifications_service_success):
    """Testa set_status com 'submitted' usa mensagem status_other (linhas 241-249)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status com status 'submitted'
    result = controller.set_status("req-123", "submitted", request_type="CBPF")

    assert result is True

    # Verificar que publish foi chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    assert "submetida" in call_kwargs["message"]
    assert "CBPF" in call_kwargs["message"]


def test_set_status_unknown_status_uses_status_text_directly(mock_repo, mock_notifications_service_success):
    """Testa set_status com status desconhecido usa o próprio status como texto."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status com status desconhecido
    result = controller.set_status("req-123", "custom_status", client_id="789")

    assert result is True

    # Verificar que publish foi chamado
    mock_notifications_service_success.publish.assert_called_once()
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    # Status desconhecido deve aparecer no texto
    assert "custom_status" in call_kwargs["message"]
    assert "789" in call_kwargs["message"]


def test_set_status_only_client_id_formats_correctly(mock_repo, mock_notifications_service_success):
    """Testa set_status com apenas client_id (sem request_type) formata corretamente."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status apenas com client_id
    result = controller.set_status("req-123", "in_progress", client_id="456")

    assert result is True

    # Verificar formatação
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    assert "456" in call_kwargs["message"]
    assert "(Cliente 456)" in call_kwargs["message"]


def test_set_status_no_client_no_type_formats_minimal(mock_repo, mock_notifications_service_success):
    """Testa set_status sem client_id nem request_type formata mensagem mínima."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status sem extras
    result = controller.set_status("req-123", "in_progress")

    assert result is True

    # Verificar formatação mínima
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    assert "ANVISA" in call_kwargs["message"]
    assert "em andamento" in call_kwargs["message"]


def test_set_status_only_request_type_formats_correctly_mf46(mock_repo, mock_notifications_service_success):
    """Testa set_status com apenas request_type (sem client_id) formata corretamente (linha 119)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status apenas com request_type (sem client_id)
    result = controller.set_status("req-123", "done", request_type="AFE")

    assert result is True

    # Verificar formatação: "ANVISA • Demanda finalizada: AFE"
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    assert "AFE" in call_kwargs["message"]
    # Não deve ter "(Cliente ...)" porque não passou client_id
    assert "(Cliente" not in call_kwargs["message"]


# ========== MF47: Branch L121 - client_id sem request_type ==========


def test_set_status_only_client_id_formats_correctly_mf47(mock_repo, mock_notifications_service_success):
    """Testa set_status com apenas client_id (sem request_type) formata corretamente (linha 121)."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_controller")
    controller = AnvisaController(
        repository=mock_repo, logger=logger, notifications_service=mock_notifications_service_success
    )

    # Executar set_status apenas com client_id (sem request_type)
    result = controller.set_status("req-123", "done", client_id="789")

    assert result is True

    # Verificar formatação: "ANVISA • Demanda finalizada (Cliente 789)"
    call_kwargs = mock_notifications_service_success.publish.call_args.kwargs
    assert "(Cliente 789)" in call_kwargs["message"]
    # Não deve ter tipo da demanda porque não passou request_type
    assert ": " not in call_kwargs["message"] or ":" not in call_kwargs["message"].split("(Cliente")[0]
