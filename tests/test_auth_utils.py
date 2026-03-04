# -*- coding: utf-8 -*-
"""Tests for src.utils.auth_utils — PR21: coverage step 2.

Covers:
- current_user_id: normal user, dict response, exception, None
- resolve_org_id: from memberships, env fallback, RuntimeError

No real network calls — supabase client is always mocked.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.utils.auth_utils import current_user_id, resolve_org_id


# ===========================================================================
# current_user_id
# ===========================================================================
class TestCurrentUserId:
    @patch("src.utils.auth_utils.supabase")
    def test_returns_user_id(self, mock_sb: MagicMock) -> None:
        user = MagicMock()
        user.id = "uuid-123"
        resp = MagicMock()
        resp.user = user
        mock_sb.auth.get_user.return_value = resp

        assert current_user_id() == "uuid-123"

    @patch("src.utils.auth_utils.supabase")
    def test_dict_response(self, mock_sb: MagicMock) -> None:
        mock_sb.auth.get_user.return_value = {"user": {"id": "dict-uuid"}}

        assert current_user_id() == "dict-uuid"

    @patch("src.utils.auth_utils.supabase")
    def test_returns_none_on_exception(self, mock_sb: MagicMock) -> None:
        mock_sb.auth.get_user.side_effect = RuntimeError("network down")

        assert current_user_id() is None

    @patch("src.utils.auth_utils.supabase")
    def test_returns_none_when_no_user(self, mock_sb: MagicMock) -> None:
        resp = MagicMock()
        resp.user = None
        mock_sb.auth.get_user.return_value = resp

        assert current_user_id() is None


# ===========================================================================
# resolve_org_id
# ===========================================================================
class TestResolveOrgId:
    @patch("src.utils.auth_utils.exec_postgrest")
    @patch("src.utils.auth_utils.current_user_id", return_value="uid-1")
    @patch("src.utils.auth_utils.supabase")
    def test_from_memberships(self, mock_sb: MagicMock, _uid: MagicMock, mock_pg: MagicMock) -> None:
        result = MagicMock()
        result.data = [{"org_id": "org-abc"}]
        mock_pg.return_value = result

        assert resolve_org_id() == "org-abc"

    @patch("src.utils.auth_utils.exec_postgrest")
    @patch("src.utils.auth_utils.current_user_id", return_value="uid-1")
    @patch("src.utils.auth_utils.supabase")
    @patch.dict(os.environ, {"SUPABASE_DEFAULT_ORG": "env-org-99"})
    def test_fallback_to_env(self, mock_sb: MagicMock, _uid: MagicMock, mock_pg: MagicMock) -> None:
        # memberships returns empty
        result = MagicMock()
        result.data = []
        mock_pg.return_value = result

        assert resolve_org_id() == "env-org-99"

    @patch("src.utils.auth_utils.current_user_id", return_value=None)
    @patch.dict(os.environ, {}, clear=True)
    def test_raises_when_no_user_no_env(self, _uid: MagicMock) -> None:
        # Ensure SUPABASE_DEFAULT_ORG is not set
        os.environ.pop("SUPABASE_DEFAULT_ORG", None)
        with pytest.raises(RuntimeError, match="não autenticado"):
            resolve_org_id()

    @patch("src.utils.auth_utils.exec_postgrest")
    @patch("src.utils.auth_utils.current_user_id", return_value="uid-1")
    @patch("src.utils.auth_utils.supabase")
    @patch.dict(os.environ, {"SUPABASE_DEFAULT_ORG": "fallback-org"})
    def test_memberships_exception_falls_back(self, mock_sb: MagicMock, _uid: MagicMock, mock_pg: MagicMock) -> None:
        mock_pg.side_effect = RuntimeError("DB down")
        assert resolve_org_id() == "fallback-org"

    @patch("src.utils.auth_utils.exec_postgrest")
    @patch("src.utils.auth_utils.current_user_id", return_value="uid-1")
    @patch("src.utils.auth_utils.supabase")
    @patch.dict(os.environ, {}, clear=True)
    def test_memberships_exception_no_fallback_raises(
        self, mock_sb: MagicMock, _uid: MagicMock, mock_pg: MagicMock
    ) -> None:
        os.environ.pop("SUPABASE_DEFAULT_ORG", None)
        mock_pg.side_effect = RuntimeError("DB down")
        result = MagicMock()
        result.data = []
        # Even though pg raises, we still need the empty path to fail
        with pytest.raises(RuntimeError, match="Não foi possível resolver"):
            resolve_org_id()
