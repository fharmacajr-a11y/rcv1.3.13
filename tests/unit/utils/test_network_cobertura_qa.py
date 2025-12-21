"""
Testes de cobertura QA para src/utils/network.py

Objetivo: Cobrir branch faltante (linha 30->37) - WinError 10013 já logado.
"""

from __future__ import annotations

import socket
from email.message import Message
from unittest.mock import MagicMock, patch

import pytest

import src.utils.network as network


@pytest.fixture(autouse=True)
def _reset_winerror_flag():
    """Reset flag global antes de cada teste."""
    network._winerror_10013_logged = False
    yield
    network._winerror_10013_logged = False


class TestWinError10013Branch:
    """Testes para cobrir branch de WinError 10013 já logado."""

    def test_socket_check_winerror_10013_primeira_vez_loga(self, monkeypatch):
        """
        Testa que WinError 10013 na primeira vez loga debug e seta flag.
        (Esse caso já está coberto pelos testes existentes, mas vamos garantir)
        """
        # Criar OSError com winerror=10013
        error = OSError("Permission denied")
        error.winerror = 10013

        # Mock socket.create_connection para lançar erro
        def mock_create_connection(*args, **kwargs):
            raise error

        monkeypatch.setattr(socket, "create_connection", mock_create_connection)

        # Verificar que flag está False inicialmente
        assert network._winerror_10013_logged is False

        # Executar socket check
        with patch.object(network.logger, "debug") as mock_debug:
            result = network._socket_check(timeout=1.0)

            # Verificar que retornou False
            assert result is False

            # Verificar que debug foi chamado
            mock_debug.assert_called_once()
            assert "WinError 10013" in mock_debug.call_args[0][0]

            # Verificar que flag foi setada
            assert network._winerror_10013_logged is True

    def test_socket_check_winerror_10013_segunda_vez_nao_loga(self, monkeypatch):
        """
        Testa que WinError 10013 na SEGUNDA vez NÃO loga (branch 30->37).
        Este é o branch que estava faltando na cobertura.
        """
        # Setar flag como True (já logado anteriormente)
        network._winerror_10013_logged = True

        # Criar OSError com winerror=10013
        error = OSError("Permission denied")
        error.winerror = 10013

        # Mock socket.create_connection para lançar erro
        def mock_create_connection(*args, **kwargs):
            raise error

        monkeypatch.setattr(socket, "create_connection", mock_create_connection)

        # Executar socket check
        with patch.object(network.logger, "debug") as mock_debug:
            result = network._socket_check(timeout=1.0)

            # Verificar que retornou False
            assert result is False

            # Verificar que debug NÃO foi chamado (já estava logado)
            mock_debug.assert_not_called()

            # Flag deve permanecer True
            assert network._winerror_10013_logged is True

    def test_socket_check_winerror_10013_sequencia_completa(self, monkeypatch):
        """
        Testa sequência completa: primeira vez loga, segunda vez não loga.
        Garante que ambos os branches são cobertos em um único teste.
        """
        # Criar OSError com winerror=10013
        error = OSError("Permission denied")
        error.winerror = 10013

        # Mock socket.create_connection para lançar erro
        def mock_create_connection(*args, **kwargs):
            raise error

        monkeypatch.setattr(socket, "create_connection", mock_create_connection)

        # Primeira chamada: deve logar
        with patch.object(network.logger, "debug") as mock_debug:
            result1 = network._socket_check(timeout=1.0)

            assert result1 is False
            assert mock_debug.call_count == 1
            assert "WinError 10013" in mock_debug.call_args[0][0]

        # Segunda chamada: NÃO deve logar (branch faltante)
        with patch.object(network.logger, "debug") as mock_debug:
            result2 = network._socket_check(timeout=1.0)

            assert result2 is False
            assert mock_debug.call_count == 0  # Não deve ter chamado debug

    def test_socket_check_winerror_10013_apos_reset_loga_novamente(self, monkeypatch):
        """
        Testa que após resetar flag, WinError 10013 volta a logar.
        """
        # Setar flag como True
        network._winerror_10013_logged = True

        # Resetar flag (simula restart ou reset manual)
        network._winerror_10013_logged = False

        # Criar OSError com winerror=10013
        error = OSError("Permission denied")
        error.winerror = 10013

        # Mock socket.create_connection
        def mock_create_connection(*args, **kwargs):
            raise error

        monkeypatch.setattr(socket, "create_connection", mock_create_connection)

        # Executar socket check
        with patch.object(network.logger, "debug") as mock_debug:
            result = network._socket_check(timeout=1.0)

            assert result is False
            mock_debug.assert_called_once()
            assert "WinError 10013" in mock_debug.call_args[0][0]


