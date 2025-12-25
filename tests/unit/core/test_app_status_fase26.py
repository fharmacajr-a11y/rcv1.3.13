from __future__ import annotations

import logging
import types
from pathlib import Path
from typing import Any

import pytest

from src import app_status


class DummyVar:
    def __init__(self) -> None:
        self.value = None

    def set(self, value: Any) -> None:
        self.value = value


class DummyStatusDot:
    def __init__(self) -> None:
        self.bootstyle = None

    def configure(self, *, bootstyle: str) -> None:
        self.bootstyle = bootstyle


def test_set_env_text_prefers_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class App:
        def _merge_status_text(self, text: str) -> None:
            calls.append(text)

    app = App()
    app_status._set_env_text(app, "ONLINE")
    assert calls == ["ONLINE"]


def test_set_env_text_logs_exception(caplog: pytest.LogCaptureFixture) -> None:
    class App:
        def _merge_status_text(self, text: str) -> None:
            raise RuntimeError("fail")

    caplog.set_level(logging.DEBUG, logger=app_status.log.name)
    app_status._set_env_text(App(), "x")
    assert any("Falha ao propagar texto de ambiente" in rec.message for rec in caplog.records)


def test_set_env_text_uses_status_var_text(monkeypatch: pytest.MonkeyPatch) -> None:
    var = DummyVar()
    app = types.SimpleNamespace(status_var_text=var)
    app_status._set_env_text(app, "OFFLINE")
    assert var.value == "OFFLINE"


def test_apply_status_with_status_dot_and_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    var_dot = DummyVar()
    status_dot = DummyStatusDot()
    callback_calls: list[app_status.Status] = []

    class App:
        def __init__(self) -> None:
            self.status_var_dot = var_dot
            self.status_dot = status_dot
            self.status_var_text = DummyVar()

        def winfo_exists(self) -> bool:
            return True

        def on_net_status_change(self, status: app_status.Status) -> None:
            callback_calls.append(status)

    app = App()
    app_status._apply_status(app, app_status.Status.ONLINE)

    assert var_dot.value == app_status._STATUS_DOT
    assert status_dot.bootstyle == "success"
    assert app.status_var_text.value == "ONLINE"
    assert callback_calls == [app_status.Status.ONLINE]


def test_apply_status_skips_when_window_missing() -> None:
    class App:
        def winfo_exists(self) -> bool:
            return False

    app = App()
    app_status._apply_status(app, app_status.Status.OFFLINE)  # nothing should raise


def test_apply_status_winfo_raises() -> None:
    class App:
        def winfo_exists(self) -> bool:
            raise RuntimeError("boom")

    app_status._apply_status(App(), app_status.Status.ONLINE)


def test_apply_status_handles_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    class BadStatusDot:
        def configure(self, *, bootstyle: str) -> None:
            raise RuntimeError("fail")

    class App:
        def __init__(self) -> None:
            self.status_dot = BadStatusDot()
            self.status_var_text = DummyVar()

    app = App()

    def bad_callback(status: app_status.Status) -> None:
        raise ValueError("callback boom")

    app.on_net_status_change = bad_callback  # type: ignore[attr-defined]
    app_status._apply_status(app, app_status.Status.OFFLINE)


def test_read_cfg_from_disk_with_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
status_probe:
  url: https://example.com
  timeout_seconds: 1.5
  interval_ms: 12345
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_status, "CONFIG_PATH", cfg_path)
    url, timeout, interval = app_status._read_cfg_from_disk()
    assert url == "https://example.com"
    assert timeout == 1.5
    assert interval == 12345


def test_read_cfg_from_disk_fallback_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(Path, "open", fake_open, raising=False)
    monkeypatch.setattr(app_status, "DEFAULT_TIMEOUT", 9.9)
    monkeypatch.setattr(app_status, "DEFAULT_INTERVAL_MS", 1111)

    url, timeout, interval = app_status._read_cfg_from_disk()
    assert url == ""
    assert timeout == 9.9
    assert interval == 1111


def test_get_cfg_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    cached = ("cached://", 7.7, 7777)
    app_status._cfg_cache = (app_status.CONFIG_PATH, -1.0, cached)
    monkeypatch.setattr(Path, "stat", lambda self: (_ for _ in ()).throw(OSError()), raising=False)

    result = app_status._get_cfg()
    assert result == cached


def test_get_cfg_reads_when_cache_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    app_status._cfg_cache = None
    monkeypatch.setattr(Path, "stat", lambda self: types.SimpleNamespace(st_mtime=5.0), raising=False)
    monkeypatch.setattr(app_status, "_read_cfg_from_disk", lambda: ("u", 2.2, 2200))

    result = app_status._get_cfg()
    assert result == ("u", 2.2, 2200)
    assert app_status._cfg_cache is not None
    app_status._cfg_cache = None


