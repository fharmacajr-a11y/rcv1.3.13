from __future__ import annotations

from typing import Any, Callable

import pytest

from src.core import status_monitor


def _make_monitor(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cloud_only: bool = False,
    after_impl: Callable[[int, Callable[[], None]], Any] | None = None,
):
    monkeypatch.setattr(status_monitor, "cloud_only_default", lambda: cloud_only)

    calls: list[tuple[str, tuple[Any, ...]]] = []

    def set_text(*args: Any) -> None:
        calls.append(("set_text", args))

    def after(delay: int, func: Callable[[], None]) -> None:
        calls.append(("after", (delay,)))
        func()

    monitor = status_monitor.StatusMonitor(set_text, app_after=after_impl or after, interval_ms=5)
    return monitor, calls


def test_initial_state_and_unknown_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monitor, calls = _make_monitor(monkeypatch, cloud_only=False)

    assert monitor._online is None
    assert monitor._net is None

    monitor._post_update()

    set_calls = [c for c in calls if c[0] == "set_text"]
    assert set_calls, "expected set_text to be invoked"
    text, online = set_calls[-1][1]
    assert "Local" in text
    assert "verificando" in text
    assert online is None


def test_set_cloud_status_transitions(monkeypatch: pytest.MonkeyPatch) -> None:
    monitor, calls = _make_monitor(monkeypatch, cloud_only=True)

    monitor.set_cloud_status(True)
    monitor.set_cloud_status(False)

    set_calls = [c for c in calls if c[0] == "set_text"]
    statuses = [(args[0], args[1]) for (_, args) in set_calls[-2:]]

    assert any("online" in text for text, _ in statuses)
    assert any("offline" in text for text, _ in statuses)
    assert statuses[-1][1] is False


def test_on_net_change_uses_after(monkeypatch: pytest.MonkeyPatch) -> None:
    after_calls: list[int] = []
    monitor, calls = _make_monitor(
        monkeypatch,
        cloud_only=True,
        after_impl=lambda delay, func: after_calls.append(delay) or func(),
    )

    monitor._on_net_change(True)

    assert after_calls == [0, 0]
    set_call = [c for c in calls if c[0] == "set_text"][-1]
    text, online = set_call[1]
    assert "online" in text
    assert online is True


def test_on_net_change_fallback_when_after_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple[Any, ...]]] = []

    def failing_after(delay: int, func: Callable[[], None]) -> None:
        raise RuntimeError("boom")

    def set_text(*args: Any) -> None:
        calls.append(("set_text", args))

    monitor = status_monitor.StatusMonitor(set_text, app_after=failing_after, interval_ms=5)
    monitor._on_net_change(False)

    set_call = [c for c in calls if c[0] == "set_text"][-1]
    text, online = set_call[1]
    assert "offline" in text
    assert online is False


def test_start_and_stop_wire_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[Any] = []

    class DummyWorker:
        def __init__(self, callback: Callable[[bool], None], interval_ms: int) -> None:  # noqa: D401
            self.callback = callback
            self.interval_ms = interval_ms
            self.started = 0
            self.stopped = 0
            created.append(self)

        def start(self) -> None:
            self.started += 1

        def stop(self) -> None:
            self.stopped += 1

    monkeypatch.setattr(status_monitor, "_NetStatusWorker", DummyWorker)
    monitor, _ = _make_monitor(monkeypatch, cloud_only=True)

    monitor.start()
    worker = created[-1]
    assert isinstance(monitor._net, DummyWorker)
    assert worker.started == 1

    monitor.stop()
    assert worker.stopped == 1
    assert monitor._net is None


def test_net_status_worker_run_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status_monitor, "probe", lambda: status_monitor.Status.ONLINE)
    calls: list[bool] = []
    worker = status_monitor._NetStatusWorker(lambda is_online: (calls.append(is_online), worker._stop_event.set()))

    worker._run()

    assert calls == [True]


def test_net_status_worker_handles_probe_and_callback_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status_monitor, "probe", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    calls: list[bool] = []

    def callback(is_online: bool) -> None:
        calls.append(is_online)
        worker._stop_event.set()
        raise ValueError("listener boom")

    worker = status_monitor._NetStatusWorker(callback, interval_ms=1)
    worker._run()

    assert calls == [False]
