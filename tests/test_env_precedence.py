"""Tests for .env file loading precedence.

Validates that the loading order is correct:
1. Bundled .env (via resource_path) loads with override=False
2. Local .env (in cwd) loads with override=True (overwrites bundled values)
"""

import os

import pytest  # type: ignore[import-untyped]


def test_env_precedence_local_overwrites_bundled(tmp_path, monkeypatch):
    """Test that local .env overwrites bundled .env values."""
    # Setup: create two .env files
    bundled_env = tmp_path / "bundled.env"
    bundled_env.write_text("TEST_VAR=bundled_value\nONLY_BUNDLED=yes\n")

    local_env = tmp_path / "local.env"
    local_env.write_text("TEST_VAR=local_value\nONLY_LOCAL=yes\n")

    # Clear environment
    monkeypatch.delenv("TEST_VAR", raising=False)
    monkeypatch.delenv("ONLY_BUNDLED", raising=False)
    monkeypatch.delenv("ONLY_LOCAL", raising=False)

    # Load dotenv (simulate app behavior)
    try:
        from dotenv import load_dotenv
    except ImportError:
        pytest.skip("python-dotenv not installed")

    # Load bundled first (override=False)
    load_dotenv(str(bundled_env), override=False)

    # Load local second (override=True) - should overwrite TEST_VAR
    load_dotenv(str(local_env), override=True)

    # Verify precedence
    assert os.getenv("TEST_VAR") == "local_value", "Local .env should overwrite bundled"
    assert os.getenv("ONLY_BUNDLED") == "yes", "Bundled-only vars should remain"
    assert os.getenv("ONLY_LOCAL") == "yes", "Local-only vars should be set"


def test_env_bundled_does_not_overwrite_existing(tmp_path, monkeypatch):
    """Test that bundled .env (override=False) doesn't overwrite existing env vars."""
    bundled_env = tmp_path / "bundled.env"
    bundled_env.write_text("PREEXISTING=from_bundled\n")

    # Set environment variable before loading
    monkeypatch.setenv("PREEXISTING", "already_set")

    try:
        from dotenv import load_dotenv
    except ImportError:
        pytest.skip("python-dotenv not installed")

    # Load with override=False
    load_dotenv(str(bundled_env), override=False)

    # Should NOT overwrite
    assert os.getenv("PREEXISTING") == "already_set"


def test_env_local_overwrites_existing(tmp_path, monkeypatch):
    """Test that local .env (override=True) does overwrite existing env vars."""
    local_env = tmp_path / "local.env"
    local_env.write_text("PREEXISTING=from_local\n")

    # Set environment variable before loading
    monkeypatch.setenv("PREEXISTING", "already_set")

    try:
        from dotenv import load_dotenv
    except ImportError:
        pytest.skip("python-dotenv not installed")

    # Load with override=True
    load_dotenv(str(local_env), override=True)

    # Should overwrite
    assert os.getenv("PREEXISTING") == "from_local"


def test_env_loading_order_matches_app(tmp_path, monkeypatch):
    """Test that the loading order matches what's documented in app_gui.py."""
    # Simulate the exact loading pattern from src/app_gui.py
    bundled = tmp_path / "bundled.env"
    bundled.write_text("RC_LOG_LEVEL=INFO\nSUPABASE_URL=bundled_url\n")

    local = tmp_path / "local.env"
    local.write_text("SUPABASE_URL=local_url\n")

    monkeypatch.delenv("RC_LOG_LEVEL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    try:
        from dotenv import load_dotenv
    except ImportError:
        pytest.skip("python-dotenv not installed")

    # Exact order from app_gui.py:
    load_dotenv(str(bundled), override=False)  # empacotado
    load_dotenv(str(local), override=True)  # externo sobrescreve

    assert os.getenv("RC_LOG_LEVEL") == "INFO", "Bundled-only should work"
    assert os.getenv("SUPABASE_URL") == "local_url", "Local should overwrite"
