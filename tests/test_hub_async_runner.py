# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes unitários para src/modules/hub/async_runner.py (HubAsyncRunner)."""

from __future__ import annotations

import sys
import threading
import unittest

# ---------------------------------------------------------------------------
# Pre-mock de tkinter e do pacote hub antes de qualquer import
# ---------------------------------------------------------------------------
import importlib.util
import pathlib
import types
from unittest.mock import MagicMock

_tk_mock = types.ModuleType("tkinter")


class _TclError(Exception):
    pass


_tk_mock.TclError = _TclError  # type: ignore[attr-defined]
_tk_mock.Misc = object  # type: ignore[attr-defined]
_tk_mock.messagebox = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("tkinter", _tk_mock)
sys.modules.setdefault("tkinter.messagebox", MagicMock())

# Importa async_runner diretamente pelo caminho do arquivo, ignorando o
# hub/__init__.py que arrasta toda a cadeia views → HubScreen → tkinter pesado.
_WORKSPACE = pathlib.Path(__file__).parent.parent
_RUNNER_PATH = _WORKSPACE / "src" / "modules" / "hub" / "async_runner.py"
_spec = importlib.util.spec_from_file_location("src.modules.hub.async_runner", _RUNNER_PATH)
_runner_module = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["src.modules.hub.async_runner"] = _runner_module
_spec.loader.exec_module(_runner_module)  # type: ignore[union-attr]
HubAsyncRunner = _runner_module.HubAsyncRunner


# ---------------------------------------------------------------------------
# FakeRoot: substituto de tk.Misc/tk.Tk sem janela real
# ---------------------------------------------------------------------------
class FakeRoot:
    """Fake mínimo de Tk para testar HubAsyncRunner sem UI real."""

    def __init__(self) -> None:
        self._counter = 0
        self._pending: dict[int, tuple] = {}   # id → (fn, args)
        self._cancelled: set[int] = set()
        self._destroyed = False

    def winfo_exists(self) -> bool:
        return not self._destroyed

    def after(self, ms: int, fn, *args) -> int:
        self._counter += 1
        after_id = self._counter
        self._pending[after_id] = (fn, args)
        return after_id

    def after_cancel(self, after_id: int) -> None:
        self._cancelled.add(after_id)
        self._pending.pop(after_id, None)

    def run_pending(self, after_id: int) -> None:
        """Simula o mainloop do Tk executando o callback agendado."""
        entry = self._pending.pop(after_id, None)
        if entry is not None:
            fn, args = entry
            fn(*args)

    def run_all_pending(self) -> None:
        """Executa todos os callbacks pendentes (cópia para evitar mutação durante iteração)."""
        for aid in list(self._pending.keys()):
            self.run_pending(aid)

    def destroy(self) -> None:
        self._destroyed = True


def _make_runner(root: FakeRoot | None = None) -> tuple[HubAsyncRunner, FakeRoot]:
    if root is None:
        root = FakeRoot()
    runner = HubAsyncRunner(tk_root=root)
    return runner, root


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestPendingSetAddAndRemove(unittest.TestCase):
    """set de IDs: add ao agendar, remove ao executar."""

    def test_schedule_adds_id_to_set(self):
        runner, root = _make_runner()
        runner._schedule_callback(lambda: None)

        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, 1)

    def test_running_callback_removes_id(self):
        runner, root = _make_runner()
        runner._schedule_callback(lambda: None)

        # Pega o id agendado
        with runner._pending_lock:
            after_id = next(iter(runner._pending_after_ids))

        # Simula mainloop executando o callback
        root.run_pending(after_id)

        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, 0)

    def test_id_removed_even_if_callback_raises(self):
        """finally garante remoção mesmo se callback lança exceção."""
        runner, root = _make_runner()

        def _bad():
            raise RuntimeError("boom")

        runner._schedule_callback(_bad)

        with runner._pending_lock:
            after_id = next(iter(runner._pending_after_ids))

        root.run_pending(after_id)  # não deve propagar exceção

        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, 0)

    def test_multiple_callbacks_tracked_independently(self):
        runner, root = _make_runner()
        n = 5
        for _ in range(n):
            runner._schedule_callback(lambda: None)

        with runner._pending_lock:
            ids = list(runner._pending_after_ids)
        self.assertEqual(len(ids), n)

        # Executa apenas 2
        root.run_pending(ids[0])
        root.run_pending(ids[1])

        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, n - 2)


