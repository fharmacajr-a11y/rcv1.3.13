from __future__ import annotations

import time
from types import SimpleNamespace

from src.modules.auditoria.views.dialogs import UploadProgressDialog


def test_auditoria_upload_progress_dialog_uses_progress_component(monkeypatch, tk_root_session):
    created = {}

    class DummyProgress:
        def __init__(self, *_args, **_kwargs):
            created["instance"] = self
            self.details: list[str] = []
            self.values: list[float] = []
            self.etas: list[str] = []
            self.closed = False

        def set_detail(self, text: str) -> None:
            self.details.append(text)

        def set_eta_text(self, text: str) -> None:
            self.etas.append(text)

        def set_progress(self, value: float) -> None:
            self.values.append(value)

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("src.modules.auditoria.views.dialogs.ProgressDialog", DummyProgress)

    dialog = UploadProgressDialog(tk_root_session, "Auditoria", "Msg", on_cancel=lambda: None)

    state = SimpleNamespace(
        total_files=2,
        total_bytes=2000,
        done_files=1,
        done_bytes=1000,
        start_ts=time.monotonic() - 1,
        ema_bps=500_000,
    )

    dialog.update_with_state(state)
    dialog.close()

    instance: DummyProgress = created["instance"]  # type: ignore[assignment]
    assert "1/2" in instance.details[-1]
    assert instance.values[-1] == 0.5
    assert "ETA" in instance.etas[-1]
    assert instance.closed is True
