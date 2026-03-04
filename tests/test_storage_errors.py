# -*- coding: utf-8 -*-
"""Tests for src.utils.storage_errors — PR21: coverage step 2.

Covers:
- classify_storage_error: all four categories (invalid_key, rls, exists, other)
- Both str and Exception inputs
- Case-insensitivity
"""

from __future__ import annotations

import pytest

from src.utils.storage_errors import classify_storage_error


# ---------------------------------------------------------------------------
# invalid_key
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "msg",
    [
        "InvalidKey: bad path",
        "invalid key in bucket header",
        "INVALIDKEY",
        "the key is invalid key for storage",
    ],
)
def test_classify_invalid_key(msg: str) -> None:
    assert classify_storage_error(msg) == "invalid_key"


def test_classify_invalid_key_from_exception() -> None:
    exc = ValueError("Storage returned InvalidKey")
    assert classify_storage_error(exc) == "invalid_key"


# ---------------------------------------------------------------------------
# rls (row-level security / permission)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "msg",
    [
        "row-level security violation",
        "RLS policy denied",
        "error code 42501",
        "HTTP 403 Forbidden",
        "permission denied by rls",
    ],
)
def test_classify_rls(msg: str) -> None:
    assert classify_storage_error(msg) == "rls"


def test_classify_rls_from_exception() -> None:
    exc = PermissionError("row-level security blocked insert")
    assert classify_storage_error(exc) == "rls"


# ---------------------------------------------------------------------------
# exists (conflict / duplicate)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "msg",
    [
        "Object already exists in bucket",
        "KeyAlreadyExists",
        "conflict 409",
        "duplicate: already exists",
    ],
)
def test_classify_exists(msg: str) -> None:
    assert classify_storage_error(msg) == "exists"


def test_classify_exists_from_exception() -> None:
    exc = RuntimeError("KeyAlreadyExists: path/to/file.pdf")
    assert classify_storage_error(exc) == "exists"


# ---------------------------------------------------------------------------
# other (fallback)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "msg",
    [
        "timeout connecting to server",
        "unknown error occurred",
        "",
        "network unreachable",
    ],
)
def test_classify_other(msg: str) -> None:
    assert classify_storage_error(msg) == "other"


def test_classify_other_from_exception() -> None:
    exc = ConnectionError("DNS resolution failed")
    assert classify_storage_error(exc) == "other"
