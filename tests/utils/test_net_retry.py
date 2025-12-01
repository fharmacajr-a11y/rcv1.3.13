from __future__ import annotations

import pytest

import src.utils.net_retry as net_retry


def test_run_cloud_op_success_first_try(monkeypatch):
    calls = {"op": 0, "ensure": 0, "sleep": []}
    monkeypatch.setattr(
        net_retry.SessionGuard, "ensure_alive", lambda: calls.__setitem__("ensure", calls["ensure"] + 1)
    )
    monkeypatch.setattr(net_retry.time, "sleep", lambda delay: calls["sleep"].append(delay))

    def op():
        calls["op"] += 1
        return "ok"

    result = net_retry.run_cloud_op(op, retries=2, base_delay=0.5)

    assert result == "ok"
    assert calls["op"] == 1
    assert calls["ensure"] == 0
    assert calls["sleep"] == []


def test_run_cloud_op_retry_then_success(monkeypatch):
    calls = {"op": 0, "ensure": 0, "sleep": []}

    monkeypatch.setattr(
        net_retry.SessionGuard, "ensure_alive", lambda: calls.__setitem__("ensure", calls["ensure"] + 1)
    )
    monkeypatch.setattr(net_retry.time, "sleep", lambda delay: calls["sleep"].append(delay))

    def op():
        calls["op"] += 1
        if calls["op"] < 3:
            raise RuntimeError("fail")
        return "ok"

    result = net_retry.run_cloud_op(op, retries=2, base_delay=0.5)

    assert result == "ok"
    assert calls["op"] == 3
    assert calls["ensure"] == 2  # called before each retry after the first
    assert calls["sleep"] == [0.5, 1.0]


def test_run_cloud_op_all_fail_raises_last(monkeypatch):
    calls = {"op": 0, "ensure": 0, "sleep": []}

    monkeypatch.setattr(
        net_retry.SessionGuard, "ensure_alive", lambda: calls.__setitem__("ensure", calls["ensure"] + 1)
    )
    monkeypatch.setattr(net_retry.time, "sleep", lambda delay: calls["sleep"].append(delay))

    def op():
        calls["op"] += 1
        raise ValueError(f"fail-{calls['op']}")

    with pytest.raises(ValueError) as excinfo:
        net_retry.run_cloud_op(op, retries=2, base_delay=0.25)

    assert "fail-3" in str(excinfo.value)
    assert calls["op"] == 3
    assert calls["ensure"] == 2
    assert calls["sleep"] == [0.25, 0.5]
