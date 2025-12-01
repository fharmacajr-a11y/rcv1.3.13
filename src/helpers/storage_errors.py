"""Utilities to classify and handle storage errors."""

from __future__ import annotations

from typing import Literal

# Known storage error categories exposed to callers
StorageErrorKind = Literal["invalid_key", "rls", "exists", "other"]


def classify_storage_error(exc: BaseException | str) -> StorageErrorKind:
    """
    Classify a storage error into a normalized category understood by the app.

    Returns one of: "invalid_key" (invalid path/key), "rls" (permission/RLS),
    "exists" (already present, conflict), or "other" (fallback for unknown errors).
    """
    normalized_message = str(exc).lower()

    if "invalidkey" in normalized_message or "invalid key" in normalized_message:
        return "invalid_key"

    if (
        "row-level security" in normalized_message
        or "rls" in normalized_message
        or "42501" in normalized_message
        or "403" in normalized_message
    ):
        return "rls"

    if (
        "already exists" in normalized_message
        or "keyalreadyexists" in normalized_message
        or "409" in normalized_message
    ):
        return "exists"

    return "other"
