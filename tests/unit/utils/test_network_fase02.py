# -*- coding: utf-8 -*-
"""Testes adicionais para src/utils/network.py - Coverage Pack 01."""

from __future__ import annotations

import socket
import urllib.request
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

from src.utils import network


# ==================== Testes de _socket_check ====================


def test_socket_check_returns_true_on_success(monkeypatch):
    """Testa que _socket_check retorna True quando socket conecta."""
    mock_socket = MagicMock()
    mock_socket.__enter__ = MagicMock(return_value=mock_socket)
    mock_socket.__exit__ = MagicMock(return_value=None)

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: mock_socket)

    result = network._socket_check(timeout=1.0)

    assert result is True


def test_socket_check_returns_false_on_os_error(monkeypatch):
    """Testa que _socket_check retorna False quando OSError ocorre."""

    def fail_connection(*args, **kwargs):
        raise OSError("Connection failed")

    monkeypatch.setattr(socket, "create_connection", fail_connection)

    result = network._socket_check(timeout=1.0)

    assert result is False


def test_socket_check_handles_winerror_10013(monkeypatch):
    """Testa que _socket_check trata WinError 10013 (firewall/VPN)."""

    def fail_with_winerror(*args, **kwargs):
        exc = OSError("Permission denied")
        exc.winerror = 10013
        raise exc

    monkeypatch.setattr(socket, "create_connection", fail_with_winerror)

    result = network._socket_check(timeout=1.0)

    assert result is False


# ==================== Testes de _http_check ====================


def test_http_check_returns_true_on_success(monkeypatch):
    """Testa que _http_check retorna True quando HTTP funciona."""
    mock_response = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=None)

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: mock_response)

    result = network._http_check(timeout=2.0)

    assert result is True


def test_http_check_returns_false_when_all_urls_fail(monkeypatch):
    """Testa que _http_check retorna False quando todas URLs falham."""

    def fail_urlopen(*args, **kwargs):
        raise URLError("Connection failed")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)

    result = network._http_check(timeout=2.0)

    assert result is False


def test_http_check_tries_all_urls_on_error(monkeypatch):
    """Testa que _http_check tenta todas URLs na lista."""
    attempts = []

    def track_urlopen(req, **kwargs):
        attempts.append(req.full_url)
        raise URLError("Failed")

    monkeypatch.setattr(urllib.request, "urlopen", track_urlopen)

    network._http_check(timeout=2.0)

    # Deve tentar pelo menos 2 URLs
    assert len(attempts) >= 2


def test_http_check_handles_http_error(monkeypatch):
    """Testa que _http_check trata HTTPError."""
    from http.client import HTTPMessage

    def fail_with_http_error(*args, **kwargs):
        # Criar HTTPMessage vazio
        import io

        headers = HTTPMessage()
        headers.fp = io.BytesIO()
        raise HTTPError(url="http://test", code=404, msg="Not Found", hdrs=headers, fp=None)

    monkeypatch.setattr(urllib.request, "urlopen", fail_with_http_error)

    result = network._http_check(timeout=2.0)

    assert result is False


def test_http_check_handles_generic_os_error(monkeypatch):
    """Testa que _http_check trata OSError genérico."""

    def fail_with_os_error(*args, **kwargs):
        raise OSError("Generic error")

    monkeypatch.setattr(urllib.request, "urlopen", fail_with_os_error)

    result = network._http_check(timeout=2.0)

    assert result is False


# ==================== Testes de check_internet_connectivity ====================


def test_check_internet_uses_socket_first(monkeypatch):
    """Testa que check_internet_connectivity tenta socket primeiro."""
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    socket_called = []

    def track_socket(*args, **kwargs):
        socket_called.append(True)
        mock = MagicMock()
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=None)
        return mock

    monkeypatch.setattr(socket, "create_connection", track_socket)

    result = network.check_internet_connectivity()

    assert socket_called == [True]
    assert result is True


def test_check_internet_fallback_to_http(monkeypatch):
    """Testa que check_internet_connectivity usa HTTP como fallback."""
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Socket falha
    def fail_socket(*args, **kwargs):
        raise OSError("Socket failed")

    monkeypatch.setattr(socket, "create_connection", fail_socket)

    # HTTP funciona
    mock_response = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=None)

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: mock_response)

    result = network.check_internet_connectivity()

    assert result is True


