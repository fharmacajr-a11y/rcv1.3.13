"""Type stubs for postgrest.exceptions module."""

from __future__ import annotations

__all__ = ["APIError"]

class APIError(Exception):
    """PostgREST API error exception."""

    message: str
    details: str | None
    hint: str | None
    code: str | None

    def __init__(
        self,
        message: str,
        details: str | None = None,
        hint: str | None = None,
        code: str | None = None,
    ) -> None: ...
