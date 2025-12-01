from __future__ import annotations

import types

import src.core.status_monitor as monitor


class FakeThread:
    def __init__(self, target=None, daemon=None, name=None):
        self.target = target
        self.started = False
        self._alive = False
        self.join_called = False

    def start(self):
        self.started = True
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self.join_called = True
        self._alive = False


class FakeEvent:
    def __init__(self, wait_result=True):
        self._wait_result = wait_result
        self.set_called = False

    def set(self):
        self.set_called = True

    def is_set(self):
        return False

    def wait(self, _timeout):
        return self._wait_result


class FakeEventSet:
    def is_set(self):
        return True

    def wait(self, _timeout):
        return True

    def set(self):
        pass


class FakeEventCycle:
    def __init__(self):
        self.toggled = False

    def is_set(self):
        return self.toggled

    def wait(self, _timeout):
        self.toggled = True
        return False

    def set(self):
        self.toggled = True


def test_netstatusworker_start_stop(monkeypatch):
    monkeypatch.setattr(monitor.threading, "Thread", FakeThread)
    worker = monitor._NetStatusWorker(callback=lambda online: None, interval_ms=10)
    worker.start()
    assert isinstance(worker._thread, FakeThread)
    assert worker._thread.started is True

    worker.stop()
    assert worker._thread is None

    alive_thread = FakeThread()
    alive_thread._alive = True
    worker._thread = alive_thread
    worker.start()
    assert alive_thread.started is False  # start not called again


def test_netstatusworker_run_success(monkeypatch):
    monkeypatch.setattr(monitor, "probe", lambda: monitor.Status.ONLINE)
    worker = monitor._NetStatusWorker(callback=lambda online: results.append(online), interval_ms=10)
    results = []
    worker._stop_event = FakeEvent(wait_result=True)  # type: ignore[assignment]
    worker._run()
    assert results == [True]


