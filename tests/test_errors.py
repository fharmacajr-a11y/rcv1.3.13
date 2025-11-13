"""Tests for global exception handling."""

import logging
import sys

import pytest  # type: ignore[import-untyped]


def test_exception_hook_can_be_installed():
    """Test that exception hook can be installed without errors."""
    from src.utils.errors import install_global_exception_hook, uninstall_global_exception_hook

    original_hook = sys.excepthook

    try:
        install_global_exception_hook()
        assert sys.excepthook != original_hook
    finally:
        uninstall_global_exception_hook()
        assert sys.excepthook == sys.__excepthook__


def test_exception_hook_logs_exception(caplog, monkeypatch):
    """Test that exception hook logs exceptions."""
    from src.utils.errors import install_global_exception_hook, uninstall_global_exception_hook

    # Suppress GUI errors in test
    monkeypatch.setenv("RC_NO_GUI_ERRORS", "1")

    try:
        install_global_exception_hook()

        # Simulate an exception
        with caplog.at_level(logging.CRITICAL):
            try:
                raise ValueError("Test exception")
            except ValueError:
                exc_info = sys.exc_info()
                # Type check: exc_info components are never None in except block
                exc_type, exc_value, exc_tb = exc_info
                if exc_type is not None and exc_value is not None:
                    sys.excepthook(exc_type, exc_value, exc_tb)

        # Check that it was logged
        assert any("Unhandled exception" in record.message for record in caplog.records)

    finally:
        uninstall_global_exception_hook()


def test_exception_hook_suppresses_gui_in_test_mode(monkeypatch):
    """Test that GUI is suppressed when RC_NO_GUI_ERRORS=1."""
    from src.utils.errors import install_global_exception_hook, uninstall_global_exception_hook

    monkeypatch.setenv("RC_NO_GUI_ERRORS", "1")

    try:
        install_global_exception_hook()

        # This should not raise even though we're not in a GUI environment
        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            exc_info = sys.exc_info()
            # Type check: exc_info components are never None in except block
            exc_type, exc_value, exc_tb = exc_info
            if exc_type is not None and exc_value is not None:
                sys.excepthook(exc_type, exc_value, exc_tb)  # Should not crash

    finally:
        uninstall_global_exception_hook()


def test_errors_module_imports():
    """Test that errors module can be imported."""
    try:
        import src.utils.errors

        assert hasattr(src.utils.errors, "install_global_exception_hook")
        assert hasattr(src.utils.errors, "uninstall_global_exception_hook")
    except Exception as e:
        pytest.fail(f"Failed to import src.utils.errors: {e}")
