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


def test_register_endpoints_with_none():
    """Should handle None as app parameter."""
    result = router.register_endpoints(None)
    assert result is None


def test_register_endpoints_with_dict():
    """Should work with dict-like app objects."""
    app = {"name": "test", "debug": True}
    result = router.register_endpoints(app)
    assert result is app
    assert result["name"] == "test"


def test_register_endpoints_idempotent():
    """Should return same result when called multiple times."""
    app = types.SimpleNamespace(config="test")

    result1 = router.register_endpoints(app)
    result2 = router.register_endpoints(app)
    result3 = router.register_endpoints(app)

    assert result1 is app
    assert result2 is app
    assert result3 is app


def test_api_modules_are_imported():
    """Should have api modules imported and accessible."""
    # If imports failed, these would raise AttributeError
    assert hasattr(router, "api_clients")
    assert hasattr(router, "api_files")
    assert hasattr(router, "api_notes")


def test_register_endpoints_in_all():
    """Should export register_endpoints in __all__."""
    assert "register_endpoints" in router.__all__
