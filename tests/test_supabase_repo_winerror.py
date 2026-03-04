# -*- coding: utf-8 -*-
"""Testes para lógica WinError 10035 via retry_policy (migrado de with_retries).

PR-10: with_retries removido de supabase_repo. Retry agora vive em
src.infra.retry_policy.retry_call. Os testes validam o mesmo comportamento.
"""

import unittest

from src.infra.retry_policy import retry_call


class _FakeWinOSError(OSError):
    """OSError com winerror tipado como int (evita reportAttributeAccessIssue do Pylance)."""

    def __init__(self, winerror: int) -> None:
        super().__init__(f"fake os error [winerror {winerror}]")
        self.winerror: int = winerror


class _FakePlainOSError(OSError):
    """OSError sem winerror (winerror=None é o padrão do OSError)."""


def _make_oserror(winerror: int | None = None) -> OSError:
    """Cria OSError com atributo winerror controlado."""
    if winerror is None:
        return _FakePlainOSError("fake os error")
    return _FakeWinOSError(winerror)


def _noop_sleep(_: float) -> None:
    """sleep_fn injetável que não espera."""


class TestRetryCallWinError(unittest.TestCase):
    """Valida que WinError 10035 é transitório (retry) e outros OSError levantam imediatamente."""

    def test_winerror_10035_e_transitorio_permite_retry(self) -> None:
        """OSError com winerror=10035 deve ser retentado (fn chamado 3 vezes com max_attempts=3)."""
        counter = {"calls": 0}

        def fn_always_10035() -> None:
            counter["calls"] += 1
            raise _make_oserror(winerror=10035)

        with self.assertRaises(OSError):
            retry_call(fn_always_10035, max_attempts=3, sleep_fn=_noop_sleep)

        # transitório: todas as 3 tentativas devem ocorrer
        self.assertEqual(counter["calls"], 3)

    def test_oserror_nao_transitorio_levanta_imediatamente(self) -> None:
        """OSError com outro winerror deve ser re-levantado na 1ª tentativa (sem retry)."""
        counter = {"calls": 0}

        def fn_non_transient() -> None:
            counter["calls"] += 1
            raise _make_oserror(winerror=99)  # código não-transitório

        with self.assertRaises(OSError):
            retry_call(fn_non_transient, max_attempts=3, sleep_fn=_noop_sleep)

        # não-transitório: fn chamado apenas 1 vez
        self.assertEqual(counter["calls"], 1)

    def test_oserror_sem_winerror_levanta_imediatamente(self) -> None:
        """OSError com winerror=None deve ser re-levantado imediatamente."""
        counter = {"calls": 0}

        def fn_plain_oserror() -> None:
            counter["calls"] += 1
            raise _make_oserror(winerror=None)

        with self.assertRaises(OSError):
            retry_call(fn_plain_oserror, max_attempts=3, sleep_fn=_noop_sleep)

        self.assertEqual(counter["calls"], 1)

    def test_sucesso_na_primeira_tentativa(self) -> None:
        """Função bem-sucedida não deve ser chamada mais de 1 vez."""
        counter = {"calls": 0}

        def fn_success() -> str:
            counter["calls"] += 1
            return "ok"

        result = retry_call(fn_success, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(result, "ok")
        self.assertEqual(counter["calls"], 1)

    def test_sucesso_apos_winerror_10035(self) -> None:
        """Função que falha com 10035 na 1ª tentativa mas sucede na 2ª retorna o valor."""
        counter = {"calls": 0}

        def fn_retry_then_success() -> str:
            counter["calls"] += 1
            if counter["calls"] < 2:
                raise _make_oserror(winerror=10035)
            return "recovered"

        result = retry_call(fn_retry_then_success, max_attempts=3, sleep_fn=_noop_sleep)
        self.assertEqual(result, "recovered")
        self.assertEqual(counter["calls"], 2)


if __name__ == "__main__":
    unittest.main()
