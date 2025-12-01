# tests/test_infra_supabase_auth_fase39.py
"""
Testes para infra/supabase_auth.py (COV-INFRA-SUPABASE).
Foco: cobrir fluxos felizes e de erro do login e logout.
"""

from __future__ import annotations

import importlib
import sys
import logging
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def supabase_auth_module(monkeypatch):
    """
    Isola o import de supabase_auth com um stub de infra.supabase_client
    para evitar dependencias pesadas e ciclos.
    """
    stub_client = ModuleType("infra.supabase_client")
    stub_client.get_supabase = MagicMock()
    stub_client.exec_postgrest = MagicMock()
    stub_client.supabase = MagicMock()
    monkeypatch.setitem(sys.modules, "infra.supabase_client", stub_client)
    sys.modules.pop("infra.supabase_auth", None)
    module = importlib.import_module("infra.supabase_auth")
    return module


def _make_fake_client(response) -> SimpleNamespace:
    fake_auth = MagicMock()
    fake_auth.sign_in_with_password.return_value = response
    return SimpleNamespace(auth=fake_auth)


def test_login_with_password_success(monkeypatch, supabase_auth_module):
    supabase_auth = supabase_auth_module
    access_token = "access-123"
    refresh_token = "refresh-456"
    fake_response = SimpleNamespace(session=SimpleNamespace(access_token=access_token, refresh_token=refresh_token))
    fake_client = _make_fake_client(fake_response)

    set_current_user = MagicMock()
    set_tokens = MagicMock()
    monkeypatch.setattr(supabase_auth, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(supabase_auth.session, "set_current_user", set_current_user)
    monkeypatch.setattr(supabase_auth.session, "set_tokens", set_tokens)

    returned_access, returned_refresh = supabase_auth.login_with_password("user@example.com", "secret")

    fake_client.auth.sign_in_with_password.assert_called_once_with({"email": "user@example.com", "password": "secret"})
    set_current_user.assert_called_once_with("user@example.com")
    set_tokens.assert_called_once_with(access_token, refresh_token)
    assert returned_access == access_token
    assert returned_refresh == refresh_token


def test_login_with_password_missing_session(monkeypatch, supabase_auth_module):
    supabase_auth = supabase_auth_module
    fake_client = _make_fake_client(None)
    set_current_user = MagicMock()
    set_tokens = MagicMock()
    monkeypatch.setattr(supabase_auth, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(supabase_auth.session, "set_current_user", set_current_user)
    monkeypatch.setattr(supabase_auth.session, "set_tokens", set_tokens)

    with pytest.raises(supabase_auth.AuthError) as exc:
        supabase_auth.login_with_password("user@example.com", "secret")

    assert "Falha ao autenticar" in str(exc.value)
    set_current_user.assert_not_called()
    set_tokens.assert_not_called()


def test_login_with_password_missing_access_token(monkeypatch, supabase_auth_module):
    supabase_auth = supabase_auth_module
    fake_response = SimpleNamespace(session=SimpleNamespace(access_token=None, refresh_token="refresh-only"))
    fake_client = _make_fake_client(fake_response)
    set_current_user = MagicMock()
    set_tokens = MagicMock()
    monkeypatch.setattr(supabase_auth, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(supabase_auth.session, "set_current_user", set_current_user)
    monkeypatch.setattr(supabase_auth.session, "set_tokens", set_tokens)

    with pytest.raises(supabase_auth.AuthError) as exc:
        supabase_auth.login_with_password("user@example.com", "secret")

    assert "access token" in str(exc.value)
    set_current_user.assert_not_called()
    set_tokens.assert_not_called()


def test_login_with_password_propagates_errors(monkeypatch, supabase_auth_module):
    supabase_auth = supabase_auth_module
    fake_auth = MagicMock()
    fake_auth.sign_in_with_password.side_effect = RuntimeError("network down")
    fake_client = SimpleNamespace(auth=fake_auth)
    monkeypatch.setattr(supabase_auth, "get_supabase", lambda: fake_client)

    with pytest.raises(supabase_auth.AuthError) as exc:
        supabase_auth.login_with_password("user@example.com", "secret")

    assert "network down" in str(exc.value)


def test_logout_signs_out_and_clears_state(monkeypatch, supabase_auth_module):
    supabase_auth = supabase_auth_module
    fake_auth = MagicMock()
    fake_client = SimpleNamespace(auth=fake_auth)
    set_tokens = MagicMock()
    clear_auth_session = MagicMock()
    monkeypatch.setattr(supabase_auth.session, "set_tokens", set_tokens)
    monkeypatch.setattr(supabase_auth.prefs_utils, "clear_auth_session", clear_auth_session)

    supabase_auth.logout(fake_client)

    fake_auth.sign_out.assert_called_once()
    set_tokens.assert_called_once_with(None, None)
    clear_auth_session.assert_called_once()


def test_logout_swallows_errors_and_still_cleans(monkeypatch, caplog, supabase_auth_module):
    supabase_auth = supabase_auth_module
    fake_auth = MagicMock()
    fake_auth.sign_out.side_effect = Exception("boom")
    fake_client = SimpleNamespace(auth=fake_auth)
    set_tokens = MagicMock()
    clear_auth_session = MagicMock()
    monkeypatch.setattr(supabase_auth, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(supabase_auth.session, "set_tokens", set_tokens)
    monkeypatch.setattr(supabase_auth.prefs_utils, "clear_auth_session", clear_auth_session)

    supabase_auth.logout()  # Usa get_supabase() patchado

    set_tokens.assert_called_once_with(None, None)
    clear_auth_session.assert_called_once()
    # Mesmo com excecao no sign_out, nada deve ser levantado
    assert "boom" in "".join(caplog.messages) or not caplog.messages  # Aceita log ou silencioso


def test_logout_logs_warning_when_clear_prefs_fails(monkeypatch, caplog, supabase_auth_module):
    supabase_auth = supabase_auth_module
    fake_auth = MagicMock()
    fake_client = SimpleNamespace(auth=fake_auth)
    set_tokens = MagicMock()
    monkeypatch.setattr(supabase_auth, "get_supabase", lambda: fake_client)
    monkeypatch.setattr(supabase_auth.session, "set_tokens", set_tokens)
    monkeypatch.setattr(supabase_auth.prefs_utils, "clear_auth_session", MagicMock(side_effect=Exception("disk error")))

    with caplog.at_level(logging.WARNING):
        supabase_auth.logout()  # clear_auth_session levantara excecao

    set_tokens.assert_called_once_with(None, None)
    assert any("Falha ao limpar" in msg for msg in caplog.messages)
