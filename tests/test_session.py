# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes unitários para src/core/session/session.py — sem rede/supabase real."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import src.core.session.session as _mod
from src.core.session.session import (
    CurrentUser,
    clear_current_user,
    get_current_user,
    get_session,
    get_tokens,
    refresh_current_user_from_supabase,
    set_current_user,
    set_tokens,
)

_SESSION_MOD = "src.core.session.session"


# ---------------------------------------------------------------------------
# Helpers para construir fakes mínimos
# ---------------------------------------------------------------------------

def _make_supabase_fake(uid: str, email: str, memberships: list[dict]) -> MagicMock:
    """
    Constrói um fake de supabase com:
      - supabase.auth.get_session() → objeto com .user
      - supabase.table(...).select(...).eq(...) → objeto chainable (retorna self)
    O resultado final de .eq() é passado para exec_postgrest, que é mockado
    separadamente via patch de _mod.exec_postgrest.
    """
    user = MagicMock()
    user.id = uid
    user.email = email

    sess_obj = MagicMock()
    sess_obj.user = user

    auth = MagicMock()
    auth.get_session.return_value = sess_obj

    # chainable: .table().select().eq()  — cada método retorna o próprio mock
    chainable = MagicMock()
    chainable.select.return_value = chainable
    chainable.eq.return_value = chainable

    sb = MagicMock()
    sb.auth = auth
    sb.table.return_value = chainable

    return sb


