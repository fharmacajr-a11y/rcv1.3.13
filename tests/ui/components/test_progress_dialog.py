from __future__ import annotations

import pytest

from src.ui.components.progress_dialog import ProgressDialog


def test_progress_dialog_updates_fields(tk_root_session):
    dialog = ProgressDialog(
        tk_root_session,
        title="Teste",
        message="Inicial",
        detail="Detalhe",
    )

    dialog.set_message("Nova mensagem")
    dialog.set_detail("Novo detalhe")
    dialog.set_progress(0.5)
    dialog.set_eta(125)

    assert dialog._message_var.get() == "Nova mensagem"  # type: ignore[attr-defined]
    assert dialog._detail_var.get() == "Novo detalhe"  # type: ignore[attr-defined]
    assert float(dialog._progress.cget("value")) == pytest.approx(50.0)  # type: ignore[attr-defined]
    assert "ETA" in dialog._eta_var.get()  # type: ignore[attr-defined]

    dialog.set_progress(None)
    assert str(dialog._progress.cget("mode")) == "indeterminate"  # type: ignore[attr-defined]

    dialog.set_progress(1.0)
    assert str(dialog._progress.cget("mode")) == "determinate"  # type: ignore[attr-defined]
    assert float(dialog._progress.cget("value")) == pytest.approx(100.0)  # type: ignore[attr-defined]

    dialog.close()


def test_progress_dialog_cancel_invokes_callback(tk_root_session):
    called = {"count": 0}

    def _on_cancel() -> None:
        called["count"] += 1

    dialog = ProgressDialog(
        tk_root_session,
        title="Cancelavel",
        can_cancel=True,
        on_cancel=_on_cancel,
    )

    button = dialog._cancel_button  # type: ignore[attr-defined]
    assert button is not None

    button.invoke()
    assert called["count"] == 1

    dialog.close()
