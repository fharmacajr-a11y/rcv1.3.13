"""Testes focados em regressão SEC-001 para ClientPicker."""

from __future__ import annotations

import logging

import pytest

from src.modules.clientes.forms.client_picker import ClientPicker


class _BrokenDialog:
    def close(self) -> None:
        raise RuntimeError("Falha simulada no close()")


def test_close_busy_logs_exception_and_clears_dialog(caplog: pytest.LogCaptureFixture) -> None:
    picker = ClientPicker.__new__(ClientPicker)
    picker._busy_dialog = _BrokenDialog()  # type: ignore[attr-defined]

    caplog.set_level(logging.ERROR, logger="src.modules.clientes.forms.client_picker")

    picker._close_busy()

    assert picker._busy_dialog is None
    assert any("Falha ao fechar BusyDialog" in record.message for record in caplog.records)
