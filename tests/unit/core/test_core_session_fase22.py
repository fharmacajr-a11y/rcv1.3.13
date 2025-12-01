from __future__ import annotations

import types

from src.core.session import session


def setup_function():
    session.clear_current_user()
    session.set_tokens(None, None)


class DummyQuery:
    def __init__(self):
        self.filters: list[tuple[str, object]] = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self


def test_refresh_current_user_no_user(monkeypatch):
    monkeypatch.setattr(
        session,
        "supabase",
        types.SimpleNamespace(auth=types.SimpleNamespace(get_session=lambda: types.SimpleNamespace(user=None))),
    )
    called = {"n": 0}
    monkeypatch.setattr(session, "exec_postgrest", lambda q: called.update(n=called["n"] + 1))

    session.refresh_current_user_from_supabase()
    assert session.get_current_user() is None
    assert called["n"] == 0


def test_refresh_current_user_prefers_owner(monkeypatch):
    dummy_query = DummyQuery()

    def table(name: str):
        assert name == "memberships"
        return dummy_query

    def exec_fn(query):
        assert dummy_query.filters == [("user_id", "u1")]
        return types.SimpleNamespace(
            data=[
                {"org_id": "org_other", "role": "viewer"},
                {"org_id": "org_owner", "role": "Owner"},
            ]
        )

    supabase_stub = types.SimpleNamespace(
        auth=types.SimpleNamespace(
            get_session=lambda: types.SimpleNamespace(user=types.SimpleNamespace(id="u1", email="e@x"))
        ),
        table=table,
    )
    monkeypatch.setattr(session, "supabase", supabase_stub)
    monkeypatch.setattr(session, "exec_postgrest", exec_fn)

    session.refresh_current_user_from_supabase()
    cu = session.get_current_user()
    assert cu is not None
    assert cu.uid == "u1"
    assert cu.email == "e@x"
    assert cu.org_id == "org_owner"


def test_refresh_current_user_first_when_no_owner(monkeypatch):
    dummy_query = DummyQuery()
    monkeypatch.setattr(
        session,
        "supabase",
        types.SimpleNamespace(
            auth=types.SimpleNamespace(
                get_session=lambda: types.SimpleNamespace(user=types.SimpleNamespace(id="u2", email="b@y"))
            ),
            table=lambda name: dummy_query,
        ),
    )
    monkeypatch.setattr(
        session,
        "exec_postgrest",
        lambda q: types.SimpleNamespace(data=[{"org_id": "first", "role": "viewer"}]),
    )
    session.refresh_current_user_from_supabase()
    cu = session.get_current_user()
    assert cu.org_id == "first"


def test_set_and_clear_tokens_and_session():
    assert session.get_tokens() == (None, None)
    session.set_tokens("a", "r")
    assert session.get_tokens() == ("a", "r")
    session.set_current_user("user@test")
    assert session.get_current_user() is not None
    session.clear_current_user()
    assert session.get_current_user() is None


def test_get_session_combines_user_and_tokens():
    session.set_current_user("user@example.com")
    session.set_tokens("access123", "refresh123")
    sess = session.get_session()
    assert sess.email == "user@example.com"
    assert sess.org_id is None
    assert sess.access_token == "access123"
    assert sess.refresh_token == "refresh123"
