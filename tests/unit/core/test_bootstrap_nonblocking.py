# -*- coding: utf-8 -*-
"""Testes para garantir que schedule_healthcheck_after_gui não bloqueia a UI."""

import threading
import time
from unittest.mock import MagicMock, patch


def test_schedule_healthcheck_uses_thread_not_blocking(monkeypatch):
    """Verifica que healthcheck roda em thread separada e não bloqueia."""
    from src.core import bootstrap

    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")

    # Mock app with after() capability
    app = MagicMock()
    call_sequence = []

    def mock_after(ms, func):
        """Simula app.after() executando func imediatamente para teste."""
        call_sequence.append(f"after({ms})")
        func()  # Executa imediatamente para teste

    app.after = mock_after

    # Mock check_internet_connectivity para não fazer rede real
    with patch("src.utils.network.check_internet_connectivity") as mock_check:
        mock_check.return_value = True

        # Track thread creation
        original_thread = threading.Thread
        threads_created = []

        def track_thread(*args, **kwargs):
            t = original_thread(*args, **kwargs)
            threads_created.append(t)
            return t

        with patch("threading.Thread", side_effect=track_thread):
            bootstrap.schedule_healthcheck_after_gui(app, logger=None, delay_ms=100)

            # Wait for background thread to complete
            time.sleep(0.5)

    # Verificações
    assert len(threads_created) == 1, "Deve criar exatamente 1 thread"
    assert threads_created[0].daemon, "Thread deve ser daemon"
    assert threads_created[0].name == "HealthCheckWorker"
    assert "after(100)" in call_sequence, "Deve agendar via after()"


def test_schedule_healthcheck_skips_in_local_mode(monkeypatch):
    """Verifica que healthcheck é ignorado quando não está em cloud-only mode."""
    from src.core import bootstrap

    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)

    app = MagicMock()

    def mock_after(ms, func):
        func()

    app.after = mock_after

    with patch("src.utils.network.check_internet_connectivity") as mock_check:
        bootstrap.schedule_healthcheck_after_gui(app, logger=None, delay_ms=100)
        time.sleep(0.3)

    # check_internet_connectivity não deve ser chamado quando RC_NO_LOCAL_FS != 1
    mock_check.assert_not_called()


def test_schedule_healthcheck_handles_app_without_footer():
    """Verifica que funciona mesmo se app não tiver atributo footer."""
    from src.core import bootstrap
    import os

    os.environ["RC_NO_LOCAL_FS"] = "1"

    app = MagicMock()
    # Remove footer attribute
    del app.footer

    def mock_after(ms, func):
        func()

    app.after = mock_after

    with patch("src.utils.network.check_internet_connectivity") as mock_check:
        mock_check.return_value = True

        # Não deve gerar exceção
        bootstrap.schedule_healthcheck_after_gui(app, logger=None, delay_ms=100)
        time.sleep(0.3)

    # Deve ter tentado check
    assert mock_check.called
