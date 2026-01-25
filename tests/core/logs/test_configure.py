from __future__ import annotations

import importlib
import logging

import src.core.logs.configure as configure


def reload_configure_module():
    return importlib.reload(configure)


def test_configure_logging_uses_default_level_and_adds_filter(monkeypatch):
    cfg = reload_configure_module()
    recorded = {}

    monkeypatch.setattr(cfg.logging, "basicConfig", lambda **kwargs: recorded.update(kwargs))
    monkeypatch.setattr(cfg, "env_str", lambda key: "")

    cfg.configure_logging()

    assert recorded["level"] == cfg.logging.INFO
    assert "%(levelname)s" in recorded["format"]
    root = logging.getLogger()
    assert any(isinstance(flt, cfg.RedactSensitiveData) for flt in root.filters)


def test_configure_logging_respects_env_level(monkeypatch):
    cfg = reload_configure_module()
    recorded = {}

    monkeypatch.setattr(cfg.logging, "basicConfig", lambda **kwargs: recorded.update(kwargs))
    monkeypatch.setattr(cfg, "env_str", lambda key: "debug")

    cfg.configure_logging()

    assert recorded["level"] == cfg.logging.DEBUG


def test_configure_logging_parameter_overrides_env(monkeypatch):
    cfg = reload_configure_module()
    recorded = {}

    monkeypatch.setattr(cfg.logging, "basicConfig", lambda **kwargs: recorded.update(kwargs))
    monkeypatch.setattr(cfg, "env_str", lambda key: "error")

    cfg.configure_logging(level="warning")

    assert recorded["level"] == cfg.logging.WARNING


def test_configure_logging_runs_only_once(monkeypatch):
    cfg = reload_configure_module()
    monkeypatch.setattr(cfg, "env_str", lambda key: "")

    calls = []

    def fake_basic(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(cfg.logging, "basicConfig", fake_basic)

    cfg.configure_logging()
    cfg.configure_logging()

    assert len(calls) == 1
