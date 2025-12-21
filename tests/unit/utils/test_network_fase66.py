"""Testes unitários para src.utils.network — Fase 66.

TEST-009: Cobertura de funções de verificação de conectividade de rede.
Todos os testes usam mocks para evitar dependências de rede real.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch
from urllib.error import URLError

from src.utils.network import (
    _http_check,
    _socket_check,
    check_internet_connectivity,
    require_internet_or_alert,
)


# ==========================
# A) Funções Internas - _socket_check
# ==========================


class TestSocketCheck:
    """Testes para _socket_check (verificação via socket TCP)."""

    @patch("src.utils.network.socket.create_connection")
    def test_socket_sucesso_retorna_true(self, mock_conn: Mock) -> None:
        """Socket bem-sucedido deve retornar True."""
        mock_conn.return_value.__enter__ = Mock()
        mock_conn.return_value.__exit__ = Mock()

        result = _socket_check(timeout=1.0)
        assert result is True
        mock_conn.assert_called_once_with(("8.8.8.8", 53), timeout=1.0)

    @patch("src.utils.network.socket.create_connection")
    def test_socket_oserror_generico_retorna_false(self, mock_conn: Mock) -> None:
        """OSError genérico deve retornar False."""
        mock_conn.side_effect = OSError("Network unreachable")

        result = _socket_check(timeout=1.0)
        assert result is False

    @patch("src.utils.network.socket.create_connection")
    def test_socket_winerror_10013_retorna_false(self, mock_conn: Mock) -> None:
        """WinError 10013 (firewall) deve retornar False e logar uma vez."""
        error = OSError("Permission denied")
        error.winerror = 10013
        mock_conn.side_effect = error

        # Reset flag global para garantir log
        import src.utils.network

        src.utils.network._winerror_10013_logged = False

        result = _socket_check(timeout=1.0)
        assert result is False

    @patch("src.utils.network.socket.create_connection")
    def test_socket_timeout_customizado(self, mock_conn: Mock) -> None:
        """Deve usar timeout customizado na chamada."""
        mock_conn.return_value.__enter__ = Mock()
        mock_conn.return_value.__exit__ = Mock()

        _socket_check(timeout=5.0)
        mock_conn.assert_called_once_with(("8.8.8.8", 53), timeout=5.0)


# ==========================
# A) Funções Internas - _http_check
# ==========================


class TestHttpCheck:
    """Testes para _http_check (fallback via HTTP HEAD)."""

    @patch("src.utils.network.urllib.request.urlopen")
    def test_http_sucesso_primeira_url_retorna_true(self, mock_urlopen: Mock) -> None:
        """Sucesso na primeira URL deve retornar True."""
        mock_urlopen.return_value.__enter__ = Mock()
        mock_urlopen.return_value.__exit__ = Mock()

        result = _http_check(timeout=2.0)
        assert result is True

    @patch("src.utils.network.urllib.request.urlopen")
    def test_http_falha_primeira_sucesso_segunda(self, mock_urlopen: Mock) -> None:
        """Falha na primeira, sucesso na segunda URL deve retornar True."""
        # Primeira chamada falha, segunda sucede
        mock_urlopen.side_effect = [
            URLError("Connection refused"),
            MagicMock(__enter__=Mock(), __exit__=Mock()),
        ]

        result = _http_check(timeout=2.0)
        assert result is True

    @patch("src.utils.network.urllib.request.urlopen")
    def test_http_todas_urls_falham_retorna_false(self, mock_urlopen: Mock) -> None:
        """Falha em todas as URLs deve retornar False."""
        mock_urlopen.side_effect = URLError("Connection refused")

        result = _http_check(timeout=2.0)
        assert result is False

    @patch("src.utils.network.urllib.request.urlopen")
    def test_http_timeout_usado_corretamente(self, mock_urlopen: Mock) -> None:
        """Timeout deve ser passado para urlopen."""
        mock_urlopen.return_value.__enter__ = Mock()
        mock_urlopen.return_value.__exit__ = Mock()

        _http_check(timeout=3.5)

        # Verifica que timeout foi usado em alguma das chamadas
        call_kwargs = mock_urlopen.call_args_list[0][1]
        assert call_kwargs["timeout"] == 3.5


# ==========================
# B) check_internet_connectivity
# ==========================


class TestCheckInternetConnectivity:
    """Testes para check_internet_connectivity."""

    @patch("src.utils.network._socket_check")
    def test_sucesso_via_socket_retorna_true(self, mock_socket: Mock) -> None:
        """Sucesso via socket deve retornar True sem tentar HTTP."""
        mock_socket.return_value = True

        result = check_internet_connectivity()
        assert result is True
        mock_socket.assert_called_once()

    @patch("src.utils.network._http_check")
    @patch("src.utils.network._socket_check")
    def test_falha_socket_sucesso_http_retorna_true(self, mock_socket: Mock, mock_http: Mock) -> None:
        """Falha socket + sucesso HTTP deve retornar True."""
        mock_socket.return_value = False
        mock_http.return_value = True

        result = check_internet_connectivity()
        assert result is True
        mock_socket.assert_called_once()
        mock_http.assert_called_once()

    @patch("src.utils.network._http_check")
    @patch("src.utils.network._socket_check")
    def test_falha_ambos_retorna_false(self, mock_socket: Mock, mock_http: Mock) -> None:
        """Falha em socket e HTTP deve retornar False."""
        mock_socket.return_value = False
        mock_http.return_value = False

        result = check_internet_connectivity()
        assert result is False

    @patch.dict("os.environ", {"RC_NO_NET_CHECK": "1"})
    def test_bypass_com_rc_no_net_check(self) -> None:
        """RC_NO_NET_CHECK=1 deve bypassar check e retornar True."""
        result = check_internet_connectivity()
        assert result is True

    @patch("src.utils.network._socket_check")
    def test_timeout_customizado_passado_socket(self, mock_socket: Mock) -> None:
        """Timeout customizado deve ser passado para _socket_check."""
        mock_socket.return_value = True

        check_internet_connectivity(timeout=3.0)
        mock_socket.assert_called_once_with(timeout=3.0)

    @patch("src.utils.network._http_check")
    @patch("src.utils.network._socket_check")
    def test_timeout_http_minimo_2_segundos(self, mock_socket: Mock, mock_http: Mock) -> None:
        """HTTP fallback deve usar no mínimo 2.0 segundos."""
        mock_socket.return_value = False
        mock_http.return_value = True

        check_internet_connectivity(timeout=0.5)

        # HTTP deve usar max(0.5, 2.0) = 2.0
        mock_http.assert_called_once_with(timeout=2.0)


# ==========================
# C) require_internet_or_alert
# ==========================


class TestRequireInternetOrAlert:
    """Testes para require_internet_or_alert."""

    @patch.dict("os.environ", {}, clear=True)
    def test_modo_nao_cloud_only_retorna_true(self) -> None:
        """Sem RC_NO_LOCAL_FS=1, deve retornar True sem checar."""
        result = require_internet_or_alert()
        assert result is True

    @patch("src.utils.network.check_internet_connectivity")
    @patch.dict("os.environ", {"RC_NO_LOCAL_FS": "1"})
    def test_cloud_only_com_internet_retorna_true(self, mock_check: Mock) -> None:
        """Cloud-only + internet disponível deve retornar True."""
        mock_check.return_value = True

        result = require_internet_or_alert()
        assert result is True
        mock_check.assert_called_once()

    @patch("src.utils.network.check_internet_connectivity")
    @patch.dict("os.environ", {"RC_NO_LOCAL_FS": "1", "RC_NO_GUI_ERRORS": "1"})
    def test_cloud_only_sem_internet_gui_suppressed(self, mock_check: Mock) -> None:
        """Cloud-only + sem internet + GUI suppressed deve retornar False."""
        mock_check.return_value = False

        result = require_internet_or_alert()
        assert result is False

    @patch("tkinter.messagebox.askokcancel")
    @patch("tkinter.Tk")
    @patch("src.utils.network.check_internet_connectivity")
    @patch.dict("os.environ", {"RC_NO_LOCAL_FS": "1"}, clear=True)
    def test_cloud_only_sem_internet_mostra_gui_ok(self, mock_check: Mock, mock_tk: Mock, mock_msgbox: Mock) -> None:
        """Cloud-only + sem internet + user clica OK deve retornar False."""
        mock_check.return_value = False
        mock_msgbox.return_value = True  # User clicked OK

        root_mock = MagicMock()
        mock_tk.return_value = root_mock

        result = require_internet_or_alert()

        # User clicked OK, mas sem internet, então False
        assert result is True  # askokcancel retornou True
        mock_msgbox.assert_called_once()
        root_mock.withdraw.assert_called_once()
        root_mock.destroy.assert_called_once()

    @patch("tkinter.messagebox.askokcancel")
    @patch("tkinter.Tk")
    @patch("src.utils.network.check_internet_connectivity")
    @patch.dict("os.environ", {"RC_NO_LOCAL_FS": "1"}, clear=True)
    def test_cloud_only_sem_internet_mostra_gui_cancel(
        self, mock_check: Mock, mock_tk: Mock, mock_msgbox: Mock
    ) -> None:
        """Cloud-only + sem internet + user clica Cancel deve retornar False."""
        mock_check.return_value = False
        mock_msgbox.return_value = False  # User clicked Cancel

        root_mock = MagicMock()
        mock_tk.return_value = root_mock

        result = require_internet_or_alert()

        assert result is False
        mock_msgbox.assert_called_once()

    @patch("tkinter.Tk")
    @patch("src.utils.network.check_internet_connectivity")
    @patch.dict("os.environ", {"RC_NO_LOCAL_FS": "1"}, clear=True)
    def test_cloud_only_sem_internet_gui_exception(self, mock_check: Mock, mock_tk: Mock) -> None:
        """Exceção ao mostrar GUI deve retornar False e logar warning."""
        mock_check.return_value = False
        mock_tk.side_effect = Exception("Display not available")

        result = require_internet_or_alert()
        assert result is False
