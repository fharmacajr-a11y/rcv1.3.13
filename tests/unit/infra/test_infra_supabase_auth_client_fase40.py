# tests/test_infra_supabase_auth_client_fase40.py
"""
Testes para infra/supabase/auth_client.py.
Foco: bind_postgrest_auth_if_any cobre fluxos com/sem token e erro ao aplicar.

FASE 8: Marcado como integration — excluído do default.
"""

from __future__ import annotations

import importlib
import logging
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

_supabase_available = importlib.util.find_spec("supabase") is not None

pytestmark = [
    pytest.mark.integration,
    pytest.mark.supabase,
    pytest.mark.skipif(not _supabase_available, reason="supabase package not installed"),
]


@pytest.fixture
def auth_client_module(monkeypatch):
    """Isola o import com stub de data.auth_bootstrap para controlar o token."""
    stub_bootstrap = ModuleType("src.db.auth_bootstrap")
    stub_bootstrap._get_access_token = MagicMock()
    monkeypatch.setitem(sys.modules, "src.db.auth_bootstrap", stub_bootstrap)
    sys.modules.pop("src.infra.supabase.auth_client", None)
    module = importlib.import_module("src.infra.supabase.auth_client")
    return module


def test_bind_postgrest_auth_without_token(auth_client_module, monkeypatch, caplog):
    auth_client = auth_client_module
    client = SimpleNamespace(postgrest=MagicMock())
    auth_client._get_access_token = MagicMock(return_value=None)
    # Ensure stub is used
    monkeypatch.setattr(sys.modules["src.db.auth_bootstrap"], "_get_access_token", auth_client._get_access_token)

    with caplog.at_level(logging.DEBUG):
        auth_client.bind_postgrest_auth_if_any(client)

    auth_client._get_access_token.assert_called_once_with(client)
    client.postgrest.auth.assert_not_called()
    assert any("sem token" in msg for msg in caplog.messages)


def test_bind_postgrest_auth_success(auth_client_module, monkeypatch, caplog):
    auth_client = auth_client_module
    client = SimpleNamespace(postgrest=MagicMock())
    auth_client._get_access_token = MagicMock(return_value="token-123")
    monkeypatch.setattr(sys.modules["src.db.auth_bootstrap"], "_get_access_token", auth_client._get_access_token)

    with caplog.at_level(logging.INFO):
        auth_client.bind_postgrest_auth_if_any(client)

    client.postgrest.auth.assert_called_once_with("token-123")
    assert any("token aplicado" in msg for msg in caplog.messages)


def test_bind_postgrest_auth_handles_errors(auth_client_module, monkeypatch, caplog):
    auth_client = auth_client_module
    failing_postgrest = MagicMock()
    failing_postgrest.auth.side_effect = RuntimeError("postgrest down")
    client = SimpleNamespace(postgrest=failing_postgrest)
    auth_client._get_access_token = MagicMock(return_value="token-err")
    monkeypatch.setattr(sys.modules["src.db.auth_bootstrap"], "_get_access_token", auth_client._get_access_token)

    with caplog.at_level(logging.WARNING):
        auth_client.bind_postgrest_auth_if_any(client)

    failing_postgrest.auth.assert_called_once_with("token-err")
    assert any("auth falhou" in msg for msg in caplog.messages)