def _make_exec_postgrest_fake(rows: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.data = rows
    fn = MagicMock(return_value=resp)
    return fn


def _reset_state() -> None:
    """Devolve o módulo ao estado inicial entre testes."""
    _mod._CURRENT_USER = None
    _mod._TOKENS = _mod.Tokens()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestRefreshCurrentUser(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state()

    def tearDown(self) -> None:
        _reset_state()

    def test_owner_role_prioritized(self):
        """refresh define org_id priorizando role='owner'."""
        memberships = [
            {"org_id": "org-member", "role": "member"},
            {"org_id": "org-owner", "role": "owner"},
        ]
        sb_fake = _make_supabase_fake("uid-1", "user@test.com", memberships)
        ep_fake = _make_exec_postgrest_fake(memberships)

        with patch.object(_mod, "supabase", sb_fake), patch.object(_mod, "exec_postgrest", ep_fake):
            refresh_current_user_from_supabase()

        cu = get_current_user()
        self.assertIsNotNone(cu)
        self.assertEqual(cu.org_id, "org-owner")
        self.assertEqual(cu.uid, "uid-1")
        self.assertEqual(cu.email, "user@test.com")

    def test_first_row_used_when_no_owner(self):
        """Quando não há owner, usa a primeira linha."""
        memberships = [
            {"org_id": "org-first", "role": "member"},
            {"org_id": "org-second", "role": "admin"},
        ]
        sb_fake = _make_supabase_fake("uid-2", "a@b.com", memberships)
        ep_fake = _make_exec_postgrest_fake(memberships)

        with patch.object(_mod, "supabase", sb_fake), patch.object(_mod, "exec_postgrest", ep_fake):
            refresh_current_user_from_supabase()

        cu = get_current_user()
        self.assertIsNotNone(cu)
        self.assertEqual(cu.org_id, "org-first")

    def test_no_session_clears_user(self):
        """Sem sessão ativa, _CURRENT_USER deve ser None."""
        sb_fake = MagicMock()
        sb_fake.auth.get_session.return_value = MagicMock(user=None)

        with patch.object(_mod, "supabase", sb_fake):
            # Garante que havia algo antes
            _mod._CURRENT_USER = CurrentUser(uid="x", email="x@x.com")
            refresh_current_user_from_supabase()

        self.assertIsNone(get_current_user())

    def test_empty_memberships_sets_org_id_none(self):
        """Sem linhas de membership, org_id fica None."""
        sb_fake = _make_supabase_fake("uid-3", "c@d.com", [])
        ep_fake = _make_exec_postgrest_fake([])

        with patch.object(_mod, "supabase", sb_fake), patch.object(_mod, "exec_postgrest", ep_fake):
            refresh_current_user_from_supabase()

        cu = get_current_user()
        self.assertIsNotNone(cu)
        self.assertIsNone(cu.org_id)


class TestGetCurrentUserReturnsACopy(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state()

    def tearDown(self) -> None:
        _reset_state()

    def test_returns_copy_not_same_object(self):
        """get_current_user() deve retornar objeto distinto do interno."""
        _mod._CURRENT_USER = CurrentUser(uid="u", email="e@e.com", org_id="org-x")

        copy1 = get_current_user()
        copy2 = get_current_user()

        self.assertIsNotNone(copy1)
        self.assertIsNot(copy1, _mod._CURRENT_USER)
        self.assertIsNot(copy1, copy2)

    def test_mutating_copy_does_not_affect_internal_state(self):
        """Modificar o retorno de get_current_user não deve alterar _CURRENT_USER."""
        _mod._CURRENT_USER = CurrentUser(uid="u", email="e@e.com", org_id="org-original")

        copy = get_current_user()
        self.assertIsNotNone(copy)
        copy.org_id = "mutado"  # type: ignore[union-attr]

        # Estado interno deve permanecer intacto
        internal = _mod._CURRENT_USER
        self.assertEqual(internal.org_id, "org-original")

    def test_returns_none_when_not_set(self):
        self.assertIsNone(get_current_user())


class TestGetSessionConsistency(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state()

    def tearDown(self) -> None:
        _reset_state()

    def test_session_reflects_set_tokens_and_set_current_user(self):
        """get_session deve refletir tokens e user definidos atomicamente."""
        set_tokens("access-abc", "refresh-xyz")
        set_current_user("joao@empresa.com")

        sess = get_session()

        self.assertEqual(sess.email, "joao@empresa.com")
        self.assertEqual(sess.access_token, "access-abc")
        self.assertEqual(sess.refresh_token, "refresh-xyz")

    def test_session_empty_when_cleared(self):
        set_tokens("tok", "ref")
        set_current_user("user@x.com")
        clear_current_user()
        set_tokens(None, None)

        sess = get_session()

        self.assertEqual(sess.uid, "")
        self.assertEqual(sess.email, "")
        self.assertIsNone(sess.access_token)
        self.assertIsNone(sess.refresh_token)

    def test_session_user_and_tokens_are_consistent(self):
        """Tokens e user devem vir do mesmo snapshot (sem valores de estados diferentes)."""
        set_current_user("snapshot@x.com")
        set_tokens("tok-snap", "ref-snap")

        sess = get_session()

        self.assertEqual(sess.email, "snapshot@x.com")
        self.assertEqual(sess.access_token, "tok-snap")


class TestTokens(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state()

    def tearDown(self) -> None:
        _reset_state()

    def test_set_and_get_tokens(self):
        set_tokens("A", "B")
        at, rt = get_tokens()
        self.assertEqual(at, "A")
        self.assertEqual(rt, "B")

    def test_tokens_default_none(self):
        at, rt = get_tokens()
        self.assertIsNone(at)
        self.assertIsNone(rt)

    def test_overwrite_tokens(self):
        set_tokens("old-a", "old-r")
        set_tokens("new-a", "new-r")
        at, rt = get_tokens()
        self.assertEqual(at, "new-a")
        self.assertEqual(rt, "new-r")


class TestClearAndSetCurrentUser(unittest.TestCase):
    def setUp(self) -> None:
        _reset_state()

    def tearDown(self) -> None:
        _reset_state()

    def test_set_current_user_sets_email(self):
        set_current_user("foo@bar.com")
        cu = get_current_user()
        self.assertIsNotNone(cu)
        self.assertEqual(cu.email, "foo@bar.com")

    def test_clear_current_user(self):
        set_current_user("foo@bar.com")
        clear_current_user()
        self.assertIsNone(get_current_user())


if __name__ == "__main__":
    unittest.main()
