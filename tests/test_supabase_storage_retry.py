# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários para retry em _upload() — Fase 9.

Estratégia:
  - Patchar client.storage.from_(...).upload para simular falhas.
  - Patchar src.adapters.storage.supabase_storage._sleep para velocidade.
  - Patchar src.adapters.storage.supabase_storage._UPLOAD_MAX_ATTEMPTS para controlar ciclos.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import src.adapters.storage.supabase_storage as mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(side_effects: list):
    """Cria mock de client com .storage.from_(...).upload() com efeitos colaterais."""
    upload_mock = MagicMock(side_effect=side_effects)
    bucket_ref = MagicMock()
    bucket_ref.upload = upload_mock
    storage = MagicMock()
    storage.from_ = MagicMock(return_value=bucket_ref)
    client = MagicMock()
    client.storage = storage
    return client, upload_mock


def _run_upload(client, side_effects, data=b"bytes", max_attempts=3):
    """Executa _upload com sleep e _UPLOAD_MAX_ATTEMPTS patchados."""
    with patch.object(mod, "_sleep"), patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", max_attempts):
        client, upload_mock = _make_client(side_effects)
        return mod._upload(
            client=client,
            bucket="bucket",
            source=data,
            remote_key="org/1/file.pdf",
            content_type="application/pdf",
        ), upload_mock


# ---------------------------------------------------------------------------
# (a) Falha transitória 2x → sucesso na 3ª → upload chamado 3 vezes
# ---------------------------------------------------------------------------


class TestRetryTransientSuccess(unittest.TestCase):
    def test_two_transient_failures_then_success(self):
        """Falha 2× com erro transitório → sucesso na 3ª tentativa."""
        transient = ConnectionError("connection refused")
        side_effects = [transient, transient, "ok"]

        sleep_calls = []

        def fake_sleep(secs):
            sleep_calls.append(secs)

        with patch.object(mod, "_sleep", side_effect=fake_sleep), patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3):
            client, upload_mock = _make_client(side_effects)
            result = mod._upload(
                client=client,
                bucket="bucket",
                source=b"data",
                remote_key="a/b/c.pdf",
                content_type="application/pdf",
            )

        self.assertEqual(upload_mock.call_count, 3)
        self.assertEqual(len(sleep_calls), 2, "deve dormir entre as tentativas")
        # O retorno "ok" não tem .get(), então result_path = key
        self.assertIsNotNone(result)

    def test_one_transient_failure_then_success(self):
        timeout_exc = TimeoutError("read timeout")
        side_effects = [timeout_exc, {"data": {"path": "org/1/file.pdf"}}]

        with patch.object(mod, "_sleep"), patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3):
            client, upload_mock = _make_client(side_effects)
            result = mod._upload(
                client=client,
                bucket="bucket",
                source=b"data",
                remote_key="org/1/file.pdf",
                content_type="application/pdf",
            )

        self.assertEqual(upload_mock.call_count, 2)
        self.assertEqual(result, "org/1/file.pdf")

    def test_sleep_not_called_on_first_success(self):
        """Sem falha → sleep nunca é chamado."""
        sleep_tracker = []
        with (
            patch.object(mod, "_sleep", side_effect=lambda s: sleep_tracker.append(s)),
            patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3),
        ):
            client, _ = _make_client(["ok"])
            mod._upload(
                client=client,
                bucket="bucket",
                source=b"data",
                remote_key="a/b.pdf",
                content_type=None,
            )

        self.assertEqual(sleep_tracker, [])


# ---------------------------------------------------------------------------
# (b) Falha sempre → N tentativas, relança última exceção
# ---------------------------------------------------------------------------


class TestRetryExhausted(unittest.TestCase):
    def test_all_attempts_fail_raises_last_exception(self):
        """Esgotados todas as tentativas → relança última exceção transitória."""
        exc = OSError("network down")
        side_effects = [exc, exc, exc]

        with patch.object(mod, "_sleep"), patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3):
            client, upload_mock = _make_client(side_effects)
            with self.assertRaises(OSError) as ctx:
                mod._upload(
                    client=client,
                    bucket="bucket",
                    source=b"data",
                    remote_key="a/b.pdf",
                    content_type=None,
                )

        self.assertEqual(upload_mock.call_count, 3)
        self.assertIs(ctx.exception, exc)

    def test_attempts_count_matches_max_attempts(self):
        server_err = RuntimeError("500 Internal Server Error")
        side_effects = [server_err] * 5

        with patch.object(mod, "_sleep"), patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 5):
            client, upload_mock = _make_client(side_effects)
            with self.assertRaises(RuntimeError):
                mod._upload(
                    client=client,
                    bucket="bucket",
                    source=b"d",
                    remote_key="x.pdf",
                    content_type=None,
                )

        self.assertEqual(upload_mock.call_count, 5)

    def test_sleep_called_between_attempts_not_after_last(self):
        """sleep é chamado N-1 vezes (não após a última tentativa)."""
        exc = ConnectionError("conn error")
        side_effects = [exc, exc, exc]
        sleep_calls = []

        with (
            patch.object(mod, "_sleep", side_effect=lambda s: sleep_calls.append(s)),
            patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3),
        ):
            client, _ = _make_client(side_effects)
            with self.assertRaises(ConnectionError):
                mod._upload(
                    client=client,
                    bucket="bucket",
                    source=b"d",
                    remote_key="x.pdf",
                    content_type=None,
                )

        self.assertEqual(len(sleep_calls), 2, "sleep deve ser chamado N-1 vezes")


