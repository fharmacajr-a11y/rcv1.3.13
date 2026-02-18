from __future__ import annotations

import pytest

from src.ui.components.progress_dialog import ProgressDialog


def test_progress_dialog_updates_fields(tk_root_session):
    from src.ui.ctk_config import HAS_CUSTOMTKINTER

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

    # Para CustomTkinter, verificamos via get(), para tkinter puro via atributo interno
    if HAS_CUSTOMTKINTER and hasattr(dialog._progress, "get"):
        progress_value = dialog._progress.get()  # type: ignore[attr-defined]
        assert progress_value == pytest.approx(0.5)
    else:
        progress_value = dialog._progress._progress_value  # type: ignore[attr-defined]
        assert progress_value == pytest.approx(0.5)

    assert "ETA" in dialog._eta_var.get()  # type: ignore[attr-defined]

    dialog.set_progress(None)
    assert dialog._indeterminate is True  # type: ignore[attr-defined]

    dialog.set_progress(1.0)
    assert dialog._indeterminate is False  # type: ignore[attr-defined]

    # Verificar progresso em 100%
    if HAS_CUSTOMTKINTER and hasattr(dialog._progress, "get"):
        progress_value = dialog._progress.get()  # type: ignore[attr-defined]
        assert progress_value == pytest.approx(1.0)
    else:
        progress_value = dialog._progress._progress_value  # type: ignore[attr-defined]
        assert progress_value == pytest.approx(1.0)

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
