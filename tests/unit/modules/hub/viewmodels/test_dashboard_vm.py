# -*- coding: utf-8 -*-
"""Testes para DashboardViewModel (headless, sem Tkinter)."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from src.modules.hub.dashboard_service import DashboardSnapshot
from src.modules.hub.viewmodels import DashboardCardView, DashboardViewModel, DashboardViewState


class TestDashboardViewModel:
    """Testes para DashboardViewModel."""

    def test_initial_state(self):
        """Estado inicial deve ser vazio (não carregado, sem erro)."""
        vm = DashboardViewModel()
        state = vm.state

        assert state.is_loading is False
        assert state.error_message is None
        assert state.snapshot is None
        assert state.card_clientes is None
        assert state.card_pendencias is None
        assert state.card_tarefas is None

    def test_load_success_with_all_zeros(self):
        """Carregar com sucesso snapshot com todos os valores zerados."""
        # Mock do service retornando snapshot vazio
        mock_snapshot = DashboardSnapshot(
            active_clients=0,
            pending_obligations=0,
            tasks_today=0,
        )
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org", today=date(2025, 12, 8))

        # Verificar que service foi chamado com parâmetros corretos
        mock_service.assert_called_once_with(org_id="test-org", today=date(2025, 12, 8))

        # Verificar estado final
        assert state.is_loading is False
        assert state.error_message is None
        assert state.snapshot is mock_snapshot

        # Verificar cards foram criados
        assert state.card_clientes is not None
        assert state.card_pendencias is not None
        assert state.card_tarefas is not None

    def test_load_success_with_values(self):
        """Carregar com sucesso snapshot com valores não-zero."""
        mock_snapshot = DashboardSnapshot(
            active_clients=15,
            pending_obligations=3,
            tasks_today=7,
        )
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org", today=None)

        assert state.is_loading is False
        assert state.error_message is None
        assert state.snapshot is mock_snapshot
        assert state.card_clientes is not None
        assert state.card_pendencias is not None
        assert state.card_tarefas is not None

    def test_load_failure_exception(self):
        """Service lançando exceção deve resultar em estado de erro."""
        mock_service = Mock(side_effect=Exception("Database connection failed"))

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org", today=None)

        # Verificar estado de erro
        assert state.is_loading is False
        assert state.error_message is not None
        assert "não foi possível carregar" in state.error_message.lower()
        assert state.snapshot is None
        assert state.card_clientes is None
        assert state.card_pendencias is None
        assert state.card_tarefas is None


class TestCardClientes:
    """Testes para formatação do card de Clientes Ativos."""

    def test_card_clientes_zero(self):
        """Card de clientes com 0 ativos."""
        mock_snapshot = DashboardSnapshot(active_clients=0)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_clientes
        assert card is not None
        assert card.label == "Clientes"
        assert card.value == 0
        assert card.value_text == "0"
        assert card.bootstyle == "info"

    def test_card_clientes_with_value(self):
        """Card de clientes com valor positivo."""
        mock_snapshot = DashboardSnapshot(active_clients=42)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_clientes
        assert card is not None
        assert card.label == "Clientes"
        assert card.value == 42
        assert card.value_text == "42"
        assert card.bootstyle == "info"  # Sempre info (azul neutro)


class TestCardPendencias:
    """Testes para formatação do card de Pendências Regulatórias."""

    def test_card_pendencias_zero(self):
        """Card de pendências com 0 pendências (verde, sem ícone)."""
        mock_snapshot = DashboardSnapshot(pending_obligations=0)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_pendencias
        assert card is not None
        assert card.label == "Pendências"
        assert card.value == 0
        assert card.value_text == "0"
        assert card.bootstyle == "success"  # Verde quando 0

    def test_card_pendencias_with_one(self):
        """Card de pendências com 1 pendência (vermelho, com ícone)."""
        mock_snapshot = DashboardSnapshot(pending_obligations=1)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_pendencias
        assert card is not None
        assert card.label == "Pendências"
        assert card.value == 1
        assert card.value_text == "1 ⚠"  # Com ícone de alerta
        assert card.bootstyle == "danger"  # Vermelho quando >0

    def test_card_pendencias_with_many(self):
        """Card de pendências com várias pendências (vermelho, com ícone)."""
        mock_snapshot = DashboardSnapshot(pending_obligations=15)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_pendencias
        assert card is not None
        assert card.label == "Pendências"
        assert card.value == 15
        assert card.value_text == "15 ⚠"
        assert card.bootstyle == "danger"


class TestCardTarefas:
    """Testes para formatação do card de Tarefas Hoje."""

    def test_card_tarefas_zero(self):
        """Card de tarefas com 0 tarefas (verde)."""
        mock_snapshot = DashboardSnapshot(tasks_today=0)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_tarefas
        assert card is not None
        assert card.label == "Tarefas hoje"
        assert card.value == 0
        assert card.value_text == "0"
        assert card.bootstyle == "success"  # Verde quando 0

    def test_card_tarefas_with_one(self):
        """Card de tarefas com 1 tarefa (amarelo)."""
        mock_snapshot = DashboardSnapshot(tasks_today=1)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_tarefas
        assert card is not None
        assert card.label == "Tarefas hoje"
        assert card.value == 1
        assert card.value_text == "1"
        assert card.bootstyle == "warning"  # Amarelo quando >0

    def test_card_tarefas_with_many(self):
        """Card de tarefas com várias tarefas (amarelo)."""
        mock_snapshot = DashboardSnapshot(tasks_today=25)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org")

        card = state.card_tarefas
        assert card is not None
        assert card.label == "Tarefas hoje"
        assert card.value == 25
        assert card.value_text == "25"
        assert card.bootstyle == "warning"


class TestViewStateImmutability:
    """Testes para garantir que DashboardViewState é imutável."""

    def test_state_is_frozen(self):
        """DashboardViewState deve ser frozen (imutável)."""
        state = DashboardViewState()

        # Tentar modificar deve lançar exceção
        with pytest.raises(Exception):  # dataclass frozen levanta FrozenInstanceError
            state.is_loading = True

    def test_card_view_is_frozen(self):
        """DashboardCardView deve ser frozen (imutável)."""
        card = DashboardCardView(
            label="Test",
            value=10,
            value_text="10",
            bootstyle="info",
        )

        # Tentar modificar deve lançar exceção
        with pytest.raises(Exception):
            card.value = 20


class TestEdgeCases:
    """Testes de casos extremos."""

    def test_load_with_none_today(self):
        """Carregar com today=None deve funcionar (usa date.today())."""
        mock_snapshot = DashboardSnapshot(active_clients=5)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)
        state = vm.load(org_id="test-org", today=None)

        # Service deve ter sido chamado com today=None
        mock_service.assert_called_once_with(org_id="test-org", today=None)
        assert state.snapshot is mock_snapshot

    def test_multiple_loads_update_state(self):
        """Múltiplas cargas devem atualizar o estado corretamente."""
        mock_snapshot1 = DashboardSnapshot(active_clients=10)
        mock_snapshot2 = DashboardSnapshot(active_clients=20)

        mock_service = Mock(side_effect=[mock_snapshot1, mock_snapshot2])

        vm = DashboardViewModel(service=mock_service)

        # Primeira carga
        state1 = vm.load(org_id="test-org")
        assert state1.snapshot is not None
        assert state1.card_clientes is not None
        assert state1.snapshot.active_clients == 10
        assert state1.card_clientes.value == 10

        # Segunda carga
        state2 = vm.load(org_id="test-org")
        assert state2.snapshot is not None
        assert state2.card_clientes is not None
        assert state2.snapshot.active_clients == 20
        assert state2.card_clientes.value == 20

    def test_load_after_error_clears_error(self):
        """Carregar com sucesso após erro deve limpar estado de erro."""
        mock_service = Mock(
            side_effect=[
                Exception("First error"),
                DashboardSnapshot(active_clients=5),
            ]
        )

        vm = DashboardViewModel(service=mock_service)

        # Primeira carga com erro
        state1 = vm.load(org_id="test-org")
        assert state1.error_message is not None
        assert state1.snapshot is None

        # Segunda carga com sucesso
        state2 = vm.load(org_id="test-org")
        assert state2.error_message is None
        assert state2.snapshot is not None
        assert state2.snapshot.active_clients == 5


class TestDashboardViewModelStateFactories:
    """Testes para métodos factory de estados (start_loading, from_error)."""

    def test_start_loading_creates_loading_state(self):
        """start_loading deve criar estado de loading limpo."""
        vm = DashboardViewModel()
        state = vm.start_loading()

        assert state.is_loading is True
        assert state.error_message is None
        assert state.snapshot is None
        assert state.card_clientes is None
        assert state.card_pendencias is None
        assert state.card_tarefas is None

    def test_from_error_creates_error_state(self):
        """from_error deve criar estado de erro com mensagem."""
        vm = DashboardViewModel()
        state = vm.from_error("Erro de teste")

        assert state.is_loading is False
        assert state.error_message == "Erro de teste"
        assert state.snapshot is None
        assert state.card_clientes is None
        assert state.card_pendencias is None
        assert state.card_tarefas is None

    def test_start_loading_clears_previous_state(self):
        """start_loading deve limpar estado anterior (sucesso ou erro)."""
        mock_snapshot = DashboardSnapshot(active_clients=10)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)

        # Carregar com sucesso
        state1 = vm.load(org_id="test-org")
        assert state1.snapshot is not None
        assert state1.card_clientes is not None

        # Iniciar loading deve limpar tudo
        state2 = vm.start_loading()
        assert state2.is_loading is True
        assert state2.snapshot is None
        assert state2.card_clientes is None

    def test_from_error_after_success(self):
        """from_error deve substituir estado de sucesso."""
        mock_snapshot = DashboardSnapshot(active_clients=5)
        mock_service = Mock(return_value=mock_snapshot)

        vm = DashboardViewModel(service=mock_service)

        # Carregar com sucesso
        state1 = vm.load(org_id="test-org")
        assert state1.error_message is None
        assert state1.snapshot is not None

        # Criar estado de erro
        state2 = vm.from_error("Novo erro")
        assert state2.error_message == "Novo erro"
        assert state2.snapshot is None

    def test_state_factories_update_vm_state_property(self):
        """Métodos factory devem atualizar vm.state."""
        vm = DashboardViewModel()

        # Após start_loading, state deve refletir loading
        vm.start_loading()
        assert vm.state.is_loading is True

        # Após from_error, state deve refletir erro
        vm.from_error("Teste")
        assert vm.state.error_message == "Teste"
        assert vm.state.is_loading is False
