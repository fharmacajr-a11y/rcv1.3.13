# -*- coding: utf-8 -*-
"""Tests for src.infra.http_client — PR21: coverage step 2.

Covers:
- Circuit: state transitions (initial, failures, trip, cooldown, reset)
- HttpClient: successful GET/POST, retry on failure, circuit breaker activation,
  cache fallback, config loading

No real network calls — requests.request is always mocked.
No real sleeps — time.sleep is always mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.infra.http_client import Circuit, HttpClient


# ===========================================================================
# Circuit (near-pure — only needs time.time mock)
# ===========================================================================
class TestCircuit:
    def test_initial_state_allows(self) -> None:
        c = Circuit()
        assert c.allow() is True

    def test_success_keeps_open(self) -> None:
        c = Circuit()
        c.report(ok=True)
        assert c.allow() is True
        assert c._fails == 0

    def test_four_failures_still_open(self) -> None:
        c = Circuit()
        for _ in range(4):
            c.report(ok=False)
        assert c.allow() is True  # trips at 5

    @patch("src.infra.http_client.time")
    def test_five_failures_trip(self, mock_time: MagicMock) -> None:
        mock_time.time.return_value = 1000.0
        c = Circuit()
        c._next_try = 0.0
        for _ in range(5):
            c.report(ok=False)
        # _next_try should be ~1000 + 300 = 1300
        assert c._next_try == pytest.approx(1300.0)
        mock_time.time.return_value = 1100.0
        assert c.allow() is False

    @patch("src.infra.http_client.time")
    def test_cooldown_expires(self, mock_time: MagicMock) -> None:
        mock_time.time.return_value = 1000.0
        c = Circuit()
        for _ in range(5):
            c.report(ok=False)
        # After 300s cooldown
        mock_time.time.return_value = 1301.0
        assert c.allow() is True

    @patch("src.infra.http_client.time")
    def test_success_resets_after_trip(self, mock_time: MagicMock) -> None:
        mock_time.time.return_value = 1000.0
        c = Circuit()
        for _ in range(5):
            c.report(ok=False)
        c.report(ok=True)
        assert c._fails == 0
        assert c._next_try == 0.0


# ===========================================================================
# HttpClient
# ===========================================================================
class TestHttpClient:
    """Tests for HttpClient with mocked requests and no real I/O."""

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_get_success(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"ok": True}
        mock_req.return_value = resp

        client = HttpClient(config_path="__nonexistent__")
        result = client.get("https://api.example.com/data")

        assert result["data"] == {"ok": True}
        assert result["from_cache"] is False
        mock_sleep.assert_not_called()

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_post_success(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        resp = MagicMock()
        resp.status_code = 201
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"id": 1}
        mock_req.return_value = resp

        client = HttpClient(config_path="__nonexistent__")
        result = client.post("https://api.example.com/items", json={"name": "x"})

        assert result["data"] == {"id": 1}
        mock_req.assert_called_once()

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_retry_then_success(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        fail = MagicMock()
        fail.status_code = 500
        fail.headers = {}

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.headers = {"Content-Type": "application/json"}
        ok_resp.json.return_value = {"recovered": True}

        mock_req.side_effect = [fail, ok_resp]

        client = HttpClient(config_path="__nonexistent__")
        result = client.get("https://api.example.com/flaky")

        assert result["data"] == {"recovered": True}
        assert mock_req.call_count == 2
        assert mock_sleep.call_count == 1  # one backoff between attempts

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_all_retries_exhausted_raises(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        mock_req.side_effect = ConnectionError("refused")

        client = HttpClient(config_path="__nonexistent__")
        with pytest.raises(ConnectionError, match="refused"):
            client.get("https://api.example.com/down")

        assert mock_req.call_count == 3  # default 3 attempts

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_cache_fallback_after_exhaustion(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        mock_req.side_effect = ConnectionError("refused")
        cache = MagicMock()
        cache.get.return_value = {"cached_data": 42}

        client = HttpClient(cache_store=cache, config_path="__nonexistent__")
        result = client.get("https://api.example.com/cached", cache_key="k1")

        assert result["data"] == {"cached_data": 42}
        assert result["from_cache"] is True

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_circuit_breaker_blocks_requests(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        # circuit.report(ok=False) is called once per _req (after all retries).
        # Need 5 failed _req calls (5 x 3 retries = 15 attempts) to trip the breaker.
        mock_req.side_effect = [ConnectionError("refused")] * 15

        client = HttpClient(config_path="__nonexistent__")

        for _ in range(5):
            with pytest.raises(ConnectionError):
                client.get("https://api.example.com/down")

        # Now circuit should be tripped — next call raises RuntimeError
        with pytest.raises(RuntimeError, match="Circuit breaker"):
            client.get("https://api.example.com/down")

    @patch("src.infra.http_client.time.sleep")
    @patch("src.infra.http_client.requests.request")
    def test_text_response(self, mock_req: MagicMock, mock_sleep: MagicMock) -> None:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "text/plain"}
        resp.text = "plain text body"
        mock_req.return_value = resp

        client = HttpClient(config_path="__nonexistent__")
        result = client.get("https://example.com/text")

        assert result["data"] == "plain text body"

    def test_config_from_nonexistent_file(self) -> None:
        """When config path doesn't exist, defaults are used."""
        client = HttpClient(config_path="__nonexistent__")
        assert client.config["retries"]["attempts"] == 3
