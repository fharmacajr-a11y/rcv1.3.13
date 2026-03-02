# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários para _ProgressPump (Fase 6 — race do progress/result_queue).

Estratégia: _ProgressPump não depende de Tk; injetamos after_fn / close_fn
como callables simples.  Todos os cenários rodam sem display real.
"""

from __future__ import annotations

import queue
import threading
import unittest

from src.modules.uploads.uploader_supabase import _ProgressPump


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pump(
    rq: "queue.Queue",
    done_event: threading.Event,
    after_calls: list,
    closed: list,
    poll_ms: int = 0,
    after_cancel_fn=None,
) -> _ProgressPump:
    def after_fn(ms, cb):
        after_calls.append((ms, cb))
        return object()

    def close_fn():
        closed.append(True)

    return _ProgressPump(
        rq,
        done_event,
        after_fn=after_fn,
        close_fn=close_fn,
        after_cancel_fn=after_cancel_fn,
        poll_ms=poll_ms,
    )


def _drain(pump: _ProgressPump, after_calls: list, max_iter: int = 50) -> None:
    """Executa ticks até pump._finalized ou esgotar iterações."""
    for _ in range(max_iter):
        if pump._finalized:
            break
        if after_calls:
            _, cb = after_calls.pop(0)
            cb()


# ---------------------------------------------------------------------------
# Cenário (a): fila vazia + done_event=False => NÃO finaliza (reagenda)
# ---------------------------------------------------------------------------


class TestNotFinalizeWhenQueueEmptyAndNotDone(unittest.TestCase):
    """Diálogo nunca deve fechar apenas porque a fila está vazia."""

    def test_reschedule_on_empty_queue_not_done(self):
        """Tick com fila vazia + done_event off → reagenda, não fecha."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        after_calls.clear()  # remove o after do start()
        pump._tick()  # executa manualmente

        self.assertEqual(len(after_calls), 1, "deve reagendar exatamente uma vez")
        self.assertFalse(closed, "não deve fechar o diálogo")
        self.assertFalse(pump._finalized)

    def test_multiple_empty_ticks_never_close(self):
        """N ticks consecutivos sem resultado e sem done_event nunca fecham."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        # Simula 5 ticks onde a fila está vazia e worker ainda vivo
        for _ in range(5):
            after_calls.clear()
            pump._tick()
            self.assertFalse(closed)

        self.assertFalse(pump._finalized)


# ---------------------------------------------------------------------------
# Cenário (b): worker coloca resultado + seta done_event => finaliza
# ---------------------------------------------------------------------------


class TestSuccessFlow(unittest.TestCase):
    """Worker envia resultado e seta done_event → pump fecha corretamente."""

    def test_success_result_stored_and_close_called(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        rq.put(("success", 5, []))
        done_event.set()

        _drain(pump, after_calls)

        self.assertEqual(pump.result, (5, []))
        self.assertIsNone(pump.error)
        self.assertEqual(len(closed), 1, "close deve ser chamado exatamente uma vez")
        self.assertTrue(pump._finalized)

    def test_success_with_failures_list(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        failures = [("item.pdf", ValueError("tamanho inválido"))]
        rq.put(("success", 2, failures))
        done_event.set()

        _drain(pump, after_calls)

        self.assertEqual(pump.result, (2, failures))
        self.assertIsNone(pump.error)
        self.assertTrue(closed)

    def test_done_event_only_set_before_queue_put(self):
        """done_event setado *antes* da mensagem chegar → ainda finaliza."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        done_event.set()  # sinaliza antes de colocar na fila
        rq.put(("success", 1, []))

        _drain(pump, after_calls)

        self.assertEqual(pump.result, (1, []))
        self.assertTrue(pump._finalized)


# ---------------------------------------------------------------------------
# Cenário (c): erro enviado => registra erro, não fecha silenciosamente
# ---------------------------------------------------------------------------