def test_update_net_status_starts_once(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyThread:
        def __init__(self, *, target: Any, daemon: bool, name: str):
            self.target = target
            self.daemon = daemon
            self.name = name
            self.started = 0

        def start(self) -> None:
            self.started += 1

    app = types.SimpleNamespace(after=lambda delay, fn: fn())
    monkeypatch.setattr(app_status, "_get_cfg", lambda: ("http://x", 1.0, 1000))
    monkeypatch.setattr(app_status, "probe", lambda url, timeout=0.0: app_status.Status.ONLINE)
    monkeypatch.setattr(
        app_status.threading,
        "Thread",
        lambda target, daemon, name: DummyThread(target=target, daemon=daemon, name=name),
    )

    app_status.update_net_status(app)
    assert getattr(app, "_net_worker_started")
    thread_obj = getattr(app, "_net_worker_thread")
    assert isinstance(thread_obj, DummyThread)
    assert thread_obj.started == 1

    app_status.update_net_status(app)  # second call should be no-op
    assert thread_obj.started == 1


def test_update_net_status_handles_probe_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyThread:
        def __init__(self, *, target: Any, daemon: bool, name: str):
            self.started = 0

        def start(self) -> None:
            self.started += 1

    captured: list[app_status.Status] = []

    class App:
        def __init__(self) -> None:
            self.after_calls: list[Any] = []

        def after(self, delay: int, func):
            self.after_calls.append(delay)
            func()

    app = App()
    monkeypatch.setattr(app_status, "_get_cfg", lambda: ("http://y", 3.0, 0))
    monkeypatch.setattr(app_status, "probe", lambda url, timeout=0.0: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(app_status, "_apply_status", lambda app_obj, st: captured.append(st))
    monkeypatch.setattr(
        app_status.threading,
        "Thread",
        lambda target, daemon, name: DummyThread(target=target, daemon=daemon, name=name),
    )

    app_status.update_net_status(app)
    assert captured == [app_status.Status.LOCAL]
    assert app.after_calls == [0]
    app._net_worker_started = False


def test_update_net_status_after_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyThread:
        def __init__(self, *, target: Any, daemon: bool, name: str):
            self.started = 0

        def start(self) -> None:
            self.started += 1

    class App:
        def __init__(self) -> None:
            self.after_calls = 0

        def after(self, delay: int, func):
            self.after_calls += 1
            raise RuntimeError("after fail")

    app = App()
    monkeypatch.setattr(app_status, "_get_cfg", lambda: ("http://z", 1.0, 0))
    monkeypatch.setattr(app_status, "probe", lambda url, timeout=0.0: app_status.Status.ONLINE)
    monkeypatch.setattr(
        app_status.threading,
        "Thread",
        lambda target, daemon, name: DummyThread(target=target, daemon=daemon, name=name),
    )

    app_status.update_net_status(app)
    assert app.after_calls == 1


def test_update_net_status_worker_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_cfg():
        return ("url", 1.0, 1000)

    class DummyThread:
        def __init__(self, *, target: Any, daemon: bool, name: str):
            self.target = target
            self.started = 0

        def start(self) -> None:
            self.started += 1

    app = types.SimpleNamespace(
        after=lambda delay, fn: fn(),
        _net_worker_started=False,
        _net_last_ui=0.0,
        _net_last_status=None,
        winfo_exists=lambda: True,
    )
    captured: list[app_status.Status] = []

    monkeypatch.setattr(app_status, "_get_cfg", fake_get_cfg)
    monkeypatch.setattr(app_status, "probe", lambda url, timeout=0.0: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(app_status, "_apply_status", lambda app_obj, st: captured.append(st))
    monkeypatch.setattr(
        app_status.threading,
        "Thread",
        lambda target, daemon, name: DummyThread(target=target, daemon=daemon, name=name),
    )
    monkeypatch.setattr(app_status.time, "sleep", lambda s: (_ for _ in ()).throw(StopIteration()))

    app_status.update_net_status(app)
    thread = getattr(app, "_net_worker_thread")
    with pytest.raises(StopIteration):
        thread.target()
    assert captured  # at least one status applied


def test_update_net_status_worker_dispatch_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyThread:
        def __init__(self, *, target: Any, daemon: bool, name: str):
            self.target = target
            self.started = 0

        def start(self) -> None:
            self.started += 1

    app = types.SimpleNamespace(
        after=lambda delay, fn: fn(),
        _net_worker_started=False,
        _net_last_ui=0.0,
        _net_last_status=None,
        winfo_exists=lambda: (_ for _ in ()).throw(RuntimeError("winfo fail")),
    )
    monkeypatch.setattr(app_status, "_get_cfg", lambda: ("u", 1.0, 1000))
    monkeypatch.setattr(app_status, "probe", lambda url, timeout=0.0: app_status.Status.ONLINE)
    monkeypatch.setattr(
        app_status.threading,
        "Thread",
        lambda target, daemon, name: DummyThread(target=target, daemon=daemon, name=name),
    )
    monkeypatch.setattr(app_status.time, "sleep", lambda s: (_ for _ in ()).throw(StopIteration()))

    app_status.update_net_status(app)
    thread = getattr(app, "_net_worker_thread")
    with pytest.raises(StopIteration):
        thread.target()
