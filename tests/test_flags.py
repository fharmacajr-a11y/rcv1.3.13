"""Tests for CLI argument parsing."""

import pytest  # type: ignore[import-untyped]


def test_parse_args_defaults():
    """Test default argument values."""
    from src.cli import parse_args

    args = parse_args([])
    assert args.no_splash is False
    assert args.safe_mode is False
    assert args.debug is False


def test_parse_args_no_splash():
    """Test --no-splash flag."""
    from src.cli import parse_args

    args = parse_args(["--no-splash"])
    assert args.no_splash is True
    assert args.safe_mode is False


def test_parse_args_safe_mode():
    """Test --safe-mode flag."""
    from src.cli import parse_args

    args = parse_args(["--safe-mode"])
    assert args.safe_mode is True
    assert args.no_splash is False


def test_parse_args_debug():
    """Test --debug flag."""
    from src.cli import parse_args

    args = parse_args(["--debug"])
    assert args.debug is True


def test_parse_args_combined():
    """Test multiple flags together."""
    from src.cli import parse_args

    args = parse_args(["--no-splash", "--safe-mode", "--debug"])
    assert args.no_splash is True
    assert args.safe_mode is True
    assert args.debug is True


def test_cli_module_imports_without_error():
    """Test that CLI module can be imported without breaking."""
    try:
        import src.cli
        assert hasattr(src.cli, "parse_args")
        assert hasattr(src.cli, "get_args")
        assert hasattr(src.cli, "AppArgs")
    except Exception as e:
        pytest.fail(f"Failed to import src.cli: {e}")
