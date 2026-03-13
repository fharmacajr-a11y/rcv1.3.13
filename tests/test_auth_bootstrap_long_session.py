# -*- coding: utf-8 -*-
"""Regression tests para _register_token_refresh_persister.

Cobre:
- TOKEN_REFRESHED com keep_logged ativo → save_auth_session é chamado
- TOKEN_REFRESHED sem sessão persistida → save_auth_session NÃO é chamado
- Eventos não-TOKEN_REFRESHED → ignorados
- Registro duplo → persister não duplicado (flag _token_refresh_persister_registered)
- Falha em load_auth_session → não propaga exceção
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import src.core.auth_bootstrap as _mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(access: str = "new_access", refresh: str = "new_refresh") -> MagicMock:
    sess = MagicMock()
    sess.access_token = access
    sess.refresh_token = refresh
    return sess


def _make_client() -> MagicMock:
    """Cliente fake com auth.on_auth_state_change que guarda o callback."""
    client = MagicMock()
    client.auth.on_auth_state_change.return_value = MagicMock()
    return client


def _extract_registered_callback(client: MagicMock) -> Any:
    """Extrai o callback passado para on_auth_state_change."""
    assert client.auth.on_auth_state_change.called, "on_auth_state_change não foi chamado"
    return client.auth.on_auth_state_change.call_args[0][0]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_flag():
    """Reseta a flag global antes de cada teste para isolamento."""
    original = _mod._token_refresh_persister_registered
    _mod._token_refresh_persister_registered = False
    yield
    _mod._token_refresh_persister_registered = original


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterTokenRefreshPersister:
    def test_registers_callback_on_client(self) -> None:
        """Deve chamar on_auth_state_change exatamente uma vez."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        client.auth.on_auth_state_change.assert_called_once()

    def test_sets_flag_after_registration(self) -> None:
        """Flag global deve ser True após registro bem-sucedido."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        assert _mod._token_refresh_persister_registered is True

    def test_second_call_is_no_op(self) -> None:
        """Registro duplo não deve registrar segundo callback."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        _mod._register_token_refresh_persister(client)
        assert client.auth.on_auth_state_change.call_count == 1

    def test_token_refreshed_with_keep_logged_persists_tokens(self) -> None:
        """TOKEN_REFRESHED com keep_logged=True → save_auth_session chamado."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        existing_session = {"keep_logged": True, "access_token": "old_a", "refresh_token": "old_r"}
        new_session = _make_session("new_a", "new_r")

        with patch.object(_mod.prefs_utils, "load_auth_session", return_value=existing_session):
            with patch.object(_mod.prefs_utils, "save_auth_session") as mock_save:
                callback("TOKEN_REFRESHED", new_session)
                mock_save.assert_called_once_with("new_a", "new_r", keep_logged=True)

    def test_token_refreshed_without_persistent_session_does_not_persist(self) -> None:
        """TOKEN_REFRESHED sem sessão persistida → save_auth_session NÃO chamado."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        new_session = _make_session()

        with patch.object(_mod.prefs_utils, "load_auth_session", return_value={}):
            with patch.object(_mod.prefs_utils, "save_auth_session") as mock_save:
                callback("TOKEN_REFRESHED", new_session)
                mock_save.assert_not_called()

    def test_token_refreshed_with_keep_logged_false_does_not_persist(self) -> None:
        """keep_logged=False → save_auth_session NÃO chamado."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        existing_session = {"keep_logged": False, "access_token": "a", "refresh_token": "r"}
        new_session = _make_session()

        with patch.object(_mod.prefs_utils, "load_auth_session", return_value=existing_session):
            with patch.object(_mod.prefs_utils, "save_auth_session") as mock_save:
                callback("TOKEN_REFRESHED", new_session)
                mock_save.assert_not_called()

    def test_other_event_types_are_ignored(self) -> None:
        """Eventos diferentes de TOKEN_REFRESHED são ignorados silenciosamente."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        with patch.object(_mod.prefs_utils, "load_auth_session") as mock_load:
            with patch.object(_mod.prefs_utils, "save_auth_session") as mock_save:
                callback("SIGNED_IN", _make_session())
                callback("SIGNED_OUT", None)
                callback("USER_UPDATED", _make_session())
                mock_load.assert_not_called()
                mock_save.assert_not_called()

    def test_none_session_in_token_refreshed_is_ignored(self) -> None:
        """TOKEN_REFRESHED com session=None → ignorado."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        with patch.object(_mod.prefs_utils, "save_auth_session") as mock_save:
            callback("TOKEN_REFRESHED", None)
            mock_save.assert_not_called()

    def test_load_auth_session_failure_does_not_propagate(self) -> None:
        """Falha em load_auth_session não deve levantar exceção para o caller."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        with patch.object(_mod.prefs_utils, "load_auth_session", side_effect=RuntimeError("disk error")):
            with patch.object(_mod.prefs_utils, "save_auth_session") as mock_save:
                callback("TOKEN_REFRESHED", _make_session())  # não deve levantar
                mock_save.assert_not_called()

    def test_save_auth_session_failure_does_not_propagate(self) -> None:
        """Falha em save_auth_session não deve levantar exceção para o caller."""
        client = _make_client()
        _mod._register_token_refresh_persister(client)
        callback = _extract_registered_callback(client)

        existing_session = {"keep_logged": True}
        with patch.object(_mod.prefs_utils, "load_auth_session", return_value=existing_session):
            with patch.object(_mod.prefs_utils, "save_auth_session", side_effect=OSError("keyring fail")):
                callback("TOKEN_REFRESHED", _make_session())  # não deve levantar

    def test_on_auth_state_change_failure_is_silenced(self) -> None:
        """Falha em on_auth_state_change não deve propagar exceção."""
        client = MagicMock()
        client.auth.on_auth_state_change.side_effect = AttributeError("unsupported")
        _mod._register_token_refresh_persister(client)  # não deve levantar
        assert _mod._token_refresh_persister_registered is False