# ---------------------------------------------------------------------------
# (c) Erro não-transitório → sem retry (1 chamada)
# ---------------------------------------------------------------------------


class TestNoRetryForPermanentErrors(unittest.TestCase):
    def _assert_no_retry(self, exc, **kwargs):
        side_effects = [exc]
        with patch.object(mod, "_sleep") as sleep_mock, patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3):
            client, upload_mock = _make_client(side_effects)
            with self.assertRaises(type(exc)):
                mod._upload(
                    client=client,
                    bucket="bucket",
                    source=b"data",
                    remote_key="a.pdf",
                    content_type=None,
                )
        self.assertEqual(upload_mock.call_count, 1, "não deve tentar mais de uma vez")
        sleep_mock.assert_not_called()

    def test_400_no_retry(self):
        self._assert_no_retry(ValueError("400 Bad Request"))

    def test_401_no_retry(self):
        self._assert_no_retry(PermissionError("401 Unauthorized"))

    def test_403_no_retry(self):
        self._assert_no_retry(RuntimeError("403 Forbidden"))

    def test_404_no_retry(self):
        self._assert_no_retry(RuntimeError("404 Not Found"))

    def test_duplicate_409_no_retry(self):
        """409 duplicado não deve ter retry."""
        exc = RuntimeError("duplicate key value — statuscode: 409")
        side_effects = [exc]
        with patch.object(mod, "_sleep") as sleep_mock, patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3):
            client, upload_mock = _make_client(side_effects)
            with self.assertRaises(RuntimeError):
                mod._upload(
                    client=client,
                    bucket="bucket",
                    source=b"d",
                    remote_key="a.pdf",
                    content_type=None,
                )
        self.assertEqual(upload_mock.call_count, 1)
        sleep_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Backoff cresce com as tentativas
# ---------------------------------------------------------------------------


class TestBackoffBehavior(unittest.TestCase):
    def test_backoff_increases_between_attempts(self):
        exc = ConnectionError("transient")
        side_effects = [exc, exc, exc, exc]
        sleep_calls = []

        with (
            patch.object(mod, "_sleep", side_effect=lambda s: sleep_calls.append(s)),
            patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 4),
            patch("random.uniform", return_value=0.0),
        ):  # zera jitter
            client, _ = _make_client(side_effects)
            with self.assertRaises(ConnectionError):
                mod._upload(
                    client=client,
                    bucket="b",
                    source=b"d",
                    remote_key="x.pdf",
                    content_type=None,
                )

        self.assertEqual(len(sleep_calls), 3, "3 sleeps para 4 tentativas")
        # backoff: 0.4, 0.8, 1.6 (base 0.4, exp 2**attempt-1)
        for i in range(len(sleep_calls) - 1):
            self.assertLessEqual(
                sleep_calls[i], sleep_calls[i + 1], "delays devem crescer (ou igualar) a cada tentativa"
            )


# ---------------------------------------------------------------------------
# 429 rate-limit → deve ter retry
# ---------------------------------------------------------------------------


class TestRateLimitRetry(unittest.TestCase):
    def test_429_is_transient(self):
        exc = RuntimeError("429 Too Many Requests")
        self.assertTrue(mod._is_transient_exc(exc))

    def test_429_triggers_retry(self):
        rate_exc = RuntimeError("429 Too Many Requests")
        side_effects = [rate_exc, "ok"]

        with patch.object(mod, "_sleep"), patch.object(mod, "_UPLOAD_MAX_ATTEMPTS", 3):
            client, upload_mock = _make_client(side_effects)
            mod._upload(
                client=client,
                bucket="b",
                source=b"d",
                remote_key="f.pdf",
                content_type=None,
            )

        self.assertEqual(upload_mock.call_count, 2)


# ---------------------------------------------------------------------------
# _is_transient_exc diretamente
# ---------------------------------------------------------------------------


class TestIsTransientExc(unittest.TestCase):
    def test_connection_error_transient(self):
        self.assertTrue(mod._is_transient_exc(ConnectionError("refused")))

    def test_timeout_error_transient(self):
        self.assertTrue(mod._is_transient_exc(TimeoutError("timed out")))

    def test_os_error_transient(self):
        self.assertTrue(mod._is_transient_exc(OSError("network unreachable")))

    def test_500_transient(self):
        self.assertTrue(mod._is_transient_exc(RuntimeError("500 Internal Server Error")))

    def test_503_transient(self):
        self.assertTrue(mod._is_transient_exc(RuntimeError("503 Service Unavailable")))

    def test_400_not_transient(self):
        self.assertFalse(mod._is_transient_exc(RuntimeError("400 Bad Request")))

    def test_403_not_transient(self):
        self.assertFalse(mod._is_transient_exc(RuntimeError("403 Forbidden")))

    def test_404_not_transient(self):
        self.assertFalse(mod._is_transient_exc(RuntimeError("404 Not Found")))

    def test_duplicate_not_transient(self):
        self.assertFalse(mod._is_transient_exc(RuntimeError("duplicate key — statuscode: 409")))

    def test_generic_value_error_not_transient(self):
        self.assertFalse(mod._is_transient_exc(ValueError("invalid argument")))


if __name__ == "__main__":
    unittest.main()