class TestShutdown(unittest.TestCase):
    """shutdown deve cancelar todos os IDs pendentes e limpar o set."""

    def test_shutdown_cancels_pending_ids(self):
        runner, root = _make_runner()
        runner._schedule_callback(lambda: None)
        runner._schedule_callback(lambda: None)

        with runner._pending_lock:
            ids_before = set(runner._pending_after_ids)
        self.assertEqual(len(ids_before), 2)

        runner.shutdown()

        # Os IDs devem ter sido passados para after_cancel
        self.assertTrue(ids_before.issubset(root._cancelled))

    def test_shutdown_clears_set(self):
        runner, root = _make_runner()
        runner._schedule_callback(lambda: None)
        runner.shutdown()

        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, 0)

    def test_shutdown_idempotent(self):
        """Chamar shutdown duas vezes não levanta exceção."""
        runner, root = _make_runner()
        runner.shutdown()
        try:
            runner.shutdown()
        except Exception as exc:
            self.fail(f"Segunda chamada a shutdown levantou: {exc}")

    def test_shutdown_prevents_new_schedules(self):
        """Após shutdown, _schedule_callback não deve adicionar novos IDs."""
        runner, root = _make_runner()
        runner.shutdown()
        runner._schedule_callback(lambda: None)

        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, 0)
        # Nenhum after() foi chamado
        self.assertEqual(root._counter, 0)

    def test_shutdown_tolerates_tclrerror_on_cancel(self):
        """after_cancel lançando TclError não deve interromper shutdown."""
        runner, root = _make_runner()
        runner._schedule_callback(lambda: None)

        def _bad_cancel(after_id):
            raise _TclError("widget destroyed")

        root.after_cancel = _bad_cancel  # type: ignore[method-assign]

        try:
            runner.shutdown()
        except Exception as exc:
            self.fail(f"shutdown não deve propagar TclError: {exc}")


class TestConcurrency(unittest.TestCase):
    """Várias threads chamando schedule simultaneamente não corrompem o set."""

    def test_concurrent_schedule_safe(self):
        runner, root = _make_runner()
        n_threads = 20
        errors: list[Exception] = []

        def _schedule():
            try:
                runner._schedule_callback(lambda: None)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_schedule) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Erros em threads: {errors}")
        with runner._pending_lock:
            size = len(runner._pending_after_ids)
        self.assertEqual(size, n_threads)

    def test_concurrent_schedule_and_shutdown(self):
        """schedule concorrente com shutdown não deve levantar exceções."""
        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        runner, root = _make_runner()

        def _schedules():
            barrier.wait()
            for _ in range(50):
                try:
                    runner._schedule_callback(lambda: None)
                except Exception as exc:
                    errors.append(exc)

        def _shutdown():
            barrier.wait()
            try:
                runner.shutdown()
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_schedules)
        t2 = threading.Thread(target=_shutdown)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [], f"Erros de concorrência: {errors}")
        # Após tudo, set deve ser consistente (não pode ter ids "fantasmas"
        # que foram simultaneamente adicionados e removidos de forma corrompida)
        with runner._pending_lock:
            remaining = set(runner._pending_after_ids)
        # Todos os IDs restantes devem estar nos pendentes do root ou cancelados
        for aid in remaining:
            self.assertTrue(
                aid in root._pending or aid in root._cancelled,
                f"ID {aid} não aparece nem em pending nem em cancelled",
            )


class TestPendingLockIsLock(unittest.TestCase):
    def test_pending_lock_type(self):
        runner, _ = _make_runner()
        self.assertIsInstance(runner._pending_lock, type(threading.Lock()))

    def test_pending_after_ids_is_set(self):
        runner, _ = _make_runner()
        self.assertIsInstance(runner._pending_after_ids, set)


if __name__ == "__main__":
    unittest.main()
