"""Type stubs for postgrest-py library.

Provides minimal type annotations for PostgREST client interfaces
used by the Supabase Python SDK.
"""

from __future__ import annotations

from typing import Any, Generic, Mapping, Sequence, TypeVar

__all__ = [
    "APIError",
    "APIResponse",
    "PostgrestClient",
    "RequestBuilder",
    "SyncSelectRequestBuilder",
    "SyncQueryRequestBuilder",
    "SyncFilterRequestBuilder",
]

T_co = TypeVar("T_co", covariant=True)

class APIError(Exception):
    """PostgREST API error exception."""

    message: str
    details: str | None
    hint: str | None
    code: str | None

    def __init__(
        self,
        error: Mapping[str, Any],
    ) -> None: ...

class APIResponse(Generic[T_co]):
    """Response from PostgREST execute() call."""

    data: Sequence[T_co] | None
    error: APIError | None
    count: int | None

    def __init__(
        self,
        data: Sequence[T_co] | None = None,
        error: APIError | None = None,
        count: int | None = None,
    ) -> None: ...

class RequestBuilder(Generic[T_co]):
    """Base request builder for PostgREST queries."""

    def execute(self) -> APIResponse[T_co]:
        """Execute the request and return response."""
        ...

class SyncFilterRequestBuilder(RequestBuilder[T_co]):
    """Filter request builder with chainable query methods."""

    def eq(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column equals value."""
        ...

    def neq(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column not equals value."""
        ...

    def gt(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column greater than value."""
        ...

    def gte(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column greater than or equal to value."""
        ...

    def lt(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column less than value."""
        ...

    def lte(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column less than or equal to value."""
        ...

    def like(self, column: str, pattern: str) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows using LIKE pattern matching."""
        ...

    def ilike(self, column: str, pattern: str) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows using case-insensitive LIKE pattern matching."""
        ...

    def is_(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column IS value (for NULL checks)."""
        ...

    def in_(self, column: str, values: Sequence[Any]) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column IN values."""
        ...

    def contains(self, column: str, value: Any) -> SyncFilterRequestBuilder[T_co]:
        """Filter rows where column contains value (for arrays/JSONB)."""
        ...

    def or_(self, filters: str) -> SyncFilterRequestBuilder[T_co]:
        """Combine filters with OR logic."""
        ...

    def order(
        self,
        column: str,
        *,
        desc: bool = False,
        nullsfirst: bool = False,
    ) -> SyncFilterRequestBuilder[T_co]:
        """Order results by column."""
        ...

    def limit(self, count: int) -> SyncFilterRequestBuilder[T_co]:
        """Limit number of rows returned."""
        ...

    def offset(self, count: int) -> SyncFilterRequestBuilder[T_co]:
        """Skip count rows."""
        ...

    def range(self, start: int, end: int) -> SyncFilterRequestBuilder[T_co]:
        """Limit results to range [start, end]."""
        ...

    def single(self) -> SyncFilterRequestBuilder[T_co]:
        """Return single row instead of array."""
        ...

    def maybe_single(self) -> SyncFilterRequestBuilder[T_co]:
        """Return single row or None."""
        ...

class SyncQueryRequestBuilder(SyncFilterRequestBuilder[T_co]):
    """Query request builder with select/insert/update/delete."""

    def select(
        self,
        columns: str = "*",
        *,
        count: str | None = None,
    ) -> SyncQueryRequestBuilder[T_co]:
        """Select columns from table."""
        ...

    def insert(
        self,
        json: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        count: str | None = None,
        returning: str = "representation",
        upsert: bool = False,
    ) -> SyncQueryRequestBuilder[T_co]:
        """Insert rows into table."""
        ...

    def update(
        self,
        json: Mapping[str, Any],
        *,
        count: str | None = None,
        returning: str = "representation",
    ) -> SyncQueryRequestBuilder[T_co]:
        """Update rows in table."""
        ...

    def delete(
        self,
        *,
        count: str | None = None,
        returning: str = "representation",
    ) -> SyncQueryRequestBuilder[T_co]:
        """Delete rows from table."""
        ...

    def upsert(
        self,
        json: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        count: str | None = None,
        returning: str = "representation",
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> SyncQueryRequestBuilder[T_co]:
        """Upsert rows (insert or update on conflict)."""
        ...

class SyncSelectRequestBuilder(SyncQueryRequestBuilder[Mapping[str, Any]]):
    """Select request builder (default returns dicts)."""

    ...

class PostgrestClient:
    """PostgREST client for database operations."""

    def __init__(
        self,
        base_url: str,
        *,
        schema: str = "public",
        headers: Mapping[str, str] | None = None,
    ) -> None: ...
    def from_(self, table: str) -> SyncQueryRequestBuilder[Mapping[str, Any]]:
        """Create query builder for table."""
        ...

    def table(self, table: str) -> SyncQueryRequestBuilder[Mapping[str, Any]]:
        """Create query builder for table (alias for from_)."""
        ...

    def rpc(
        self,
        func: str,
        params: Mapping[str, Any] | None = None,
        *,
        count: str | None = None,
    ) -> SyncQueryRequestBuilder[Any]:
        """Call stored procedure/function."""
        ...

    def auth(self, token: str) -> None:
        """Set authorization token for requests."""
        ...
