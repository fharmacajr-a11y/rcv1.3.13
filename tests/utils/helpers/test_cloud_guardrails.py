from __future__ import annotations

import importlib
from types import SimpleNamespace


def reload_module(monkeypatch, cloud_only: bool):
    """Reload guardrails with a chosen CLOUD_ONLY value."""
    # Remove cached module to re-evaluate CLOUD_ONLY
    monkeypatch.delitem(importlib.sys.modules, "src.config.paths", raising=False)
    monkeypatch.setitem(
        importlib.sys.modules,
        "src.config.paths",
        SimpleNamespace(CLOUD_ONLY=cloud_only),
    )
    return importlib.reload(importlib.import_module("src.utils.helpers.cloud_guardrails"))


def test_allows_operation_when_not_cloud_only(monkeypatch):
    # Stub messagebox.showinfo to capture calls
    calls = []
    monkeypatch.setitem(
        importlib.sys.modules,
        "tkinter",
        SimpleNamespace(messagebox=SimpleNamespace(showinfo=lambda *args, **kwargs: calls.append((args, kwargs)))),
    )
    module = reload_module(monkeypatch, cloud_only=False)

    blocked = module.check_cloud_only_block("Operação teste")

    assert blocked is False
    assert calls == []


def test_blocks_and_shows_message_when_cloud_only(monkeypatch):
    calls = []
    monkeypatch.setitem(
        importlib.sys.modules,
        "tkinter",
        SimpleNamespace(messagebox=SimpleNamespace(showinfo=lambda *args, **kwargs: calls.append((args, kwargs)))),
    )
    module = reload_module(monkeypatch, cloud_only=True)

    blocked = module.check_cloud_only_block("Operação crítica")

    assert blocked is True
    assert len(calls) == 1
    args, kwargs = calls[0]
    # args[0] = title, args[1] = message
    assert "Cloud-Only" in args[1]
    assert "Operação crítica" in args[1]


def test_handles_missing_config_paths(monkeypatch):
    # Remove config.paths to simulate missing dependency; module should default via reload helper
    monkeypatch.delitem(importlib.sys.modules, "src.config.paths", raising=False)
    module = reload_module(monkeypatch, cloud_only=True)

    # Should still function and block
    calls = []
    module.messagebox = SimpleNamespace(showinfo=lambda *args, **kwargs: calls.append(args))

    assert module.check_cloud_only_block() is True
    assert calls  # message was shown
