# -*- coding: utf-8 -*-
"""Testes para HubLifecycleImpl (MF-15).

Valida extração de lógica de lifecycle (live sync + timers home) de HubScreen
para um service dedicado, verificando:
- start_live_sync() chama controller.setup_realtime()
- stop_live_sync() chama controller.stop_realtime()
- start_home_timers_safely() verifica auth, reseta cache, inicia polling
- Tratamento de exceções em todos os métodos
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from src.modules.hub.services.hub_lifecycle_impl import HubLifecycleImpl
from src.modules.hub.state import HubState

if TYPE_CHECKING:
    pass


# ============================================================================
# MOCK HubScreen (implementa protocolo HubLifecycleCallbacks)
# ============================================================================


class MockHubScreen:
    """Mock de HubScreen que implementa HubLifecycleCallbacks."""

    def __init__(self):
        """Inicializa mock com controller, polling service e state."""
        self.state = HubState()
        self._hub_controller = MagicMock()
        self._polling_service = MagicMock()
        self._auth_service = MagicMock()

        # Configurar mock padrão para _get_user_id_safe
        self._auth_service.get_user_id.return_value = "test-user-123"

        # Estado de autenticação (simulado)
        self._is_auth_ready = False

    def _auth_ready(self) -> bool:
        """Simula verificação de auth."""
        return self._is_auth_ready

    def _get_org_id_safe(self) -> str | None:
        """Mock de _get_org_id_safe."""
        return "test-org-123" if self._is_auth_ready else None

    def _get_email_safe(self) -> str | None:
        """Mock de _get_email_safe."""
        return "user@test.com" if self._is_auth_ready else None

    def _get_user_id_safe(self) -> str | None:
        """Mock de _get_user_id_safe."""
        try:
            return self._auth_service.get_user_id()
        except Exception:
            return None

    def _update_notes_ui_state(self) -> None:
        """Mock de _update_notes_ui_state."""
        pass


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_hub_screen() -> MockHubScreen:
    """Cria MockHubScreen para testes."""
    return MockHubScreen()


@pytest.fixture
def hub_lifecycle_impl(mock_hub_screen: MockHubScreen) -> HubLifecycleImpl:
    """Cria HubLifecycleImpl com mock de callbacks."""
    return HubLifecycleImpl(callbacks=mock_hub_screen)


# ============================================================================
# TESTES: start_live_sync
# ============================================================================


def test_start_live_sync_calls_controller_setup_realtime(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_live_sync() deve chamar controller.setup_realtime()."""
    # Arrange
    mock_controller = mock_hub_screen._hub_controller
    mock_controller.setup_realtime = MagicMock()

    # Act
    hub_lifecycle_impl.start_live_sync()

    # Assert
    mock_controller.setup_realtime.assert_called_once()


