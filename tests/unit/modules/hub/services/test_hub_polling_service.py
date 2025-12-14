# -*- coding: utf-8 -*-
"""Testes para HubPollingService.

MF-14: Testes unitários do serviço de polling extraído.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.modules.hub.services.hub_polling_service import HubPollingService
from src.modules.hub.state import HubState


class MockHubScreen:
    """Mock do HubScreen para testes do polling service."""

    def __init__(self):
        self.state = HubState()
        self._lifecycle = Mock()
        self._hub_controller = Mock()
        self._polling_service: HubPollingService | None = None

    def refresh_notes_async(self, *, force: bool = False) -> None:
        """Mock de refresh_notes_async."""
        pass


@pytest.fixture
def mock_hub():
    """Cria mock do HubScreen."""
    return MockHubScreen()


@pytest.fixture
def polling_service(mock_hub):
    """Cria serviço de polling com mock."""
    service = HubPollingService(callbacks=mock_hub)
    mock_hub._polling_service = service
    return service


def test_start_notes_polling_marks_active(polling_service, mock_hub):
    """Teste: start_notes_polling marca polling_active como True."""
    # Arrange
    assert mock_hub.state.polling_active is False

    # Act
    polling_service.start_notes_polling()

    # Assert
    assert mock_hub.state.polling_active is True


def test_start_notes_polling_schedules_timers(polling_service, mock_hub):
    """Teste: start_notes_polling agenda timers de authors e notes."""
    # Act
    polling_service.start_notes_polling()

    # Assert
    mock_hub._lifecycle.schedule_authors_refresh.assert_called_once()
    mock_hub._lifecycle.schedule_notes_poll.assert_called_once()


def test_start_notes_polling_skip_if_active(polling_service, mock_hub):
    """Teste: start_notes_polling não reagenda se já ativo (sem force)."""
    # Arrange
    mock_hub.state.polling_active = True

    # Act
    polling_service.start_notes_polling(force=False)

    # Assert
    mock_hub._lifecycle.schedule_authors_refresh.assert_not_called()


def test_start_notes_polling_force_overrides_active(polling_service, mock_hub):
    """Teste: start_notes_polling com force=True agenda mesmo se ativo."""
    # Arrange
    mock_hub.state.polling_active = True

    # Act
    polling_service.start_notes_polling(force=True)

    # Assert
    mock_hub._lifecycle.schedule_authors_refresh.assert_called_once()
    mock_hub._lifecycle.schedule_notes_poll.assert_called_once()


def test_refresh_authors_cache_delegates_to_controller(polling_service, mock_hub):
    """Teste: refresh_authors_cache delega para controller."""
    # Act
    polling_service.refresh_authors_cache(force=True)

    # Assert
    mock_hub._hub_controller.refresh_author_names_cache_async.assert_called_once_with(force=True)


def test_poll_notes_delegates_to_controller(polling_service, mock_hub):
    """Teste: poll_notes delega para controller."""
    # Act
    polling_service.poll_notes(force=False)

    # Assert
    mock_hub._hub_controller.refresh_notes.assert_called_once_with(force=False)


def test_schedule_next_poll_delegates_to_lifecycle(polling_service, mock_hub):
    """Teste: schedule_next_poll delega para lifecycle."""
    # Act
    polling_service.schedule_next_poll(delay_ms=5000)

    # Assert
    mock_hub._lifecycle.schedule_notes_poll.assert_called_once_with(delay_ms=5000)


def test_stop_polling_marks_inactive(polling_service, mock_hub):
    """Teste: stop_polling marca polling_active como False."""
    # Arrange
    mock_hub.state.polling_active = True

    # Act
    polling_service.stop_polling()

    # Assert
    assert mock_hub.state.polling_active is False


def test_refresh_authors_cache_handles_exception(polling_service, mock_hub, caplog):
    """Teste: refresh_authors_cache não falha se controller lançar exceção."""
    # Arrange
    mock_hub._hub_controller.refresh_author_names_cache_async.side_effect = Exception("Test error")

    # Act & Assert (não deve lançar exceção)
    polling_service.refresh_authors_cache(force=True)

    # Verificar que erro foi logado
    assert "Erro ao refresh cache de autores" in caplog.text


def test_poll_notes_handles_exception(polling_service, mock_hub, caplog):
    """Teste: poll_notes não falha se controller lançar exceção."""
    # Arrange
    mock_hub._hub_controller.refresh_notes.side_effect = Exception("Test error")

    # Act & Assert (não deve lançar exceção)
    polling_service.poll_notes(force=False)

    # Verificar que erro foi logado
    assert "Erro no polling de notas" in caplog.text


def test_schedule_next_poll_handles_exception(polling_service, mock_hub, caplog):
    """Teste: schedule_next_poll não falha se lifecycle lançar exceção."""
    # Arrange
    mock_hub._lifecycle.schedule_notes_poll.side_effect = Exception("Test error")

    # Act & Assert (não deve lançar exceção)
    polling_service.schedule_next_poll(delay_ms=5000)

    # Verificar que erro foi logado
    assert "Erro ao agendar polling" in caplog.text
