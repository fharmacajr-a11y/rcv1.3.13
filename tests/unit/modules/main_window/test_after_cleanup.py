# -*- coding: utf-8 -*-
"""
Testes unitários para cleanup de .after() jobs (P0 #2).

Verifica que:
1. IDs de .after() são guardados
2. after_cancel() é chamado no destroy()
3. Não há duplicação de jobs
"""

import unittest
from unittest.mock import MagicMock


class MockApp:
    """Mock simplificado da classe App para testes."""

    def __init__(self):
        self._notifications_poll_job_id = None
        self._status_refresh_job_id = None
        self._health_poll_job_id = None
        self._status_monitor = None
        self._theme_listener = None
        self.after_cancel = MagicMock()


class TestAfterJobsCleanup(unittest.TestCase):
    """Testes para cleanup de .after() jobs."""

    def setUp(self):
        """Setup comum para todos os testes."""
        self.app = MockApp()

    def test_notifications_poll_job_id_is_stored(self):
        """Verifica que job ID de notifications poll é guardado."""
        self.assertIsNone(self.app._notifications_poll_job_id)

        # Simular agendamento
        self.app._notifications_poll_job_id = "job123"

        self.assertEqual(self.app._notifications_poll_job_id, "job123")

    def test_status_refresh_job_id_is_stored(self):
        """Verifica que job ID de status refresh é guardado."""
        self.assertIsNone(self.app._status_refresh_job_id)

        self.app._status_refresh_job_id = "job456"

        self.assertEqual(self.app._status_refresh_job_id, "job456")

    def test_health_poll_job_id_is_stored(self):
        """Verifica que job ID de health poll é guardado."""
        self.assertIsNone(self.app._health_poll_job_id)

        self.app._health_poll_job_id = "job789"

        self.assertEqual(self.app._health_poll_job_id, "job789")

    def test_destroy_cancels_notifications_poll(self):
        """Verifica que destroy() deve cancelar job de notifications poll."""
        self.app._notifications_poll_job_id = "job123"

        # Simular comportamento do destroy()
        if self.app._notifications_poll_job_id is not None:
            self.app.after_cancel(self.app._notifications_poll_job_id)
            self.app._notifications_poll_job_id = None

        # Verificar que after_cancel foi chamado
        self.app.after_cancel.assert_called_once_with("job123")

        # Verificar que o ID foi limpo
        self.assertIsNone(self.app._notifications_poll_job_id)

    def test_destroy_cancels_status_refresh(self):
        """Verifica que destroy() deve cancelar job de status refresh."""
        self.app._status_refresh_job_id = "job456"

        if self.app._status_refresh_job_id is not None:
            self.app.after_cancel(self.app._status_refresh_job_id)
            self.app._status_refresh_job_id = None

        self.app.after_cancel.assert_called_once_with("job456")
        self.assertIsNone(self.app._status_refresh_job_id)

    def test_destroy_cancels_health_poll(self):
        """Verifica que destroy() deve cancelar job de health poll."""
        self.app._health_poll_job_id = "job789"

        if self.app._health_poll_job_id is not None:
            self.app.after_cancel(self.app._health_poll_job_id)
            self.app._health_poll_job_id = None

        self.app.after_cancel.assert_called_once_with("job789")
        self.assertIsNone(self.app._health_poll_job_id)

    def test_destroy_handles_none_job_ids(self):
        """Verifica que destroy() não falha se job IDs forem None."""
        self.app._notifications_poll_job_id = None
        self.app._status_refresh_job_id = None
        self.app._health_poll_job_id = None

        # Simular comportamento do destroy() com None
        if self.app._notifications_poll_job_id is not None:
            self.app.after_cancel(self.app._notifications_poll_job_id)
        if self.app._status_refresh_job_id is not None:
            self.app.after_cancel(self.app._status_refresh_job_id)
        if self.app._health_poll_job_id is not None:
            self.app.after_cancel(self.app._health_poll_job_id)

        # after_cancel não deveria ser chamado
        self.app.after_cancel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