class TestEdgeCasesAdicionais:
    """Testes de edge cases adicionais para aumentar cobertura."""

    def test_socket_check_oserror_sem_winerror_attribute(self, monkeypatch):
        """
        Testa OSError sem atributo winerror (ou winerror=None).
        """
        # Criar OSError sem winerror
        error = OSError("Generic error")

        # Mock socket.create_connection
        def mock_create_connection(*args, **kwargs):
            raise error

        monkeypatch.setattr(socket, "create_connection", mock_create_connection)

        # Executar socket check
        with patch.object(network.logger, "warning") as mock_warning:
            result = network._socket_check(timeout=1.0)

            assert result is False
            mock_warning.assert_called_once()
            assert "Generic error" in str(mock_warning.call_args)

    def test_socket_check_oserror_com_winerror_diferente(self, monkeypatch):
        """
        Testa OSError com winerror diferente de 10013.
        """
        # Criar OSError com winerror != 10013
        error = OSError("Connection refused")
        error.winerror = 10061  # WSAECONNREFUSED

        # Mock socket.create_connection
        def mock_create_connection(*args, **kwargs):
            raise error

        monkeypatch.setattr(socket, "create_connection", mock_create_connection)

        # Executar socket check
        with patch.object(network.logger, "warning") as mock_warning:
            result = network._socket_check(timeout=1.0)

            assert result is False
            mock_warning.assert_called_once()
            assert "Connection refused" in str(mock_warning.call_args)

    def test_http_check_urlerror_vs_httperror(self, monkeypatch):
        """
        Testa que _http_check trata URLError e HTTPError corretamente.
        """
        from urllib.error import HTTPError, URLError

        # Criar lista de erros para cada URL
        hdrs = Message()
        errors = [
            URLError("Network unreachable"),
            HTTPError("http://test.com", 404, "Not Found", hdrs, None),
            OSError("Connection reset"),
        ]

        call_count = 0

        def mock_urlopen(*args, **kwargs):
            nonlocal call_count
            error = errors[call_count % len(errors)]
            call_count += 1
            raise error

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        # Executar http check
        with patch.object(network.logger, "debug") as mock_debug:
            result = network._http_check(timeout=2.0)

            assert result is False
            # Deve ter tentado 3 URLs (test_urls tem 3 itens)
            assert mock_debug.call_count == 3

    def test_check_internet_connectivity_com_timeout_customizado(self, monkeypatch):
        """
        Testa check_internet_connectivity com timeout < 2.0 (deve usar 2.0 para HTTP).
        """
        # Mock socket check para falhar
        monkeypatch.setattr(network, "_socket_check", lambda timeout: False)

        # Mock http check para capturar timeout passado
        http_timeout_received = []

        def mock_http_check(timeout):
            http_timeout_received.append(timeout)
            return False

        monkeypatch.setattr(network, "_http_check", mock_http_check)

        # Executar com timeout < 2.0
        result = network.check_internet_connectivity(timeout=0.5)

        assert result is False
        # HTTP timeout deve ser max(0.5, 2.0) = 2.0
        assert len(http_timeout_received) == 1
        assert http_timeout_received[0] == 2.0

    def test_require_internet_or_alert_user_clica_cancel(self, monkeypatch):
        """
        Testa require_internet_or_alert quando usuário clica Cancel (retorna False).
        """
        # Configurar ambiente cloud-only
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
        monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)

        # Mock check_internet_connectivity para retornar False (offline)
        monkeypatch.setattr(network, "check_internet_connectivity", lambda: False)

        # Mock messagebox para retornar False (Cancel)
        mock_root = MagicMock()
        mock_messagebox = MagicMock()
        mock_messagebox.askokcancel.return_value = False

        with (
            patch("tkinter.Tk", return_value=mock_root),
            patch("tkinter.messagebox", mock_messagebox),
        ):
            result = network.require_internet_or_alert()

            # Verificar que askokcancel foi chamado
            mock_messagebox.askokcancel.assert_called_once()
            # Resultado deve ser False (usuário cancelou)
            assert result is False

    def test_require_internet_or_alert_nao_cloud_only(self, monkeypatch):
        """
        Testa require_internet_or_alert quando NÃO está em modo cloud-only.
        """
        # Remover RC_NO_LOCAL_FS ou setar != "1"
        monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)

        # Executar (não deve verificar internet)
        with patch.object(network.logger, "debug") as mock_debug:
            result = network.require_internet_or_alert()

            assert result is True
            mock_debug.assert_called_once()
            assert "Not in cloud-only mode" in mock_debug.call_args[0][0]

    def test_require_internet_or_alert_rc_no_gui_errors(self, monkeypatch):
        """
        Testa require_internet_or_alert quando RC_NO_GUI_ERRORS=1 (sem GUI).
        """
        # Configurar ambiente cloud-only + sem GUI
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
        monkeypatch.setenv("RC_NO_GUI_ERRORS", "1")

        # Mock check_internet_connectivity para retornar False
        monkeypatch.setattr(network, "check_internet_connectivity", lambda: False)

        # Executar (não deve tentar mostrar GUI)
        result = network.require_internet_or_alert()

        # Deve retornar False sem tentar GUI
        assert result is False