def test_netstatusworker_run_probe_and_callback_fail(monkeypatch, caplog):
    monkeypatch.setattr(monitor, "probe", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    def bad_callback(_online):
        raise RuntimeError("cb fail")

    worker = monitor._NetStatusWorker(callback=bad_callback, interval_ms=10)
    worker._stop_event = FakeEvent(wait_result=True)  # type: ignore[assignment]
    with caplog.at_level("DEBUG", logger=monitor.log.name):
        worker._run()
    assert any("callback de rede falhou" in rec.getMessage() for rec in caplog.records)


def test_netstatusworker_run_exit_when_set(monkeypatch):
    worker = monitor._NetStatusWorker(callback=lambda _: None, interval_ms=10)
    worker._stop_event = FakeEventSet()  # type: ignore[assignment]
    worker._run()  # should exit immediately without errors


def test_netstatusworker_run_wait_continue(monkeypatch):
    monkeypatch.setattr(monitor, "probe", lambda: monitor.Status.ONLINE)
    called = []
    worker = monitor._NetStatusWorker(callback=lambda online: called.append(online), interval_ms=10)
    worker._stop_event = FakeEventCycle()  # type: ignore[assignment]
    worker._run()
    assert called == [True]


def test_netstatusworker_stop_no_thread():
    worker = monitor._NetStatusWorker(callback=lambda _: None, interval_ms=10)
    worker._thread = None
    worker.stop()  # should no-op


def test_post_update_uses_after_and_typeerror_fallback(monkeypatch):
    texts = []

    def set_text(arg, online=None):
        if online is not None:
            raise TypeError("only one arg")
        texts.append(arg)

    def after(_delay, callback):
        callback()

    m = monitor.StatusMonitor(set_text, app_after=after, interval_ms=10)
    m._online = True
    m._is_cloud = True
    m._post_update()
    assert texts[-1].startswith("Nuvem")


def test_post_update_after_exception(monkeypatch):
    texts = []

    def set_text(text, online=None):
        texts.append((text, online))

    m = monitor.StatusMonitor(
        set_text, app_after=lambda *_args: (_ for _ in ()).throw(RuntimeError("fail")), interval_ms=10
    )
    m._online = False
    m._post_update()
    assert texts[-1][1] is False


def test_on_net_change_updates_and_handles_after(monkeypatch):
    m = monitor.StatusMonitor(
        lambda *_args: None, app_after=lambda *_args: (_ for _ in ()).throw(RuntimeError("fail")), interval_ms=10
    )
    m._online = None
    m._post_update = lambda: setattr(m, "_online", "updated")  # type: ignore[method-assign]
    m._on_net_change(True)
    assert m._online == "updated"


def test_status_monitor_start_stop(monkeypatch):
    fake_worker = types.SimpleNamespace(start_called=0, stop_called=0)

    class FakeWorker:
        def __init__(self, callback, interval_ms):
            self.callback = callback

        def start(self):
            fake_worker.start_called += 1

        def stop(self):
            fake_worker.stop_called += 1

    texts = []
    m = monitor.StatusMonitor(
        lambda text, online=None: texts.append((text, online)), app_after=lambda _d, cb: cb(), interval_ms=5
    )
    monkeypatch.setattr(monitor, "_NetStatusWorker", FakeWorker)

    m.start()
    assert fake_worker.start_called == 1
    assert texts  # post_update called

    m.stop()
    assert fake_worker.stop_called == 1
    assert m._net is None


def test_status_monitor_start_with_existing_worker(monkeypatch):
    fake_worker = types.SimpleNamespace(start_called=0)

    class FakeWorker:
        def start(self):
            fake_worker.start_called += 1

    m = monitor.StatusMonitor(lambda *_args: None, app_after=lambda _d, cb: cb(), interval_ms=5)
    m._net = FakeWorker()
    m.start()
    assert fake_worker.start_called == 1


def test_status_monitor_start_handles_worker_error(monkeypatch, caplog):
    class BoomWorker:
        def __init__(self, callback, interval_ms):
            pass

        def start(self):
            raise RuntimeError("fail")

    m = monitor.StatusMonitor(lambda *_args: None, app_after=lambda _d, cb: cb(), interval_ms=5)
    monkeypatch.setattr(monitor, "_NetStatusWorker", BoomWorker)

    with caplog.at_level("DEBUG", logger=monitor.log.name):
        m.start()
    assert any("falha ao iniciar" in rec.getMessage() for rec in caplog.records)


def test_status_monitor_stop_handles_worker_error(monkeypatch, caplog):
    class BoomWorker:
        def stop(self):
            raise RuntimeError("fail")

    m = monitor.StatusMonitor(lambda *_args: None, app_after=lambda _d, cb: cb(), interval_ms=5)
    m._net = BoomWorker()
    with caplog.at_level("DEBUG", logger=monitor.log.name):
        m.stop()
    assert m._net is None
    assert any("falha ao parar" in rec.getMessage() for rec in caplog.records)


def test_status_monitor_stop_without_worker():
    m = monitor.StatusMonitor(lambda *_args: None, app_after=lambda _d, cb: cb(), interval_ms=5)
    m._net = None
    m.stop()  # should not raise and keep None


def test_set_cloud_only_and_status(monkeypatch):
    texts = []
    m = monitor.StatusMonitor(
        lambda text, online=None: texts.append((text, online)), app_after=lambda _d, cb: cb(), interval_ms=5
    )
    m.set_cloud_only(True)
    m.set_cloud_status(False)
    assert texts[-1][1] is False


def test_merge_status_text_branches():
    assert "verificando" in monitor.StatusMonitor.merge_status_text("Env", None)
    assert "online" in monitor.StatusMonitor.merge_status_text("Env", True)
    assert "offline" in monitor.StatusMonitor.merge_status_text("Env", False)


def test_env_text_branches():
    assert monitor.StatusMonitor.env_text(True) == "Nuvem"
    assert monitor.StatusMonitor.env_text(False) == "Local"
    assert monitor.StatusMonitor.env_text(None) == "Local"