def test_start_live_sync_handles_exception_gracefully(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_live_sync() deve tratar exceções sem propagar."""
    # Arrange
    mock_controller = mock_hub_screen._hub_controller
    mock_controller.setup_realtime = MagicMock(side_effect=RuntimeError("Teste"))

    # Act & Assert (não deve propagar exceção)
    hub_lifecycle_impl.start_live_sync()


# ============================================================================
# TESTES: stop_live_sync
# ============================================================================


def test_stop_live_sync_calls_controller_stop_realtime(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """stop_live_sync() deve chamar controller.stop_realtime()."""
    # Arrange
    mock_controller = mock_hub_screen._hub_controller
    mock_controller.stop_realtime = MagicMock()

    # Act
    hub_lifecycle_impl.stop_live_sync()

    # Assert
    mock_controller.stop_realtime.assert_called_once()


def test_stop_live_sync_handles_exception_gracefully(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """stop_live_sync() deve tratar exceções sem propagar."""
    # Arrange
    mock_controller = mock_hub_screen._hub_controller
    mock_controller.stop_realtime = MagicMock(side_effect=RuntimeError("Teste"))

    # Act & Assert (não deve propagar exceção)
    hub_lifecycle_impl.stop_live_sync()


# ============================================================================
# TESTES: start_home_timers_safely
# ============================================================================


def test_start_home_timers_safely_returns_false_when_auth_not_ready(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_home_timers_safely() deve retornar False quando auth não está pronta."""
    # Arrange
    mock_hub_screen._is_auth_ready = False

    # Act
    result = hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    assert result is False
    mock_hub_screen._polling_service.start_notes_polling.assert_not_called()


def test_start_home_timers_safely_returns_true_when_auth_ready(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_home_timers_safely() deve retornar True quando auth está pronta."""
    # Arrange
    mock_hub_screen._is_auth_ready = True

    # Act
    result = hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    assert result is True


def test_start_home_timers_safely_resets_cache_when_auth_ready(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_home_timers_safely() deve resetar cache quando auth está pronta."""
    # Arrange
    mock_hub_screen._is_auth_ready = True
    state = mock_hub_screen.state
    state.names_cache_loaded = True
    state.author_cache = {"test": "data"}
    state.email_prefix_map = {"test": "data"}

    # Act
    hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    assert state.names_cache_loaded is False
    assert state.author_cache == {}
    assert state.email_prefix_map == {}


def test_start_home_timers_safely_calls_update_notes_ui_state(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_home_timers_safely() deve chamar _update_notes_ui_state()."""
    # Arrange
    mock_hub_screen._is_auth_ready = True
    mock_hub_screen._update_notes_ui_state = MagicMock()

    # Act
    hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    mock_hub_screen._update_notes_ui_state.assert_called_once()


def test_start_home_timers_safely_starts_polling(hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen):
    """start_home_timers_safely() deve iniciar polling via service."""
    # Arrange
    mock_hub_screen._is_auth_ready = True
    mock_polling = mock_hub_screen._polling_service
    mock_polling.start_notes_polling = MagicMock()

    # Act
    hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    mock_polling.start_notes_polling.assert_called_once()


def test_start_home_timers_safely_handles_exception_in_polling_start(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_home_timers_safely() deve retornar False se falhar ao iniciar polling."""
    # Arrange
    mock_hub_screen._is_auth_ready = True
    mock_polling = mock_hub_screen._polling_service
    mock_polling.start_notes_polling = MagicMock(side_effect=RuntimeError("Teste"))

    # Act
    result = hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    # Deve retornar False quando há exceção (capturada no except geral)
    assert result is False


def test_start_home_timers_safely_handles_exception_in_update_ui(
    hub_lifecycle_impl: HubLifecycleImpl, mock_hub_screen: MockHubScreen
):
    """start_home_timers_safely() deve retornar False se falhar ao atualizar UI."""
    # Arrange
    mock_hub_screen._is_auth_ready = True
    mock_hub_screen._update_notes_ui_state = MagicMock(side_effect=RuntimeError("Teste"))

    # Act
    result = hub_lifecycle_impl.start_home_timers_safely()

    # Assert
    # Deve retornar False quando há exceção (capturada no except geral)
    assert result is False


# ============================================================================
# TESTES: Protocolo HubLifecycleCallbacks
# ============================================================================


def test_mock_hub_screen_implements_hub_lifecycle_callbacks_protocol(mock_hub_screen: MockHubScreen):
    """MockHubScreen deve implementar protocolo HubLifecycleCallbacks."""
    # Verificar que MockHubScreen tem todos os atributos/métodos do protocolo
    assert hasattr(mock_hub_screen, "state")
    assert hasattr(mock_hub_screen, "_hub_controller")
    assert hasattr(mock_hub_screen, "_polling_service")
    assert hasattr(mock_hub_screen, "_auth_ready")
    assert hasattr(mock_hub_screen, "_get_org_id_safe")
    assert hasattr(mock_hub_screen, "_get_email_safe")
    assert hasattr(mock_hub_screen, "_get_user_id_safe")
    assert hasattr(mock_hub_screen, "_update_notes_ui_state")

    # Verificar que são callables (quando aplicável)
    assert callable(mock_hub_screen._auth_ready)
    assert callable(mock_hub_screen._get_org_id_safe)
    assert callable(mock_hub_screen._get_email_safe)
    assert callable(mock_hub_screen._get_user_id_safe)
    assert callable(mock_hub_screen._update_notes_ui_state)
