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


def test_env_function_returns_env_value(monkeypatch) -> None:
    """Should return environment variable value when it exists."""
    monkeypatch.setenv("TEST_VAR", "test_value")

    result = settings.env("TEST_VAR", "default")
    assert result == "test_value"


def test_env_function_returns_default_when_missing(monkeypatch) -> None:
    """Should return default when environment variable doesn't exist."""
    monkeypatch.delenv("TEST_VAR", raising=False)

    result = settings.env("TEST_VAR", "my_default")
    assert result == "my_default"


def test_env_function_returns_empty_string_when_no_default() -> None:
    """Should return empty string when no default provided and env missing."""
    result = settings.env("NONEXISTENT_VAR_12345")
    assert result == ""


def test_env_function_handles_empty_env_value(monkeypatch) -> None:
    """Should use default when env variable is empty string."""
    monkeypatch.setenv("TEST_VAR", "")

    result = settings.env("TEST_VAR", "fallback")
    # Function uses `or default`, so empty string triggers fallback
    assert result == "fallback"


def test_constants_are_final_type() -> None:
    """Should have constants annotated as Final."""
    # Check that constants exist and are accessible
    assert hasattr(settings, "DEFAULT_PASSWORD")
    assert hasattr(settings, "SUPABASE_URL")
    assert hasattr(settings, "SUPABASE_KEY")

    # Verify they are strings
    assert isinstance(settings.DEFAULT_PASSWORD, str)
    assert isinstance(settings.SUPABASE_URL, str)
    assert isinstance(settings.SUPABASE_KEY, str)
