"""LEGACY TEST - Auth Bootstrap GUI"""

import os
import pytest
from datetime import datetime, timezone

pytestmark = [pytest.mark.legacy_ui]

from src.core import auth_bootstrap
from src.utils import prefs as prefs_module

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )


def test_ensure_logged_with_persisted_session_initializes_org(monkeypatch, tk_root_session):
    data = {
        "access_token": "tok-access",
        "refresh_token": "tok-refresh",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "keep_logged": True,
    }
    monkeypatch.setattr("src.utils.prefs.load_auth_session", lambda: data)
    monkeypatch.setattr("src.utils.prefs.clear_auth_session", lambda: None)

    class DummyAuth:
        def __init__(self):
            self.last_session = None

        def set_session(self, access_token, refresh_token):
            self.last_session = (access_token, refresh_token)

            class DummyResponse:
                session = object()

            return DummyResponse()

        def get_session(self):
            class DummySession:
                def __init__(self):
                    self.access_token = "tok-access"
                    self.refresh_token = "tok-refresh"
                    self.user = type("U", (), {"id": "uid-1", "email": "user@test.com"})

            return DummySession()

    class DummyClient:
        def __init__(self):
            self.auth = DummyAuth()

    client = DummyClient()
    monkeypatch.setattr("src.core.auth_bootstrap.get_supabase", lambda: client)
    monkeypatch.setattr("src.core.auth_bootstrap.bind_postgrest_auth_if_any", lambda _c: None)

    from src.core.session import session as session_module

    original_current_user = getattr(session_module, "_CURRENT_USER", None)

    def fake_refresh():
        session_module._CURRENT_USER = session_module.CurrentUser(uid="u1", email="e@test.com", org_id="org-1")  # type: ignore[attr-defined]

    refresh_called = {"ok": False}

    def wrapped_refresh():
        refresh_called["ok"] = True
        fake_refresh()

    monkeypatch.setattr("src.core.auth_bootstrap.refresh_current_user_from_supabase", wrapped_refresh)

    class DummyFooter:
        def set_user(self, email):
            self.email = email

        def set_cloud(self, state):
            self.state = state

    class DummyApp:
        def __init__(self, master):
            self._root = master
            self.tk = master.tk
            self._status_monitor = None
            self.footer = DummyFooter()

        def deiconify(self):
            self.deiconified = True

        def _update_user_status(self):
            self.status_updated = True

    app = DummyApp(tk_root_session)

    try:
        ok = auth_bootstrap.ensure_logged(app)
        assert ok is True
        assert refresh_called["ok"] is True
        current = session_module.get_current_user()
        assert current is not None
        assert current.org_id == "org-1"
    finally:
        session_module._CURRENT_USER = original_current_user  # type: ignore[attr-defined]
        prefs_module.clear_auth_session()
