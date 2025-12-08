"""Tests for src.utils.paths module."""

import os
import sys


def test_resource_path_dev_mode():
    """Test resource_path in development mode (no _MEIPASS)."""
    from src.utils.paths import resource_path

    # In dev mode, should resolve relative to cwd
    result = resource_path("rc.ico")
    expected = os.path.join(os.path.abspath("."), "rc.ico")
    assert result == expected


def test_resource_path_bundled_mode(monkeypatch, tmp_path):
    """Test resource_path in PyInstaller bundled mode."""
    from src.utils.paths import resource_path

    # Simulate PyInstaller's _MEIPASS usando tmp_path
    fake_meipass = str(tmp_path / "fake_bundle_path")

    # Need to set attribute before importing, use setattr on sys module itself
    import sys

    if not hasattr(sys, "_MEIPASS"):
        # Create the attribute first
        object.__setattr__(sys, "_MEIPASS", fake_meipass)
    else:
        monkeypatch.setattr(sys, "_MEIPASS", fake_meipass)

    try:
        result = resource_path("rc.ico")
        expected = os.path.join(fake_meipass, "rc.ico")
        assert result == expected
    finally:
        # Clean up
        if hasattr(sys, "_MEIPASS"):
            try:
                delattr(sys, "_MEIPASS")
            except AttributeError:
                pass


def test_is_bundled_dev_mode():
    """Test is_bundled returns False in dev mode."""
    from src.utils.paths import is_bundled

    # Remove _MEIPASS if it exists (shouldn't in normal tests)
    if hasattr(sys, "_MEIPASS"):
        delattr(sys, "_MEIPASS")

    assert is_bundled() is False


def test_is_bundled_in_bundle(monkeypatch, tmp_path):
    """Test is_bundled returns True when _MEIPASS exists."""
    from src.utils.paths import is_bundled

    # Simulate PyInstaller environment usando tmp_path
    fake_bundle = str(tmp_path / "fake_bundle")
    import sys

    if not hasattr(sys, "_MEIPASS"):
        object.__setattr__(sys, "_MEIPASS", fake_bundle)
    else:
        monkeypatch.setattr(sys, "_MEIPASS", fake_bundle)

    try:
        assert is_bundled() is True
    finally:
        # Clean up
        if hasattr(sys, "_MEIPASS"):
            try:
                delattr(sys, "_MEIPASS")
            except AttributeError:
                pass


def test_resource_path_with_subdirectory():
    """Test resource_path with nested paths."""
    from src.utils.paths import resource_path

    result = resource_path("assets/images/logo.png")
    # Normalize paths for comparison (handle forward/backward slashes)
    expected = os.path.abspath("assets/images/logo.png")
    assert os.path.normpath(result) == os.path.normpath(expected)


def test_resource_path_empty_string():
    """Test resource_path with empty string returns base path."""
    from src.utils.paths import resource_path

    result = resource_path("")
    expected = os.path.abspath(".")
    # Normalize to handle trailing slashes
    assert os.path.normpath(result) == os.path.normpath(expected)


# ==================== ensure_str_path ====================


def test_ensure_str_path_with_string():
    """Test ensure_str_path with a regular string."""

    from src.utils.paths import ensure_str_path

    result = ensure_str_path("/usr/local/bin")
    assert result == "/usr/local/bin"
    assert isinstance(result, str)


def test_ensure_str_path_with_path_object():
    """Test ensure_str_path with pathlib.Path."""
    from pathlib import Path

    from src.utils.paths import ensure_str_path

    path = Path("/usr/local/bin")
    result = ensure_str_path(path)
    assert result == str(path)
    assert isinstance(result, str)


def test_ensure_str_path_with_windows_path():
    """Test ensure_str_path with Windows-style path."""
    from pathlib import Path

    from src.utils.paths import ensure_str_path

    result = ensure_str_path(Path("C:/Users/test"))
    assert isinstance(result, str)
    assert "Users" in result


def test_ensure_str_path_with_custom_pathlike():
    """Test ensure_str_path with custom PathLike object."""

    from src.utils.paths import ensure_str_path

    class CustomPath:
        def __fspath__(self) -> str:
            return "/custom/path"

    custom = CustomPath()
    result = ensure_str_path(custom)
    assert result == "/custom/path"
    assert isinstance(result, str)
