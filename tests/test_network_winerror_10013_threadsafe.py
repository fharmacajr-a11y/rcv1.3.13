# -*- coding: utf-8 -*-
"""Testes de thread-safety da flag _winerror_10013_logged em src/utils/network.py.

O padrão correto usa _WINERROR_10013_LOCK para garantir que o log de
WinError 10013 seja emitido exatamente UMA vez, mesmo sob alta concorrência.
"""

import threading
import unittest
from unittest.mock import patch

import src.utils.network as net_mod


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------


def _winerror_exc() -> OSError:
    """Cria OSError com winerror=10013."""
    exc = OSError("Access is denied")
    exc.winerror = 10013
    return exc


def _run_concurrent(n: int, fn, barrier: threading.Barrier) -> None:
    """Dispara n threads que chamam fn sincronizadas pela barrier."""

    def worker():
        barrier.wait()
        fn()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)


# ---------------------------------------------------------------------------
# Fixture base: reseta estado global a cada teste
# ---------------------------------------------------------------------------


class _NetBase(unittest.TestCase):
    def setUp(self):
        net_mod._winerror_10013_logged = False
        # Garante lock limpo para cada teste (sem waiters presos)
        net_mod._WINERROR_10013_LOCK = threading.Lock()

    def tearDown(self):
        net_mod._winerror_10013_logged = False


# ---------------------------------------------------------------------------
# Estrutura do módulo
# ---------------------------------------------------------------------------


class TestModuleStructure(_NetBase):
    def test_lock_existe(self):
        """_WINERROR_10013_LOCK deve existir e ser um Lock."""
        self.assertTrue(hasattr(net_mod, "_WINERROR_10013_LOCK"))

    def test_lock_eh_threading_lock(self):
        """_WINERROR_10013_LOCK deve ser instância de threading.Lock."""
        # type() de Lock() retorna _thread.lock; usamos acquire/release como duck-type
        lock = net_mod._WINERROR_10013_LOCK
        self.assertTrue(callable(getattr(lock, "acquire", None)))
        self.assertTrue(callable(getattr(lock, "release", None)))

    def test_flag_inicia_false(self):
        self.assertFalse(net_mod._winerror_10013_logged)


# ---------------------------------------------------------------------------
# Comportamento single-thread
# ---------------------------------------------------------------------------


class TestSingleThread(_NetBase):
    def test_uma_chamada_loga_uma_vez(self):
        calls: list[str] = []

        with (
            patch("socket.create_connection", side_effect=_winerror_exc()),
            patch.object(net_mod.logger, "debug", side_effect=lambda m, *a, **kw: calls.append(str(m))),
        ):
            net_mod._socket_check(0.01)

        matching = [m for m in calls if "10013" in m]
        self.assertEqual(len(matching), 1)

    def test_10_chamadas_sequenciais_logam_uma_vez(self):
        calls: list[str] = []

        with (
            patch("socket.create_connection", side_effect=_winerror_exc()),
            patch.object(net_mod.logger, "debug", side_effect=lambda m, *a, **kw: calls.append(str(m))),
        ):
            for _ in range(10):
                net_mod._socket_check(0.01)

        matching = [m for m in calls if "10013" in m]
        self.assertEqual(len(matching), 1)

    def test_flag_true_apos_log(self):
        with patch("socket.create_connection", side_effect=_winerror_exc()), patch.object(net_mod.logger, "debug"):
            net_mod._socket_check(0.01)

        self.assertTrue(net_mod._winerror_10013_logged)

    def test_oserror_generico_nao_seta_flag(self):
        """OSError sem winerror=10013 não deve alterar a flag."""
        with patch("socket.create_connection", side_effect=OSError("refused")), patch.object(net_mod.logger, "warning"):
            net_mod._socket_check(0.01)

        self.assertFalse(net_mod._winerror_10013_logged)

    def test_oserror_generico_nao_usa_lock(self):
        """Erros genéricos não alteram _winerror_10013_logged via lock."""
        with patch("socket.create_connection", side_effect=OSError("refused")), patch.object(net_mod.logger, "warning"):
            for _ in range(5):
                net_mod._socket_check(0.01)

        self.assertFalse(net_mod._winerror_10013_logged)


