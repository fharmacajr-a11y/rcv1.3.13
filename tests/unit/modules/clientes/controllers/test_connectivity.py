"""Testes unitários para ClientesConnectivityController.

Este módulo testa o controller de conectividade sem depender de Tkinter real,
usando mocks para o frame e as dependências externas (get_supabase_state,
get_cloud_status_for_ui).

Cobertura esperada: >= 80% do arquivo connectivity.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.clientes.controllers.connectivity import ClientesConnectivityController


@pytest.fixture
def mock_frame() -> MagicMock:
    """Cria um mock do MainScreenFrame com métodos Tk necessários."""
    frame = MagicMock()
    frame.after = MagicMock(return_value="job_123")
    frame.after_cancel = MagicMock()
    frame._apply_connectivity_state = MagicMock()
    return frame


@pytest.fixture
def controller(mock_frame: MagicMock) -> ClientesConnectivityController:
    """Cria uma instância do controller com frame mockado."""
    return ClientesConnectivityController(frame=mock_frame)


class TestClientesConnectivityControllerInit:
    """Testes de inicialização do controller."""

    def test_controller_criado_com_valores_default(self, mock_frame: MagicMock) -> None:
        """Controller deve iniciar com estado parado e sem job agendado."""
        ctrl = ClientesConnectivityController(frame=mock_frame)

        assert ctrl.frame is mock_frame
        assert ctrl._job_id is None
        assert ctrl._running is False
        assert ctrl._interval_ms == 5000


class TestClientesConnectivityControllerStart:
    """Testes do método start()."""

    def test_start_inicia_monitor_e_agenda_primeiro_tick(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Start deve marcar como running e agendar primeiro tick após 2s."""
        controller.start()

        assert controller._running is True
        assert controller._job_id == "job_123"
        mock_frame.after.assert_called_once_with(2000, controller._tick)

    def test_start_nao_agenda_se_ja_running(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Start não deve fazer nada se já estiver rodando."""
        controller._running = True
        controller._job_id = "existing_job"

        controller.start()

        # Não deve chamar after novamente
        mock_frame.after.assert_not_called()
        assert controller._job_id == "existing_job"

    def test_start_trata_excecao_ao_agendar(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Se after() lançar exceção, deve resetar _running."""
        mock_frame.after.side_effect = RuntimeError("Frame destroyed")

        controller.start()

        assert controller._running is False
        assert controller._job_id is None


class TestClientesConnectivityControllerStop:
    """Testes do método stop()."""

    def test_stop_cancela_job_e_marca_stopped(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Stop deve cancelar job agendado e marcar como parado."""
        controller._running = True
        controller._job_id = "job_456"

        controller.stop()

        assert controller._running is False
        assert controller._job_id is None
        mock_frame.after_cancel.assert_called_once_with("job_456")

    def test_stop_nao_cancela_se_nao_running(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Stop não deve cancelar se não estiver rodando."""
        controller._running = False
        controller._job_id = None

        controller.stop()

        mock_frame.after_cancel.assert_not_called()

    def test_stop_trata_excecao_ao_cancelar(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Se after_cancel() lançar exceção, deve continuar e resetar job_id."""
        controller._running = True
        controller._job_id = "job_789"
        mock_frame.after_cancel.side_effect = RuntimeError("Invalid job ID")

        controller.stop()

        assert controller._running is False
        assert controller._job_id is None


class TestClientesConnectivityControllerScheduleNext:
    """Testes do método _schedule_next()."""

    def test_schedule_next_agenda_proximo_tick(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """_schedule_next deve agendar próximo tick com interval_ms."""
        controller._running = True
        mock_frame.after.return_value = "job_next"

        controller._schedule_next()

        assert controller._job_id == "job_next"
        mock_frame.after.assert_called_once_with(5000, controller._tick)

    def test_schedule_next_nao_agenda_se_stopped(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """_schedule_next não deve agendar se controller estiver parado."""
        controller._running = False

        controller._schedule_next()

        mock_frame.after.assert_not_called()

    def test_schedule_next_trata_excecao(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Se after() falhar, deve resetar job_id e não crashar."""
        controller._running = True
        mock_frame.after.side_effect = RuntimeError("Cannot schedule")

        controller._schedule_next()

        assert controller._job_id is None


class TestClientesConnectivityControllerTick:
    """Testes do método _tick()."""

    @patch("src.modules.clientes.controllers.connectivity.get_supabase_state")
    @patch("src.modules.clientes.controllers.connectivity.get_cloud_status_for_ui")
    def test_tick_consulta_estado_e_aplica_na_ui(
        self,
        mock_get_ui_status: MagicMock,
        mock_get_state: MagicMock,
        controller: ClientesConnectivityController,
        mock_frame: MagicMock,
    ) -> None:
        """_tick deve consultar estado e aplicar na UI via frame."""
        controller._running = True
        mock_get_state.return_value = ("online", "Tudo OK")
        mock_get_ui_status.return_value = ("Online", "success", "Conectado")

        controller._tick()

        mock_get_state.assert_called_once()
        mock_get_ui_status.assert_called_once()
        mock_frame._apply_connectivity_state.assert_called_once_with(
            "online", "Tudo OK", "Online", "success", "Conectado"
        )
        # Deve agendar próximo tick
        assert mock_frame.after.call_count == 1

    @patch("src.modules.clientes.controllers.connectivity.get_supabase_state")
    def test_tick_trata_excecao_e_continua(
        self,
        mock_get_state: MagicMock,
        controller: ClientesConnectivityController,
        mock_frame: MagicMock,
    ) -> None:
        """Se consulta falhar, deve logar e agendar próximo tick."""
        controller._running = True
        mock_get_state.side_effect = RuntimeError("Network error")

        controller._tick()

        # Mesmo com erro, deve agendar próximo tick
        mock_frame.after.assert_called_once_with(5000, controller._tick)

    def test_tick_nao_executa_se_stopped(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """_tick não deve fazer nada se controller estiver parado."""
        controller._running = False

        controller._tick()

        mock_frame._apply_connectivity_state.assert_not_called()
        mock_frame.after.assert_not_called()

    @patch("src.modules.clientes.controllers.connectivity.get_supabase_state")
    @patch("src.modules.clientes.controllers.connectivity.get_cloud_status_for_ui")
    def test_tick_agenda_proximo_mesmo_se_apply_falhar(
        self,
        mock_get_ui_status: MagicMock,
        mock_get_state: MagicMock,
        controller: ClientesConnectivityController,
        mock_frame: MagicMock,
    ) -> None:
        """Mesmo se _apply_connectivity_state falhar, deve agendar próximo tick."""
        controller._running = True
        mock_get_state.return_value = ("offline", "Sem conexão")
        mock_get_ui_status.return_value = ("Offline", "danger", "Desconectado")
        mock_frame._apply_connectivity_state.side_effect = RuntimeError("UI error")

        controller._tick()

        # Deve ter tentado aplicar estado
        mock_frame._apply_connectivity_state.assert_called_once()
        # E mesmo assim agendar próximo tick (finally block)
        mock_frame.after.assert_called_once_with(5000, controller._tick)


class TestClientesConnectivityControllerIntegration:
    """Testes de integração entre métodos do controller."""

    @patch("src.modules.clientes.controllers.connectivity.get_supabase_state")
    @patch("src.modules.clientes.controllers.connectivity.get_cloud_status_for_ui")
    def test_ciclo_completo_start_tick_stop(
        self,
        mock_get_ui_status: MagicMock,
        mock_get_state: MagicMock,
        controller: ClientesConnectivityController,
        mock_frame: MagicMock,
    ) -> None:
        """Testa ciclo completo: start -> tick -> stop."""
        mock_get_state.return_value = ("unstable", "Intermitente")
        mock_get_ui_status.return_value = ("Instável", "warning", "Conexão fraca")

        # Simular que after() retorna job_ids sequenciais
        job_ids = ["job_1", "job_2"]
        mock_frame.after.side_effect = job_ids

        # 1. Start
        controller.start()
        assert controller._running is True
        assert controller._job_id == "job_1"

        # 2. Executar tick manualmente
        controller._tick()
        mock_frame._apply_connectivity_state.assert_called_once()
        assert controller._job_id == "job_2"  # Agendou próximo

        # 3. Stop
        controller.stop()
        assert controller._running is False
        assert controller._job_id is None
        mock_frame.after_cancel.assert_called_once_with("job_2")

    def test_multiplos_starts_nao_duplicam_jobs(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Chamar start() múltiplas vezes não deve criar múltiplos jobs."""
        controller.start()
        first_job = controller._job_id

        controller.start()
        controller.start()

        # Deve ter agendado apenas uma vez
        assert mock_frame.after.call_count == 1
        assert controller._job_id == first_job

    def test_stop_antes_de_start_nao_causa_erro(
        self, controller: ClientesConnectivityController, mock_frame: MagicMock
    ) -> None:
        """Chamar stop() antes de start() não deve causar erro."""
        controller.stop()  # Não deve crashar

        assert controller._running is False
        mock_frame.after_cancel.assert_not_called()

    @patch("src.modules.clientes.controllers.connectivity.get_supabase_state")
    @patch("src.modules.clientes.controllers.connectivity.get_cloud_status_for_ui")
    def test_tick_com_diferentes_estados_de_conectividade(
        self,
        mock_get_ui_status: MagicMock,
        mock_get_state: MagicMock,
        controller: ClientesConnectivityController,
        mock_frame: MagicMock,
    ) -> None:
        """Testa _tick com diferentes estados retornados pelas funções."""
        controller._running = True

        # Estado online
        mock_get_state.return_value = ("online", "Conectado")
        mock_get_ui_status.return_value = ("Online", "success", "OK")
        controller._tick()

        # Estado unstable
        mock_get_state.return_value = ("unstable", "Lento")
        mock_get_ui_status.return_value = ("Instável", "warning", "Lento")
        controller._tick()

        # Estado offline
        mock_get_state.return_value = ("offline", "Desconectado")
        mock_get_ui_status.return_value = ("Offline", "danger", "Erro")
        controller._tick()

        # Deve ter aplicado 3 estados diferentes
        assert mock_frame._apply_connectivity_state.call_count == 3


class TestClientesConnectivityControllerCustomInterval:
    """Testes com intervalo personalizado."""

    def test_controller_com_intervalo_customizado(self, mock_frame: MagicMock) -> None:
        """Controller deve respeitar intervalo customizado."""
        ctrl = ClientesConnectivityController(frame=mock_frame, _interval_ms=10000)

        assert ctrl._interval_ms == 10000

        ctrl._running = True
        ctrl._schedule_next()

        mock_frame.after.assert_called_once_with(10000, ctrl._tick)
