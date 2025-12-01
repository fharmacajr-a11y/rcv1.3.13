from __future__ import annotations

import logging
import os
import sys
from datetime import timezone
from types import SimpleNamespace

import pytest

from src.core import bootstrap


class DummyLogger:
    def __init__(self, name: str) -> None:
        self.name = name
        self.records: list[tuple[str, str]] = []
        self.level = None

    def info(self, msg: str, *args) -> None:
        self.records.append(("info", msg % args if args else msg))

    def warning(self, msg: str, *args) -> None:
        self.records.append(("warning", msg % args if args else msg))

    def error(self, msg: str, *args) -> None:
        self.records.append(("error", msg % args if args else msg))

    def debug(self, msg: str, *args) -> None:
        self.records.append(("debug", msg % args if args else msg))

    def setLevel(self, level: int) -> None:  # noqa: N802 (matching logging API)
        self.level = level


class DummyFooter:
    def __init__(self) -> None:
        self.cloud_status: list[str] = []

    def set_cloud(self, status: str) -> None:
        self.cloud_status.append(status)


class DummyApp:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, callable]] = []
        self.footer = DummyFooter()

    def after(self, delay_ms: int, callback) -> None:
        self.after_calls.append((delay_ms, callback))


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)
    yield
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)


def test_configure_environment_sets_default_and_loads_dotenv(monkeypatch):
    calls: list[tuple[str, bool]] = []
    monkeypatch.setitem(
        sys.modules,
        "dotenv",
        SimpleNamespace(load_dotenv=lambda path, override: calls.append((path, override))),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.utils.resource_path",
        SimpleNamespace(resource_path=lambda name: f"/bundle/{name}"),
    )

    bootstrap.configure_environment()

    assert os.environ["RC_NO_LOCAL_FS"] == "1"
    assert calls == [
        ("/bundle/.env", False),
        (os.path.join(os.getcwd(), ".env"), True),
    ]


def test_configure_environment_ignores_dotenv_errors(monkeypatch):
    def failing_load(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "dotenv", SimpleNamespace(load_dotenv=failing_load))
    monkeypatch.setitem(
        sys.modules,
        "src.utils.resource_path",
        SimpleNamespace(resource_path=lambda name: f"/bundle/{name}"),
    )

    bootstrap.configure_environment()  # should not raise despite exception
    assert os.environ["RC_NO_LOCAL_FS"] == "1"


def test_configure_logging_preload_only(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setitem(
        sys.modules,
        "src.core.logs.configure",
        SimpleNamespace(configure_logging=lambda: calls.append(True)),
    )

    assert bootstrap.configure_logging(preload=True) is None
    assert calls == [True]


def test_configure_logging_returns_configured_logger(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "src.core.logs.configure",
        SimpleNamespace(configure_logging=lambda: None),
    )
    monkeypatch.setattr(bootstrap.logging, "basicConfig", lambda **_kwargs: None)
    tz_calls = {"count": 0}

    def fake_get_localzone():
        tz_calls["count"] += 1
        return timezone.utc

    monkeypatch.setitem(
        sys.modules,
        "tzlocal",
        SimpleNamespace(get_localzone=fake_get_localzone),
    )

    logger = bootstrap.configure_logging(preload=False)

    assert logger is logging.getLogger("startup")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    assert tz_calls["count"] == 1


def test_configure_hidpi_calls_helper(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setitem(
        sys.modules,
        "src.utils.helpers",
        SimpleNamespace(configure_hidpi_support=lambda: calls.append(True)),
    )

    bootstrap.configure_hidpi()

    assert calls == [True]


def test_configure_hidpi_swallow_errors(monkeypatch):
    def boom():
        raise RuntimeError("hidpi fail")

    monkeypatch.setitem(
        sys.modules,
        "src.utils.helpers",
        SimpleNamespace(configure_hidpi_support=boom),
    )

    bootstrap.configure_hidpi()  # should not raise


def test_run_initial_healthcheck_success(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "src.utils.network",
        SimpleNamespace(require_internet_or_alert=lambda: True),
    )

    assert bootstrap.run_initial_healthcheck(logger=None) is True


def test_run_initial_healthcheck_failure_logs(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "src.utils.network",
        SimpleNamespace(require_internet_or_alert=lambda: False),
    )
    logger = DummyLogger("health")

    assert bootstrap.run_initial_healthcheck(logger=logger) is False
    assert any("Internet check failed" in msg for _, msg in logger.records)


def test_run_initial_healthcheck_handles_exception(monkeypatch):
    def boom():
        raise RuntimeError("offline")

    monkeypatch.setitem(
        sys.modules,
        "src.utils.network",
        SimpleNamespace(require_internet_or_alert=boom),
    )
    logger = DummyLogger("health")

    assert bootstrap.run_initial_healthcheck(logger=logger) is True
    assert any("Failed to check internet connectivity" in msg for _, msg in logger.records)


def install_network_module(monkeypatch, *, result=True, raises=False):
    state = {"calls": 0}

    def check_internet_connectivity(timeout: float) -> bool:
        state["calls"] += 1
        if raises:
            raise RuntimeError("net fail")
        return result

    monkeypatch.setitem(
        sys.modules,
        "src.utils.network",
        SimpleNamespace(
            require_internet_or_alert=lambda: True,
            check_internet_connectivity=check_internet_connectivity,
        ),
    )
    return state


def test_schedule_healthcheck_runs_when_cloud_only(monkeypatch):
    state = install_network_module(monkeypatch, result=True)
    app = DummyApp()
    monkeypatch.setattr(os, "getenv", lambda key: "1" if key == "RC_NO_LOCAL_FS" else "")
    logger = DummyLogger("health")

    bootstrap.schedule_healthcheck_after_gui(app, logger=logger)
    delay, callback = app.after_calls[0]
    assert delay == 500
    callback()

    assert state["calls"] == 1
    assert app.footer.cloud_status == ["online"]
    assert any("Internet OK" in msg for lvl, msg in logger.records if lvl == "info")


def test_schedule_healthcheck_skips_when_not_cloud_only(monkeypatch):
    state = install_network_module(monkeypatch, result=True)
    app = DummyApp()
    monkeypatch.setattr(os, "getenv", lambda _key: "0")

    bootstrap.schedule_healthcheck_after_gui(app)
    _, callback = app.after_calls[0]
    callback()

    assert state["calls"] == 0
    assert app.footer.cloud_status == []


def test_schedule_healthcheck_handles_failures(monkeypatch):
    state = install_network_module(monkeypatch, raises=True)
    app = DummyApp()
    app.footer = DummyFooter()
    monkeypatch.setattr(os, "getenv", lambda _key: "1")
    logger = DummyLogger("health")

    bootstrap.schedule_healthcheck_after_gui(app, logger=logger)
    _, callback = app.after_calls[0]
    callback()  # should handle exception internally

    assert state["calls"] == 1
    # No status update due to exception
    assert app.footer.cloud_status == []
    assert any("Background health check failed" in msg for _, msg in logger.records)
