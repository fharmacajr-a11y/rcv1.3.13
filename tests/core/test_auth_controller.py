from __future__ import annotations

import sys
import types

import pytest

from src.core.auth_controller import AuthController


def _make_controller(callback_list: list[str | None] | None = None) -> AuthController:
    if callback_list is None:
        callback_list = []
    return AuthController(on_user_change=lambda user: callback_list.append(user))


def test_set_current_user_updates_session_and_callback(monkeypatch):
    recorded_session_values: list[str | None] = []
    fake_session_module = types.SimpleNamespace(
        set_user=lambda value: recorded_session_values.append(value),
    )
    monkeypatch.setitem(sys.modules, "src.core.session", fake_session_module)
    callbacks: list[str | None] = []
    controller = _make_controller(callbacks)

    controller.set_current_user("alice@example.com")

    assert controller.current_user() == "alice@example.com"
    assert recorded_session_values == ["alice@example.com"]
    assert callbacks == ["alice@example.com"]


def test_set_current_user_handles_missing_session_module(monkeypatch):
    monkeypatch.delitem(sys.modules, "src.core.session", raising=False)
    controller = AuthController()

    controller.set_current_user("bob@example.com")

    assert controller.current_user() == "bob@example.com"


def test_set_user_data_updates_state_and_fires_callback():
    callbacks: list[str | None] = []
    controller = _make_controller(callbacks)
    payload = {
        "email": "user@example.com",
        "org_id": "org-123",
        "claims": {"org_id": "claim-org"},
    }

    controller.set_user_data(payload)

    assert controller.is_authenticated
    assert controller.get_email() == "user@example.com"
    assert controller.get_org_id() == "org-123"
    assert callbacks[-1] == "user@example.com"


def test_set_user_data_none_resets_user_and_auth_state():
    callbacks: list[str | None] = []
    controller = _make_controller(callbacks)
    controller.set_user_data({"email": "initial@example.com"})

    controller.set_user_data(None)

    assert controller.current_user() is None
    assert not controller.is_authenticated
    assert callbacks[-1] is None


def test_get_email_falls_back_to_current_user():
    controller = AuthController()
    controller.set_current_user("fallback@example.com")

    assert controller.get_email() == "fallback@example.com"


def test_get_email_handles_invalid_user_data():
    controller = AuthController()
    controller._user_data = object()  # type: ignore[attr-defined]

    assert controller.get_email() is None


def test_get_org_id_prefers_claims_when_field_missing():
    controller = AuthController()
    controller.set_user_data({"email": "foo", "claims": {"org_id": "from-claims"}})

    assert controller.get_org_id() == "from-claims"


def test_get_org_id_returns_none_without_data():
    controller = AuthController()

    assert controller.get_org_id() is None


def test_get_user_id_prefers_id_over_uid():
    controller = AuthController()
    controller.set_user_data({"email": "foo", "id": "user-id", "uid": "alt-uid"})

    assert controller.get_user_id() == "user-id"


def test_get_user_id_uses_uid_when_id_missing():
    controller = AuthController()
    controller.set_user_data({"email": "foo", "uid": "alt-uid"})

    assert controller.get_user_id() == "alt-uid"


def test_clear_resets_user_and_data():
    controller = AuthController()
    controller.set_user_data({"email": "foo"})

    controller.clear()

    assert controller.current_user() is None
    assert not controller.is_authenticated


def test_require_returns_existing_user(monkeypatch):
    controller = AuthController()
    controller.set_current_user("existing@example.com")

    result = controller.require(lambda: pytest.fail("launcher should not run"))  # pragma: no cover

    assert result == "existing@example.com"


def test_require_invokes_launcher_and_sets_user():
    controller = AuthController()
    calls: list[None] = []

    def launcher() -> str:
        calls.append(None)
        return "launched@example.com"

    result = controller.require(launcher)

    assert calls == [None]
    assert result == "launched@example.com"
    assert controller.current_user() == "launched@example.com"


def test_require_returns_none_when_launcher_fails():
    controller = AuthController()

    def launcher() -> str:
        raise RuntimeError("boom")

    assert controller.require(launcher) is None
    assert controller.current_user() is None
