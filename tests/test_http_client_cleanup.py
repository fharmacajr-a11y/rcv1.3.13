# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários para close_http_client() / get_http_client() (Fase 7).

Estratégia de isolamento:
  - O módulo cria HTTPX_CLIENT e chama atexit.register() no import.
  - Usamos importlib.reload() com patchers ativos para controlar
    httpx.Client e atexit.register em cada teste sem depender do singleton
    real já instanciado pelo resto da suíte.
"""

from __future__ import annotations

import importlib
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch


# Módulo alvo — mantemos o caminho explícito para reload controlado.
_MODULE_PATH = "src.infra.supabase.http_client"


def _reload_module(mock_client_cls, mock_atexit_register):
    """Recarrega o módulo com httpx.Client e atexit.register patchados."""
    mod = sys.modules.get(_MODULE_PATH)
    with patch("httpx.Client", mock_client_cls), patch("atexit.register", mock_atexit_register):
        if mod is None:
            mod = importlib.import_module(_MODULE_PATH)
        else:
            mod = importlib.reload(mod)
    return mod


class TestAtexitRegistration(unittest.TestCase):
    """atexit.register deve ser chamado com close_http_client na carga do módulo."""

    def test_atexit_registered_on_import(self):
        mock_client_instance = MagicMock()
        mock_client_cls = MagicMock(return_value=mock_client_instance)
        mock_atexit_register = MagicMock()

        mod = _reload_module(mock_client_cls, mock_atexit_register)

        # atexit.register deve ter sido chamado exatamente uma vez com close_http_client
        mock_atexit_register.assert_called_once_with(mod.close_http_client)

    def test_atexit_registered_with_correct_callable(self):
        mock_client_instance = MagicMock()
        mock_client_cls = MagicMock(return_value=mock_client_instance)
        registered_fns = []

        def capture_register(fn):
            registered_fns.append(fn)

        mod = _reload_module(mock_client_cls, capture_register)

        self.assertEqual(len(registered_fns), 1)
        self.assertIs(registered_fns[0], mod.close_http_client)


class TestCloseHttpClient(unittest.TestCase):
    """close_http_client() deve chamar client.close() exatamente uma vez."""

    def setUp(self):
        # Criar cliente mock e recarregar módulo com patcher ativo
        self.mock_client_instance = MagicMock()
        mock_client_cls = MagicMock(return_value=self.mock_client_instance)
        mock_atexit_register = MagicMock()
        self.mod = _reload_module(mock_client_cls, mock_atexit_register)

    def test_close_calls_client_close(self):
        self.mod.close_http_client()
        self.mock_client_instance.close.assert_called_once()

    def test_close_is_idempotent_no_double_close(self):
        """Segunda chamada é no-op — close() chamado apenas uma vez."""
        self.mod.close_http_client()
        self.mod.close_http_client()
        self.mod.close_http_client()
        self.assertEqual(self.mock_client_instance.close.call_count, 1)

    def test_close_does_not_raise_when_client_close_raises(self):
        """Exceção dentro de client.close() não deve vazar."""
        self.mock_client_instance.close.side_effect = RuntimeError("socket dead")
        try:
            self.mod.close_http_client()
        except Exception as exc:
            self.fail(f"close_http_client() levantou exceção inesperada: {exc}")

    def test_close_sets_closed_flag(self):
        self.assertFalse(self.mod._client_closed)
        self.mod.close_http_client()
        self.assertTrue(self.mod._client_closed)

    def test_second_close_does_not_reset_flag(self):
        self.mod.close_http_client()
        self.mod.close_http_client()
        self.assertTrue(self.mod._client_closed)


class TestGetHttpClient(unittest.TestCase):
    """get_http_client() deve retornar o mesmo singleton que HTTPX_CLIENT."""

    def setUp(self):
        self.mock_client_instance = MagicMock()
        mock_client_cls = MagicMock(return_value=self.mock_client_instance)
        mock_atexit_register = MagicMock()
        self.mod = _reload_module(mock_client_cls, mock_atexit_register)

    def test_get_http_client_returns_singleton(self):
        client = self.mod.get_http_client()
        self.assertIs(client, self.mod.HTTPX_CLIENT)

    def test_get_http_client_same_as_mock(self):
        client = self.mod.get_http_client()
        self.assertIs(client, self.mock_client_instance)


class TestBackwardCompatibility(unittest.TestCase):
    """Símbolos públicos originais devem continuar acessíveis após reload."""

    def setUp(self):
        mock_client_cls = MagicMock(return_value=MagicMock())
        mock_atexit_register = MagicMock()
        self.mod = _reload_module(mock_client_cls, mock_atexit_register)

    def test_httpx_client_exists(self):
        self.assertTrue(hasattr(self.mod, "HTTPX_CLIENT"))

    def test_httpx_timeout_alias_exists(self):
        self.assertTrue(hasattr(self.mod, "HTTPX_TIMEOUT"))

    def test_httpx_timeout_light_exists(self):
        self.assertTrue(hasattr(self.mod, "HTTPX_TIMEOUT_LIGHT"))

    def test_httpx_timeout_heavy_exists(self):
        self.assertTrue(hasattr(self.mod, "HTTPX_TIMEOUT_HEAVY"))

    def test_close_http_client_in_all(self):
        self.assertIn("close_http_client", self.mod.__all__)

    def test_get_http_client_in_all(self):
        self.assertIn("get_http_client", self.mod.__all__)


class TestThreadSafety(unittest.TestCase):
    """close_http_client() deve ser segura sob chamadas concorrentes."""

    def setUp(self):
        self.mock_client_instance = MagicMock()
        mock_client_cls = MagicMock(return_value=self.mock_client_instance)
        mock_atexit_register = MagicMock()
        self.mod = _reload_module(mock_client_cls, mock_atexit_register)

    def test_concurrent_close_calls_close_once(self):
        """N threads chamando close_http_client() concorrentemente → close() 1× apenas."""
        barrier = threading.Barrier(10)
        errors: list = []

        def worker():
            try:
                barrier.wait(timeout=5)
                self.mod.close_http_client()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertFalse(errors, f"erros nas threads: {errors}")
        self.assertEqual(self.mock_client_instance.close.call_count, 1)


if __name__ == "__main__":
    unittest.main()
