from __future__ import annotations

import importlib
from types import ModuleType

import src.core.settings as settings


def reload_settings() -> ModuleType:
    return importlib.reload(settings)


def test_defaults_are_used_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("APP_DEFAULT_PASSWORD", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    reloaded = reload_settings()

    assert reloaded.DEFAULT_PASSWORD == ""
    assert reloaded.SUPABASE_URL == ""
    assert reloaded.SUPABASE_KEY == ""


def test_env_values_are_respected(monkeypatch) -> None:
    monkeypatch.setenv("APP_DEFAULT_PASSWORD", "secret")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "service-key")

    reloaded = reload_settings()

    assert reloaded.DEFAULT_PASSWORD == "secret"
    assert reloaded.SUPABASE_URL == "https://example.supabase.co"
    assert reloaded.SUPABASE_KEY == "service-key"