def test_check_internet_returns_false_when_both_fail(monkeypatch):
    """Testa que check_internet_connectivity retorna False quando socket e HTTP falham."""
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Socket falha
    def fail_socket(*args, **kwargs):
        raise OSError("Socket failed")

    monkeypatch.setattr(socket, "create_connection", fail_socket)

    # HTTP falha
    def fail_http(*args, **kwargs):
        raise URLError("HTTP failed")

    monkeypatch.setattr(urllib.request, "urlopen", fail_http)

    result = network.check_internet_connectivity()

    assert result is False


def test_check_internet_uses_max_timeout_for_http(monkeypatch):
    """Testa que check_internet_connectivity usa timeout >=2.0 para HTTP."""
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Socket falha
    def fail_socket(*args, **kwargs):
        raise OSError("Socket failed")

    monkeypatch.setattr(socket, "create_connection", fail_socket)

    timeouts = []

    def track_timeout(*args, **kwargs):
        timeouts.append(kwargs.get("timeout", 0))
        raise URLError("Failed")

    monkeypatch.setattr(urllib.request, "urlopen", track_timeout)

    # Chamar com timeout pequeno
    network.check_internet_connectivity(timeout=0.5)

    # HTTP deve usar pelo menos 2.0
    assert any(t >= 2.0 for t in timeouts)


# ==================== Testes de require_internet_or_alert ====================


def test_require_internet_shows_gui_alert_when_offline(monkeypatch):
    """Testa que require_internet_or_alert mostra alerta GUI quando offline."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Mock socket e http para falhar
    def fail_connection(*args, **kwargs):
        raise OSError("Failed")

    monkeypatch.setattr(socket, "create_connection", fail_connection)
    monkeypatch.setattr(urllib.request, "urlopen", fail_connection)

    # Mock messagebox
    alert_shown = []

    class FakeTk:
        def withdraw(self):
            pass

        def destroy(self):
            pass

    def fake_askokcancel(title, message, **kwargs):
        alert_shown.append((title, message))
        return False

    import tkinter.messagebox

    monkeypatch.setattr("tkinter.Tk", FakeTk)
    monkeypatch.setattr(tkinter.messagebox, "askokcancel", fake_askokcancel)

    result = network.require_internet_or_alert()

    assert result is False
    assert len(alert_shown) == 1
    assert "Internet Necessária" in alert_shown[0][0]


def test_require_internet_handles_gui_exception(monkeypatch):
    """Testa que require_internet_or_alert continua quando GUI falha."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Mock socket e http para falhar
    def fail_connection(*args, **kwargs):
        raise OSError("Failed")

    monkeypatch.setattr(socket, "create_connection", fail_connection)
    monkeypatch.setattr(urllib.request, "urlopen", fail_connection)

    # Mock Tk para lançar exceção
    def fail_tk():
        raise Exception("GUI not available")

    monkeypatch.setattr("tkinter.Tk", fail_tk)

    result = network.require_internet_or_alert()

    # Deve retornar False sem lançar exceção
    assert result is False


def test_require_internet_returns_result_when_user_clicks_ok(monkeypatch):
    """Testa que require_internet_or_alert retorna True quando usuário clica OK."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    monkeypatch.delenv("RC_NO_GUI_ERRORS", raising=False)
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Mock socket e http para falhar
    def fail_connection(*args, **kwargs):
        raise OSError("Failed")

    monkeypatch.setattr(socket, "create_connection", fail_connection)
    monkeypatch.setattr(urllib.request, "urlopen", fail_connection)

    # Mock messagebox para retornar True (OK)
    class FakeTk:
        def withdraw(self):
            pass

        def destroy(self):
            pass

    def fake_askokcancel(title, message, **kwargs):
        return True  # User clicked OK

    import tkinter.messagebox

    monkeypatch.setattr("tkinter.Tk", FakeTk)
    monkeypatch.setattr(tkinter.messagebox, "askokcancel", fake_askokcancel)

    result = network.require_internet_or_alert()

    # Deve retornar True (usuário clicou OK)
    assert result is True


# ==================== Testes de constantes e módulo ====================


def test_socket_test_host_is_valid():
    """Testa que SOCKET_TEST_HOST está configurado corretamente."""
    assert network.SOCKET_TEST_HOST == ("8.8.8.8", 53)


def test_module_exports_correct_api():
    """Testa que o módulo exporta as funções corretas em __all__."""
    assert "check_internet_connectivity" in network.__all__
    assert "require_internet_or_alert" in network.__all__
    assert len(network.__all__) == 2
