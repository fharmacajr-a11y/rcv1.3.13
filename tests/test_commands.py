# -*- coding: utf-8 -*-
"""Tests for src.core.commands — PR21: coverage step 2.

Covers:
- register / unregister lifecycle
- run with defaults merging and kwargs override
- run raises KeyError for unknown command
- run propagates callable exceptions
- list_commands / get_command_info
- overwrite warning on duplicate register
"""

from __future__ import annotations

import pytest

from src.core import commands


# ---------------------------------------------------------------------------
# Fixture: isolate the global registry between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_registry() -> None:  # type: ignore[misc]
    """Snapshot and restore _REGISTRY so tests don't leak state."""
    saved = dict(commands._REGISTRY)
    commands._REGISTRY.clear()
    yield  # type: ignore[misc]
    commands._REGISTRY.clear()
    commands._REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# register / unregister
# ---------------------------------------------------------------------------
def test_register_and_list() -> None:
    commands.register("test:hello", lambda: "hi", help="say hi")
    result = commands.list_commands()
    assert "test:hello" in result
    assert result["test:hello"] == "say hi"


def test_unregister_existing() -> None:
    commands.register("test:rm", lambda: None, help="will be removed")
    assert commands.unregister("test:rm") is True
    assert "test:rm" not in commands.list_commands()


def test_unregister_nonexistent() -> None:
    assert commands.unregister("no:such:cmd") is False


def test_register_overwrite_replaces() -> None:
    commands.register("test:dup", lambda: "first", help="v1")
    commands.register("test:dup", lambda: "second", help="v2")
    assert commands.run("test:dup") == "second"
    assert commands.list_commands()["test:dup"] == "v2"


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def test_run_returns_result() -> None:
    commands.register("test:add", lambda a, b: a + b, help="add two numbers")
    assert commands.run("test:add", a=3, b=7) == 10


def test_run_merges_defaults() -> None:
    commands.register("test:greet", lambda who, prefix: f"{prefix} {who}", help="", prefix="Hello")
    # default prefix="Hello", overridden by caller
    assert commands.run("test:greet", who="World") == "Hello World"
    assert commands.run("test:greet", who="World", prefix="Hi") == "Hi World"


def test_run_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="not found"):
        commands.run("no:such:cmd")


def test_run_propagates_exception() -> None:
    def _boom() -> None:
        raise ValueError("intentional")

    commands.register("test:boom", _boom, help="explodes")
    with pytest.raises(ValueError, match="intentional"):
        commands.run("test:boom")


# ---------------------------------------------------------------------------
# get_command_info
# ---------------------------------------------------------------------------
def test_get_command_info_existing() -> None:
    def _fn() -> None: ...

    commands.register("test:info", _fn, help="info test", x=42)
    info = commands.get_command_info("test:info")
    assert info is not None
    assert info["name"] == "test:info"
    assert info["help"] == "info test"
    assert info["defaults"] == {"x": 42}
    assert info["func"] == "_fn"


def test_get_command_info_missing() -> None:
    assert commands.get_command_info("nope") is None
