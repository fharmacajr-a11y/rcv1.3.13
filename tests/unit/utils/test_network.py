"""Tests for network connectivity utilities."""

import socket

import pytest  # type: ignore[import-untyped]


def test_check_internet_connectivity_bypassed_in_test(monkeypatch):
    """Test that network check is bypassed when RC_NO_NET_CHECK=1."""
    from src.utils.network import check_internet_connectivity

    monkeypatch.setenv("RC_NO_NET_CHECK", "1")

    # Should return True without actually checking
    assert check_internet_connectivity() is True


def test_check_internet_connectivity_handles_failure(monkeypatch):
    """Test that check returns False when socket connection fails."""
    from src.utils.network import check_internet_connectivity
    import urllib.request

    # Ensure check is not bypassed
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Mock socket.create_connection to raise OSError
    def mock_create_connection(*args, **kwargs):
        raise OSError("Network unreachable")

    monkeypatch.setattr(socket, "create_connection", mock_create_connection)

    # Mock urllib.request.urlopen to raise URLError
    def mock_urlopen(*args, **kwargs):
        from urllib.error import URLError

        raise URLError("HTTP unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = check_internet_connectivity()
    assert result is False


def test_require_internet_skips_check_when_not_cloud_only(monkeypatch):
    """Test that internet check is skipped when RC_NO_LOCAL_FS != 1."""
    from src.utils.network import require_internet_or_alert

    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)

    # Should return True without checking
    assert require_internet_or_alert() is True


def test_require_internet_returns_true_when_online(monkeypatch):
    """Test that require_internet_or_alert returns True when online."""
    from src.utils.network import require_internet_or_alert

    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    monkeypatch.setenv("RC_NO_NET_CHECK", "1")  # Bypass actual check

    assert require_internet_or_alert() is True


def test_require_internet_returns_false_when_offline(monkeypatch):
    """Test that require_internet_or_alert returns False when offline."""
    from src.utils.network import require_internet_or_alert
    import urllib.request

    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    monkeypatch.setenv("RC_NO_GUI_ERRORS", "1")  # Suppress GUI
    monkeypatch.delenv("RC_NO_NET_CHECK", raising=False)

    # Mock socket to fail
    def mock_create_connection(*args, **kwargs):
        raise OSError("Network unreachable")

    monkeypatch.setattr(socket, "create_connection", mock_create_connection)

    # Mock urllib.request.urlopen to raise URLError
    def mock_urlopen(*args, **kwargs):
        from urllib.error import URLError

        raise URLError("HTTP unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = require_internet_or_alert()
    assert result is False


def test_network_module_imports():
    """Test that network module can be imported."""
    try:
        import src.utils.network

        assert hasattr(src.utils.network, "check_internet_connectivity")
        assert hasattr(src.utils.network, "require_internet_or_alert")
    except Exception as e:
        pytest.fail(f"Failed to import src.utils.network: {e}")
