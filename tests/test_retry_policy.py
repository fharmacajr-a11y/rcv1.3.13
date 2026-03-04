# -*- coding: utf-8 -*-
"""Testes para src.infra.retry_policy — PR-10: núcleo unificado de retry.

Coberturas:
- retry_call: sucesso na 1ª, sucesso após falhas, exaustão, não-transitório
- is_transient_error: WinError 10035, OSError genérico, httpx, 5xx, 429
- calculate_delay: backoff exponencial com cap e jitter
- on_retry callback
- sleep_fn injeção (sem sleep real)
"""

from __future__ import annotations

import socket
import unittest
from unittest.mock import MagicMock

from src.infra.retry_policy import (
    calculate_delay,
    is_transient_error,
    retry_call,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _FakeWinOSError(OSError):
    """OSError com winerror controlável."""

    def __init__(self, winerror: int) -> None:
        super().__init__(f"fake win os error [{winerror}]")
        self.winerror: int = winerror


def _noop_sleep(_: float) -> None:
    """sleep_fn injetável que não espera."""


# ---------------------------------------------------------------------------
# is_transient_error
# ---------------------------------------------------------------------------
class TestIsTransientError(unittest.TestCase):
    """Testa classificação de erros transitórios."""

    def test_winerror_10035_transitorio(self) -> None:
        self.assertTrue(is_transient_error(_FakeWinOSError(10035)))

    def test_winerror_outro_nao_transitorio(self) -> None:
        self.assertFalse(is_transient_error(_FakeWinOSError(99)))

    def test_oserror_sem_winerror_nao_transitorio(self) -> None:
        self.assertFalse(is_transient_error(OSError("permissão negada")))

    def test_timeout_error_transitorio(self) -> None:
        self.assertTrue(is_transient_error(TimeoutError("timed out")))

    def test_connection_error_transitorio(self) -> None:
        self.assertTrue(is_transient_error(ConnectionError("reset")))

    def test_socket_timeout_transitorio(self) -> None:
        self.assertTrue(is_transient_error(socket.timeout("timed out")))

    def test_5xx_na_mensagem_transitorio(self) -> None:
        self.assertTrue(is_transient_error(RuntimeError("502 Bad Gateway")))
        self.assertTrue(is_transient_error(RuntimeError("HTTP 503")))

    def test_429_na_mensagem_transitorio(self) -> None:
        self.assertTrue(is_transient_error(RuntimeError("429 Too Many Requests")))

    def test_404_nao_transitorio(self) -> None:
        self.assertFalse(is_transient_error(RuntimeError("HTTP 404 Not Found")))

    def test_value_error_nao_transitorio(self) -> None:
        self.assertFalse(is_transient_error(ValueError("campo inválido")))

    def test_runtime_error_generico_nao_transitorio(self) -> None:
        self.assertFalse(is_transient_error(RuntimeError("falha de lógica")))

    def test_bad_gateway_texto_transitorio(self) -> None:
        self.assertTrue(is_transient_error(Exception("server returned bad gateway")))


# ---------------------------------------------------------------------------
# calculate_delay
# ---------------------------------------------------------------------------
class TestCalculateDelay(unittest.TestCase):
    """Testa cálculo de delay com backoff exponencial + cap + jitter."""

    def test_delay_attempt_1(self) -> None:
        # base_delay=0.4, attempt=1 → 0.4 * 2^0 = 0.4 + jitter
        delay = calculate_delay(1, base_delay=0.4, max_delay=8.0, jitter=0.0)
        self.assertAlmostEqual(delay, 0.4, places=3)

    def test_delay_attempt_2(self) -> None:
        delay = calculate_delay(2, base_delay=0.4, max_delay=8.0, jitter=0.0)
        self.assertAlmostEqual(delay, 0.8, places=3)

    def test_delay_cap(self) -> None:
        # attempt=10 → 0.4 * 2^9 = 204.8 → cap a 8.0
        delay = calculate_delay(10, base_delay=0.4, max_delay=8.0, jitter=0.0)
        self.assertAlmostEqual(delay, 8.0, places=3)

    def test_jitter_nao_negativo(self) -> None:
        for _ in range(50):
            delay = calculate_delay(1, base_delay=0.4, max_delay=8.0, jitter=0.15)
            self.assertGreaterEqual(delay, 0.4)
            self.assertLess(delay, 0.4 + 0.15 + 0.001)

    def test_jitter_zero(self) -> None:
        delay = calculate_delay(1, base_delay=0.4, max_delay=8.0, jitter=0.0)
        self.assertAlmostEqual(delay, 0.4, places=6)


# ---------------------------------------------------------------------------
# retry_call
# ---------------------------------------------------------------------------
class TestRetryCall(unittest.TestCase):
    """Testa loop de retry unificado."""

    def test_sucesso_primeira_tentativa(self) -> None:
        result = retry_call(lambda: 42, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(result, 42)

    def test_sucesso_apos_falha_transitoria(self) -> None:
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("reset")
            return "ok"

        result = retry_call(flaky, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_exausta_tentativas_levanta(self) -> None:
        def always_fail() -> None:
            raise ConnectionError("always fails")

        with self.assertRaises(ConnectionError):
            retry_call(always_fail, max_attempts=3, sleep_fn=_noop_sleep)

    def test_erro_nao_transitorio_nao_retenta(self) -> None:
        calls = {"n": 0}

        def business_error() -> None:
            calls["n"] += 1
            raise ValueError("campo inválido")

        with self.assertRaises(ValueError):
            retry_call(business_error, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(calls["n"], 1)

    def test_winerror_10035_retenta(self) -> None:
        calls = {"n": 0}

        def win10035() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise _FakeWinOSError(10035)
            return "recovered"

        result = retry_call(win10035, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(result, "recovered")
        self.assertEqual(calls["n"], 2)

    def test_oserror_sem_winerror_nao_retenta(self) -> None:
        calls = {"n": 0}

        def plain_os() -> None:
            calls["n"] += 1
            raise OSError("permissão negada")

        with self.assertRaises(OSError):
            retry_call(plain_os, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(calls["n"], 1)

    def test_oserror_winerror_outro_nao_retenta(self) -> None:
        calls = {"n": 0}

        def win99() -> None:
            calls["n"] += 1
            raise _FakeWinOSError(99)

        with self.assertRaises(OSError):
            retry_call(win99, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(calls["n"], 1)

    def test_5xx_na_mensagem_retenta(self) -> None:
        calls = {"n": 0}

        def server_err() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("502 Bad Gateway")
            return "ok"

        result = retry_call(server_err, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_on_retry_callback(self) -> None:
        cb = MagicMock()
        calls = {"n": 0}

        def fail_once() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise ConnectionError("first fail")
            return "ok"

        result = retry_call(fail_once, max_attempts=3, sleep_fn=_noop_sleep, on_retry=cb)
        self.assertEqual(result, "ok")
        self.assertEqual(cb.call_count, 1)
        args = cb.call_args[0]
        self.assertEqual(args[0], 1)  # attempt
        self.assertIsInstance(args[1], ConnectionError)
        self.assertGreater(args[2], 0)  # delay > 0

    def test_sleep_fn_chamado_entre_retries(self) -> None:
        sleep_mock = MagicMock()
        calls = {"n": 0}

        def fail_twice() -> str:
            calls["n"] += 1
            if calls["n"] <= 2:
                raise ConnectionError("fail")
            return "done"

        retry_call(fail_twice, max_attempts=3, sleep_fn=sleep_mock)
        self.assertEqual(sleep_mock.call_count, 2)
        # each call receives a float > 0
        for c in sleep_mock.call_args_list:
            self.assertGreater(c[0][0], 0)

    def test_args_e_kwargs_repassados(self) -> None:
        def add(a: int, b: int, offset: int = 0) -> int:
            return a + b + offset

        result = retry_call(add, 2, 3, offset=10, max_attempts=1, sleep_fn=_noop_sleep)
        self.assertEqual(result, 15)

    def test_classificador_customizado(self) -> None:
        """Usa is_transient customizado para retryar ValueError."""
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("retry this")
            return "ok"

        result = retry_call(
            flaky,
            max_attempts=3,
            sleep_fn=_noop_sleep,
            is_transient=lambda exc: isinstance(exc, ValueError),
        )
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)

    def test_max_attempts_1_sem_retry(self) -> None:
        """max_attempts=1 → sem retry (falha na 1ª tentativa → propaga)."""
        with self.assertRaises(ConnectionError):
            retry_call(
                lambda: (_ for _ in ()).throw(ConnectionError("fail")),
                max_attempts=1,
                sleep_fn=_noop_sleep,
            )

    def test_on_retry_callback_erro_engolido(self) -> None:
        """Erro no callback on_retry não interrompe o loop de retry."""
        calls = {"n": 0}

        def fail_once() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise ConnectionError("fail")
            return "ok"

        def bad_callback(attempt: int, exc: Exception, delay: float) -> None:
            raise RuntimeError("callback crash")

        result = retry_call(fail_once, max_attempts=3, sleep_fn=_noop_sleep, on_retry=bad_callback)
        self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()
