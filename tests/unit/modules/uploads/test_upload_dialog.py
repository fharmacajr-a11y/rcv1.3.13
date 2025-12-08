from __future__ import annotations

from typing import Any

import pytest

from src.modules.uploads.exceptions import UploadError
from src.modules.uploads.views import upload_dialog
from src.modules.uploads.views.upload_dialog import UploadDialog


class ImmediateFuture:
    def __init__(self, result: Any):
        self._result = result

    def result(self) -> Any:
        return self._result

    def add_done_callback(self, cb):
        cb(self)


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        return ImmediateFuture(fn(*args, **kwargs))


def test_upload_dialog_runs_callable_and_updates_progress(monkeypatch: pytest.MonkeyPatch, tk_root_session):
    created: dict[str, Any] = {}

    class DummyProgress:
        def __init__(self, *_args, **_kwargs):
            created["progress"] = self
            self.messages: list[str] = []
            self.details: list[str] = []
            self.progress_values: list[float | None] = []
            self.closed = False

        def set_message(self, text: str) -> None:
            self.messages.append(text)

        def set_detail(self, text: str) -> None:
            self.details.append(text)

        def set_progress(self, value: float | None) -> None:
            self.progress_values.append(value)

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(upload_dialog, "ProgressDialog", DummyProgress)

    outcome: dict[str, Any] = {}
    tk_root_session.after = lambda _delay, func=None, *args: func(*args) if func else None  # type: ignore[assignment]

    def _upload_callable(ctx):
        ctx.set_total(2)
        ctx.advance("primeiro")
        ctx.advance("segundo")
        return {"ok": True}

    dlg = UploadDialog(
        tk_root_session,
        _upload_callable,
        total_items=2,
        executor=ImmediateExecutor(),
        on_complete=lambda result: outcome.update({"result": result}),
    )
    dlg.start()

    result = outcome["result"]
    progress: DummyProgress = created["progress"]  # type: ignore[assignment]

    assert result.error is None
    assert result.result["ok"] is True
    assert progress.closed is True
    assert progress.progress_values[-1] == 1.0
    assert "segundo" in progress.messages[-1]


def test_upload_dialog_reports_upload_error(monkeypatch: pytest.MonkeyPatch, tk_root_session):
    monkeypatch.setattr(
        upload_dialog,
        "ProgressDialog",
        lambda *a, **k: type(
            "D",
            (),
            {
                "set_progress": lambda *_: None,
                "set_message": lambda *_: None,
                "set_detail": lambda *_: None,
                "close": lambda *_: None,
            },
        )(),
    )

    outcome: dict[str, Any] = {}
    tk_root_session.after = lambda _delay, func=None, *args: func(*args) if func else None  # type: ignore[assignment]

    def _upload_callable(ctx):
        raise UploadError("boom")

    dlg = UploadDialog(
        tk_root_session,
        _upload_callable,
        executor=ImmediateExecutor(),
        on_complete=lambda result: outcome.update({"result": result}),
    )
    dlg.start()

    result = outcome["result"]
    assert isinstance(result.error, UploadError)
    assert result.error.message == "boom"