class TestErrorFlow(unittest.TestCase):
    """Erro do worker deve ser armazenado e o diálogo fechado."""

    def test_error_stored_and_close_called(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        exc = RuntimeError("connection refused")
        rq.put(("error", exc))
        done_event.set()

        _drain(pump, after_calls)

        self.assertIs(pump.error, exc)
        self.assertIsNone(pump.result)
        self.assertEqual(len(closed), 1)

    def test_error_in_queue_but_done_event_not_set_does_not_close(self):
        """Erro lido da fila, mas done_event ainda False → não finaliza."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        exc = RuntimeError("worker explodiu")
        rq.put(("error", exc))
        # done_event NÃO setado

        after_calls.clear()
        pump._tick()  # processa a mensagem de erro

        self.assertIs(pump.error, exc, "erro deve ser armazenado")
        self.assertFalse(closed, "não deve fechar sem done_event")
        self.assertEqual(len(after_calls), 1, "deve reagendar")

    def test_unknown_message_type_does_not_crash(self):
        """Tipo de mensagem desconhecido é ignorado sem exceção."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        rq.put(("random_type", "data"))
        done_event.set()

        _drain(pump, after_calls)

        self.assertIsNone(pump.result)
        self.assertIsNone(pump.error)
        self.assertTrue(pump._finalized)


# ---------------------------------------------------------------------------
# Robustez: idempotência, cancel, close exception
# ---------------------------------------------------------------------------


class TestIdempotenceAndCancel(unittest.TestCase):
    def test_finalize_twice_calls_close_once(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump._finalize()
        pump._finalize()

        self.assertEqual(len(closed), 1)

    def test_cancel_prevents_future_ticks(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()
        pump.cancel()

        # Ticks subsequentes não devem reagendar
        after_calls.clear()
        pump._tick()
        pump._tick()

        self.assertFalse(closed)
        self.assertEqual(len(after_calls), 0)

    def test_cancel_invokes_after_cancel_fn(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        cancelled: list = []
        sentinel = object()

        def after_fn(ms, cb):
            after_calls.append((ms, cb))
            return sentinel

        def close_fn():
            pass

        def after_cancel_fn(aid):
            cancelled.append(aid)

        pump = _ProgressPump(
            rq,
            done_event,
            after_fn=after_fn,
            close_fn=close_fn,
            after_cancel_fn=after_cancel_fn,
        )
        pump.start()
        pump.cancel()

        self.assertIn(sentinel, cancelled)

    def test_close_fn_exception_does_not_propagate(self):
        """Exceção lançada por close_fn não deve vazar do _finalize."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        done_event.set()
        after_calls: list = []

        def after_fn(ms, cb):
            after_calls.append((ms, cb))
            return object()

        def close_fn():
            raise RuntimeError("destructing widget")

        pump = _ProgressPump(rq, done_event, after_fn=after_fn, close_fn=close_fn)
        pump.start()

        # Não deve levantar exceção
        _drain(pump, after_calls)
        self.assertTrue(pump._finalized)


# ---------------------------------------------------------------------------
# Drenagem em lote: múltiplas mensagens em um único tick
# ---------------------------------------------------------------------------


class TestQueueDrain(unittest.TestCase):
    def test_all_messages_drained_in_single_tick(self):
        """Múltiplas mensagens na fila são processadas em um único tick."""
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)
        pump.start()

        rq.put(("unknown_type", "x"))
        rq.put(("success", 7, []))
        done_event.set()

        after_calls.clear()
        pump._tick()

        self.assertEqual(pump.result, (7, []))
        self.assertTrue(pump._finalized)
        self.assertEqual(len(closed), 1)
        self.assertEqual(len(after_calls), 0)  # não reagendou (finalizou)


# ---------------------------------------------------------------------------
# Integração: thread real + done_event + queue, sem Tk
# ---------------------------------------------------------------------------


class TestThreadedIntegration(unittest.TestCase):
    """Verifica comportamento com thread de worker real (sem UI)."""

    def _run_pump_sync(self, pump, after_calls, max_iter=200):
        import time

        for _ in range(max_iter):
            if pump._finalized:
                break
            if after_calls:
                _, cb = after_calls.pop(0)
                cb()
            else:
                time.sleep(0.005)  # aguarda worker

    def test_threaded_success_flow(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)

        def worker():
            import time

            time.sleep(0.01)
            rq.put(("success", 10, []))
            done_event.set()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        pump.start()

        t.join(timeout=3)
        self._run_pump_sync(pump, after_calls)

        self.assertEqual(pump.result, (10, []))
        self.assertTrue(pump._finalized)
        self.assertTrue(closed)

    def test_threaded_error_flow(self):
        rq: queue.Queue = queue.Queue()
        done_event = threading.Event()
        after_calls: list = []
        closed: list = []

        pump = _make_pump(rq, done_event, after_calls, closed)

        exc = ConnectionError("timeout simulado")

        def worker():
            import time

            time.sleep(0.01)
            rq.put(("error", exc))
            done_event.set()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        pump.start()

        t.join(timeout=3)
        self._run_pump_sync(pump, after_calls)

        self.assertIs(pump.error, exc)
        self.assertIsNone(pump.result)
        self.assertTrue(closed)


if __name__ == "__main__":
    unittest.main()
