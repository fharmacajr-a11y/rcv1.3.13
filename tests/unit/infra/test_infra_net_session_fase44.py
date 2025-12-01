# tests/test_infra_net_session_fase44.py
"""
Testes para infra/net_session.py (COV-INFRA-REDE).
Cobrem TimeoutHTTPAdapter e make_session com timeout/retry.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from infra import net_session


def test_timeout_http_adapter_sets_default_timeout(monkeypatch):
    sentinel = object()
    recorded = {}

    def fake_send(self, request, **kwargs):
        recorded["timeout"] = kwargs.get("timeout")
        return sentinel

    monkeypatch.setattr(HTTPAdapter, "send", fake_send, raising=True)
    adapter = net_session.TimeoutHTTPAdapter(timeout=("connect", "read"))

    result = adapter.send(request=MagicMock())

    assert result is sentinel
    assert recorded["timeout"] == ("connect", "read")


def test_timeout_http_adapter_preserves_custom_timeout(monkeypatch):
    recorded = {}

    def fake_send(self, request, **kwargs):
        recorded["timeout"] = kwargs.get("timeout")
        return "ok"

    monkeypatch.setattr(HTTPAdapter, "send", fake_send, raising=True)
    adapter = net_session.TimeoutHTTPAdapter(timeout=(1, 2))

    result = adapter.send(request=MagicMock(), timeout=999)

    assert result == "ok"
    assert recorded["timeout"] == 999  # custom valor n�o sobrescreve


def test_make_session_mounts_adapters():
    session = net_session.make_session()

    adapter_https = session.get_adapter("https://example.com")
    adapter_http = session.get_adapter("http://example.com")

    assert isinstance(adapter_https, net_session.TimeoutHTTPAdapter)
    assert isinstance(adapter_http, net_session.TimeoutHTTPAdapter)
    assert adapter_https._timeout == net_session.DEFAULT_TIMEOUT
    assert adapter_http._timeout == net_session.DEFAULT_TIMEOUT

    retries: Retry = adapter_https.max_retries
    assert retries.total == 3
    assert retries.backoff_factor == 0.5
    assert set(retries.allowed_methods) == set(Retry.DEFAULT_ALLOWED_METHODS)
    for status in (413, 429, 500, 502, 503, 504):
        assert status in retries.status_forcelist