# ---------------------------------------------------------------------------
# Comportamento multi-thread — núcleo dos testes de thread-safety
# ---------------------------------------------------------------------------


class TestConcurrency(_NetBase):
    def _count_10013_logs(self, n_threads: int) -> int:
        """Retorna quantas vezes o log de WinError 10013 foi emitido com n threads."""
        calls: list[str] = []
        calls_lock = threading.Lock()
        barrier = threading.Barrier(n_threads)

        def fake_debug(msg, *args, **kwargs):
            with calls_lock:
                calls.append(str(msg))

        def task():
            net_mod._socket_check(0.01)

        with (
            patch("socket.create_connection", side_effect=_winerror_exc()),
            patch.object(net_mod.logger, "debug", side_effect=fake_debug),
        ):
            _run_concurrent(n_threads, task, barrier)

        return sum(1 for m in calls if "10013" in m)

    def test_20_threads_loga_no_maximo_uma_vez(self):
        count = self._count_10013_logs(20)
        self.assertLessEqual(count, 1, f"Log emitido {count}x com 20 threads (esperado ≤ 1)")

    def test_20_threads_loga_pelo_menos_uma_vez(self):
        count = self._count_10013_logs(20)
        self.assertGreaterEqual(count, 1, "Log WinError 10013 nunca emitido com 20 threads")

    def test_20_threads_loga_exatamente_uma_vez(self):
        count = self._count_10013_logs(20)
        self.assertEqual(count, 1, f"Log emitido {count}x com 20 threads (esperado exatamente 1)")

    def test_50_threads_loga_exatamente_uma_vez(self):
        count = self._count_10013_logs(50)
        self.assertEqual(count, 1, f"Log emitido {count}x com 50 threads (esperado exatamente 1)")

    def test_flag_true_apos_concorrencia(self):
        """Após disparo concorrente, a flag deve ser True."""
        barrier = threading.Barrier(20)

        with patch("socket.create_connection", side_effect=_winerror_exc()), patch.object(net_mod.logger, "debug"):
            _run_concurrent(20, lambda: net_mod._socket_check(0.01), barrier)

        self.assertTrue(net_mod._winerror_10013_logged)

    def test_reset_e_nova_rodada_loga_novamente(self):
        """Após reset da flag, uma nova rodada deve logar 1 vez novamente."""
        barrier = threading.Barrier(20)

        for ciclo in range(2):
            # Reseta para simular reinício
            net_mod._winerror_10013_logged = False
            calls: list[str] = []
            calls_lock = threading.Lock()

            def fake_debug(msg, *args, **kwargs):
                with calls_lock:
                    calls.append(str(msg))

            with (
                patch("socket.create_connection", side_effect=_winerror_exc()),
                patch.object(net_mod.logger, "debug", side_effect=fake_debug),
            ):
                _run_concurrent(20, lambda: net_mod._socket_check(0.01), barrier)

            matching = [m for m in calls if "10013" in m]
            self.assertEqual(len(matching), 1, f"Ciclo {ciclo}: esperado 1 log, obtido {len(matching)}")
            barrier = threading.Barrier(20)  # nova barrier para próxima rodada

    def test_log_fora_do_lock(self):
        """Verifica que o logger.debug é chamado FORA do lock (lock liberado antes do log).

        Estratégia: substitui logger.debug por uma função que testa se
        o lock pode ser adquirido imediatamente — se estiver livre, o log
        está sendo emitido fora do lock.
        """
        lock_was_free_during_log: list[bool] = []

        def fake_debug(msg, *args, **kwargs):
            if "10013" in str(msg):
                # Se o lock estiver livre, conseguimos adquirir sem bloquear
                acquired = net_mod._WINERROR_10013_LOCK.acquire(blocking=False)
                lock_was_free_during_log.append(acquired)
                if acquired:
                    net_mod._WINERROR_10013_LOCK.release()

        with (
            patch("socket.create_connection", side_effect=_winerror_exc()),
            patch.object(net_mod.logger, "debug", side_effect=fake_debug),
        ):
            net_mod._socket_check(0.01)

        self.assertTrue(
            any(lock_was_free_during_log),
            "O lock parece estar sendo mantido durante o logger.debug (deveria estar livre)",
        )


if __name__ == "__main__":
    unittest.main()
