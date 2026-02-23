# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes unitários para src/modules/hub/controller.py — sem Tk real, sem rede.

Estratégia de isolamento
-------------------------
controller.py importa vários módulos pesados (logger, cores, serviços de notas,
supabase). Para não precisar de infraestrutura real, inserimos mocks no
sys.modules ANTES do primeiro import do controller, substituindo apenas os
módulos externos que o controller usa por MagicMocks.

src.modules.hub.state é importado de verdade, pois só usa stdlib e é necessário
para que HubState funione corretamente.
"""

from __future__ import annotations

import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# 1. Pre-mock de módulos pesados — deve acontecer ANTES do import do controller
# ---------------------------------------------------------------------------
_LOGGER_MOCK = MagicMock()
_LOGGER_MOCK.get_logger.return_value = MagicMock()

_HEAVY_MOCKS: dict[str, MagicMock] = {
    "src.core.logger": _LOGGER_MOCK,
    "src.modules.hub.colors": MagicMock(),
    "src.modules.hub.services": MagicMock(),
    "src.modules.hub.services.authors_service": MagicMock(),
    "src.modules.hub.format": MagicMock(),
    "src.modules.hub.utils": MagicMock(),
    "src.modules.notas": MagicMock(),
    "src.modules.notas.service": MagicMock(),
    "tkinter": MagicMock(),
    "tkinter.messagebox": MagicMock(),
}

for _mod_name, _mock in _HEAVY_MOCKS.items():
    sys.modules.setdefault(_mod_name, _mock)

# Agora é seguro importar o controller
import src.modules.hub.controller as _ctrl  # noqa: E402
from src.modules.hub.controller import cancel_poll, schedule_poll  # noqa: E402
from src.modules.hub.state import HubState  # noqa: E402


# ---------------------------------------------------------------------------
# 2. Fakes mínimos
# ---------------------------------------------------------------------------

class _FakeScreenState:
    def __init__(self, live_sync_on: bool = False) -> None:
        self.live_sync_on = live_sync_on
        self.live_org_id: str | None = None
        self.live_last_ts: str | None = None
        self.polling_active: bool = False


class FakeScreen:
    """Substituto leve de HubScreen; não cria janela Tk."""

    def __init__(self, live_sync_on: bool = False) -> None:
        self.state = _FakeScreenState(live_sync_on=live_sync_on)
        self._after_counter = 0
        self._after_callbacks: dict[str, object] = {}   # id → callable
        self._cancelled: set[str] = set()
        # Instância real de HubState para que _ensure_poll_attrs funcione
        self._hub_state = HubState()
        self._last_render_hash = None

    def after(self, ms: int, fn) -> str:  # type: ignore[override]
        self._after_counter += 1
        job_id = f"after#{self._after_counter}"
        self._after_callbacks[job_id] = fn
        return job_id

    def after_cancel(self, job_id: str) -> None:
        self._cancelled.add(job_id)
        self._after_callbacks.pop(job_id, None)


# ---------------------------------------------------------------------------
# 3. Testes
# ---------------------------------------------------------------------------

class TestSchedulePoll(unittest.TestCase):

    def test_live_sync_off_does_not_schedule(self):
        """Com live_sync_on=False, schedule_poll não deve criar poll_job."""
        screen = FakeScreen(live_sync_on=False)
        schedule_poll(screen)

        self.assertIsNone(screen._hub_state.poll_job)
        self.assertEqual(screen._after_counter, 0)

    def test_live_sync_on_schedules_once(self):
        """Com live_sync_on=True, schedule_poll deve criar exatamente 1 after()."""
        screen = FakeScreen(live_sync_on=True)
        schedule_poll(screen)

        self.assertIsNotNone(screen._hub_state.poll_job)
        self.assertEqual(screen._after_counter, 1)
        # O job_id armazenado deve bater com o retornado por after()
        self.assertEqual(screen._hub_state.poll_job, "after#1")

    def test_rescheduling_cancels_previous_job(self):
        """Segunda chamada de schedule_poll deve cancelar o job anterior e criar um novo."""
        screen = FakeScreen(live_sync_on=True)
        schedule_poll(screen)
        first_job = screen._hub_state.poll_job

        schedule_poll(screen)  # reagenda
        second_job = screen._hub_state.poll_job

        self.assertIn(first_job, screen._cancelled)
        self.assertNotEqual(first_job, second_job)
        self.assertEqual(screen._hub_state.poll_job, second_job)


class TestCancelPoll(unittest.TestCase):

    def test_cancel_clears_job_and_calls_after_cancel(self):
        """cancel_poll deve cancelar o job pendente e zerar poll_job."""
        screen = FakeScreen(live_sync_on=True)
        schedule_poll(screen)
        job_id = screen._hub_state.poll_job

        cancel_poll(screen)

        self.assertIn(job_id, screen._cancelled)
        self.assertIsNone(screen._hub_state.poll_job)

    def test_cancel_when_no_job_is_noop(self):
        """cancel_poll sem job pendente não deve levantar exceção."""
        screen = FakeScreen(live_sync_on=True)
        try:
            cancel_poll(screen)
        except Exception as exc:
            self.fail(f"cancel_poll levantou inesperadamente: {exc}")
        self.assertIsNone(screen._hub_state.poll_job)


class TestToggleLiveSyncOnOff(unittest.TestCase):

    def test_toggle_true_then_false_cancels_and_does_not_reschedule(self):
        """
        Sequência: live_sync_on=True → schedule_poll → live_sync_on=False →
        cancel_poll deve cancelar e schedule_poll subsequente não deve reagendar.
        """
        screen = FakeScreen(live_sync_on=True)
        schedule_poll(screen)
        job_id = screen._hub_state.poll_job
        self.assertIsNotNone(job_id)

        # Desabilita live sync e cancela
        screen.state.live_sync_on = False
        cancel_poll(screen)
        self.assertIsNone(screen._hub_state.poll_job)
        self.assertIn(job_id, screen._cancelled)

        # Com live_sync_on=False, schedule_poll não agenda nada
        initial_counter = screen._after_counter
        schedule_poll(screen)
        self.assertEqual(screen._after_counter, initial_counter)
        self.assertIsNone(screen._hub_state.poll_job)


class TestCallbackEarlyBinding(unittest.TestCase):
    """Garante que a lambda captura o screen correto (early binding via s=screen)."""

    def test_callback_references_original_screen(self):
        """
        O callback armazenado em poll_job deve chamar poll_notes_if_needed com o
        screen passado originalmente em schedule_poll, mesmo que a variável local
        no chamador seja reatribuída depois.
        """
        screen_original = FakeScreen(live_sync_on=True)

        with patch.object(_ctrl, "poll_notes_if_needed") as mock_poll:
            schedule_poll(screen_original)
            job_id = screen_original._hub_state.poll_job
            callback = screen_original._after_callbacks[job_id]

            # Simula reatribuição do nome no chamador (não afeta o early binding)
            screen_other = FakeScreen(live_sync_on=False)
            _ = screen_other  # referência apenas para evitar linter warning

            # Invoca o callback — deve chamar com screen_original, não screen_other
            callback()  # type: ignore[operator]

        mock_poll.assert_called_once_with(screen_original)

    def test_two_screens_get_independent_callbacks(self):
        """Dois schedule_poll com screens distintos geram callbacks independentes."""
        screen_a = FakeScreen(live_sync_on=True)
        screen_b = FakeScreen(live_sync_on=True)

        with patch.object(_ctrl, "poll_notes_if_needed") as mock_poll:
            schedule_poll(screen_a)
            schedule_poll(screen_b)

            job_a = screen_a._hub_state.poll_job
            job_b = screen_b._hub_state.poll_job

            callback_a = screen_a._after_callbacks[job_a]
            callback_b = screen_b._after_callbacks[job_b]

            callback_a()  # type: ignore[operator]
            callback_b()  # type: ignore[operator]

        calls = mock_poll.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIs(calls[0].args[0], screen_a)
        self.assertIs(calls[1].args[0], screen_b)


class TestPollLockPresence(unittest.TestCase):
    """Garante que poll_lock é criado como RLock, não Lock simples."""

    def test_poll_lock_is_rlock(self):
        # poll_lock é um field(default_factory=threading.RLock) em HubState;
        # deve existir imediatamente ao criar HubState(), sem necessidade de schedule_poll.
        screen = FakeScreen()
        self.assertIsInstance(screen._hub_state.poll_lock, type(threading.RLock()))

    def test_poll_lock_is_shared_between_schedule_and_cancel(self):
        """schedule_poll e cancel_poll devem usar o MESMO objeto de lock."""
        screen = FakeScreen(live_sync_on=True)
        schedule_poll(screen)
        lock_after_schedule = screen._hub_state.poll_lock

        cancel_poll(screen)
        lock_after_cancel = screen._hub_state.poll_lock

        self.assertIs(lock_after_schedule, lock_after_cancel)


if __name__ == "__main__":
    unittest.main()
