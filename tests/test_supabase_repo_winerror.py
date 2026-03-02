# -*- coding: utf-8 -*-
"""Testes para lógica WinError 10035 em src/db/supabase_repo.py."""
import unittest
from unittest.mock import patch

from src.db.supabase_repo import with_retries


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


@patch("src.db.supabase_repo.time.sleep", return_value=None)
class TestWithRetriesWinError(unittest.TestCase):
    """Valida que WinError 10035 é transitório (retry) e outros OSError levantam imediatamente."""

    def test_winerror_10035_e_transitorio_permite_retry(self, _sleep):
        """OSError com winerror=10035 deve ser retentado (fn chamado 3 vezes com tries=3)."""
        counter = {"calls": 0}

        def fn_always_10035():
            counter["calls"] += 1
            raise _make_oserror(winerror=10035)

        with self.assertRaises(OSError):
            with_retries(fn_always_10035, tries=3, base_delay=0.0)

        # transitório: todas as 3 tentativas devem ocorrer
        self.assertEqual(counter["calls"], 3)

    def test_oserror_nao_transitorio_levanta_imediatamente(self, _sleep):
        """OSError com outro winerror deve ser re-levantado na 1ª tentativa (sem retry)."""
        counter = {"calls": 0}

        def fn_non_transient():
            counter["calls"] += 1
            raise _make_oserror(winerror=99)  # código não-transitório

        with self.assertRaises(OSError):
            with_retries(fn_non_transient, tries=3, base_delay=0.0)

        # não-transitório: fn chamado apenas 1 vez
        self.assertEqual(counter["calls"], 1)

    def test_oserror_sem_winerror_levanta_imediatamente(self, _sleep):
        """OSError com winerror=None deve ser re-levantado imediatamente."""
        counter = {"calls": 0}

        def fn_plain_oserror():
            counter["calls"] += 1
            raise _make_oserror(winerror=None)

        with self.assertRaises(OSError):
            with_retries(fn_plain_oserror, tries=3, base_delay=0.0)

        self.assertEqual(counter["calls"], 1)

    def test_sucesso_na_primeira_tentativa(self, _sleep):
        """Função bem-sucedida não deve ser chamada mais de 1 vez."""
        counter = {"calls": 0}

        def fn_success():
            counter["calls"] += 1
            return "ok"

        result = with_retries(fn_success, tries=3, base_delay=0.0)
        self.assertEqual(result, "ok")
        self.assertEqual(counter["calls"], 1)

    def test_sucesso_apos_winerror_10035(self, _sleep):
        """Função que falha com 10035 na 1ª tentativa mas sucede na 2ª retorna o valor."""
        counter = {"calls": 0}

        def fn_retry_then_success():
            counter["calls"] += 1
            if counter["calls"] < 2:
                raise _make_oserror(winerror=10035)
            return "recovered"

        result = with_retries(fn_retry_then_success, tries=3, base_delay=0.0)
        self.assertEqual(result, "recovered")
        self.assertEqual(counter["calls"], 2)


if __name__ == "__main__":
    unittest.main()

