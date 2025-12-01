from __future__ import annotations

import types

import src.core.api.router as router


def test_register_endpoints_returns_same_app_instance():
    app = object()

    assert router.register_endpoints(app) is app


def test_register_endpoints_tolerates_module_overrides(monkeypatch):
    app = types.SimpleNamespace(value=42)

    monkeypatch.setattr(router, "api_clients", object())
    monkeypatch.setattr(router, "api_files", object())
    monkeypatch.setattr(router, "api_notes", object())

    returned = router.register_endpoints(app)

    assert returned is app
    assert returned.value == 42
