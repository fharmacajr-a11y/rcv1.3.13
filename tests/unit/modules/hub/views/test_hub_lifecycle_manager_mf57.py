# -*- coding: utf-8 -*-
"""Testes unitários para hub_lifecycle_manager.py (MF-57).

Cobre:
- Inicialização com/sem logger
- Start: idempotência, delegação para HubLifecycle
- Stop: idempotência, delegação com tratamento de erro
- Propriedades: is_active, lifecycle
- Logger debug/warning em start/stop

Estratégia:
- Headless (FakeParent + mock de HubLifecycle)
- Verificação de delegação 1:1
- Cobertura de branches (polling ativo/inativo, logger presente/ausente)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.modules.hub.views.hub_lifecycle_manager import HubLifecycleManager


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES: FakeParent
# ═══════════════════════════════════════════════════════════════════════════════


class FakeParent:
    """Simula HubScreen com métodos Tk necessários."""

    def __init__(self) -> None:
        self.after_calls: list[tuple[int, Any]] = []
        self.after_cancel_calls: list[str] = []
        self._after_id = 0

    def after(self, ms: int, fn: Any) -> str:
        """Registra chamada after e retorna ID."""
        self._after_id += 1
        after_id = f"after#{self._after_id}"
        self.after_calls.append((ms, fn))
        return after_id

    def after_cancel(self, after_id: str) -> None:
        """Registra cancelamento."""
        self.after_cancel_calls.append(after_id)


@pytest.fixture
def fake_parent() -> FakeParent:
    """Fixture para FakeParent."""
    return FakeParent()


@pytest.fixture
def mock_logger() -> MagicMock:
    """Fixture para logger mock."""
    return MagicMock()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: Inicialização
# ═══════════════════════════════════════════════════════════════════════════════


class TestHubLifecycleManagerInit:
    """Testes de inicialização."""

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_init_without_logger(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """__init__ sem logger deve criar HubLifecycle sem logger."""
        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]

        assert manager._tk_root is fake_parent
        assert manager._logger is None
        assert manager._polling_active is False
        mock_lifecycle_class.assert_called_once_with(tk_root=fake_parent, logger=None)

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_init_with_logger(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent, mock_logger: MagicMock
    ) -> None:
        """__init__ com logger deve criar HubLifecycle com logger."""
        manager = HubLifecycleManager(tk_root=fake_parent, logger=mock_logger)  # type: ignore[arg-type]

        assert manager._tk_root is fake_parent
        assert manager._logger is mock_logger
        assert manager._polling_active is False
        mock_lifecycle_class.assert_called_once_with(tk_root=fake_parent, logger=mock_logger)

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_init_sets_lifecycle_instance(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """__init__ deve armazenar instância de HubLifecycle."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]

        assert manager._lifecycle is mock_lifecycle_instance


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: start()
# ═══════════════════════════════════════════════════════════════════════════════


class TestHubLifecycleManagerStart:
    """Testes do método start."""

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_start_delegates_to_lifecycle(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """start() deve delegar para HubLifecycle.start()."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.start()

        mock_lifecycle_instance.start.assert_called_once_with()
        assert manager._polling_active is True

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_start_logs_when_logger_present(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent, mock_logger: MagicMock
    ) -> None:
        """start() com logger deve logar debug."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=mock_logger)  # type: ignore[arg-type]
        manager.start()

        mock_logger.debug.assert_called_once_with("[HubLifecycleManager] Iniciando lifecycle")

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_start_idempotent_when_already_active(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent
    ) -> None:
        """start() deve ser idempotente: não chamar lifecycle.start() se já ativo."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.start()
        manager.start()  # Segunda chamada

        # start() deve ter sido chamado apenas uma vez
        mock_lifecycle_instance.start.assert_called_once()

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_start_idempotent_logs_when_logger_present(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent, mock_logger: MagicMock
    ) -> None:
        """start() idempotente com logger deve logar debug."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=mock_logger)  # type: ignore[arg-type]
        manager.start()
        mock_logger.reset_mock()
        manager.start()  # Segunda chamada

        mock_logger.debug.assert_called_once_with("[HubLifecycleManager] Lifecycle já ativo, ignorando start()")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: stop()
# ═══════════════════════════════════════════════════════════════════════════════


class TestHubLifecycleManagerStop:
    """Testes do método stop."""

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_stop_delegates_to_lifecycle(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """stop() deve delegar para HubLifecycle.stop()."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.start()
        manager.stop()

        mock_lifecycle_instance.stop.assert_called_once_with()
        assert manager._polling_active is False

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_stop_logs_when_logger_present(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent, mock_logger: MagicMock
    ) -> None:
        """stop() com logger deve logar debug."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=mock_logger)  # type: ignore[arg-type]
        manager.start()
        mock_logger.reset_mock()
        manager.stop()

        mock_logger.debug.assert_called_once_with("[HubLifecycleManager] Parando lifecycle")

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_stop_idempotent_when_already_inactive(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent
    ) -> None:
        """stop() deve ser idempotente: não chamar lifecycle.stop() se já inativo."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.stop()  # Parar sem ter iniciado

        # stop() não deve ter sido chamado
        mock_lifecycle_instance.stop.assert_not_called()

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_stop_handles_exception_from_lifecycle(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent
    ) -> None:
        """stop() deve tratar exceção de lifecycle.stop() sem propagar."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_instance.stop.side_effect = RuntimeError("stop failed")
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.start()

        # Não deve propagar exceção
        manager.stop()

        assert manager._polling_active is False

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_stop_logs_exception_when_logger_present(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent, mock_logger: MagicMock
    ) -> None:
        """stop() com logger deve logar warning ao tratar exceção."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_instance.stop.side_effect = RuntimeError("stop failed")
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=mock_logger)  # type: ignore[arg-type]
        manager.start()
        mock_logger.reset_mock()
        manager.stop()

        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "[HubLifecycleManager] Erro ao parar lifecycle:" in warning_msg
        assert "stop failed" in warning_msg


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: Propriedades
# ═══════════════════════════════════════════════════════════════════════════════


class TestHubLifecycleManagerProperties:
    """Testes das propriedades."""

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_is_active_false_initially(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """is_active deve ser False inicialmente."""
        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]

        assert manager.is_active is False

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_is_active_true_after_start(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """is_active deve ser True após start()."""
        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.start()

        assert manager.is_active is True

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_is_active_false_after_stop(self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent) -> None:
        """is_active deve ser False após stop()."""
        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]
        manager.start()
        manager.stop()

        assert manager.is_active is False

    @patch("src.modules.hub.views.hub_lifecycle_manager.HubLifecycle")
    def test_lifecycle_property_returns_instance(
        self, mock_lifecycle_class: MagicMock, fake_parent: FakeParent
    ) -> None:
        """lifecycle property deve retornar instância de HubLifecycle."""
        mock_lifecycle_instance = MagicMock()
        mock_lifecycle_class.return_value = mock_lifecycle_instance

        manager = HubLifecycleManager(tk_root=fake_parent, logger=None)  # type: ignore[arg-type]

        assert manager.lifecycle is mock_lifecycle_instance
