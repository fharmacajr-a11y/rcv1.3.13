from typing import Any

class Postgrest:
    def auth(self, *args: Any, **kwargs: Any) -> Any: ...
    def table(self, name: str) -> Any: ...
    def rpc(self, name: str, *args: Any, **kwargs: Any) -> Any: ...

class Storage:
    _base_url: str
    def from_(self, bucket: str) -> Any: ...

class APIError(Exception):
    """Supabase API error with JSON body."""

    json: Any
    message: str
    code: str | None
    hint: str | None
    details: Any

class Client:
    postgrest: Postgrest
    storage: Storage
    auth: Any
    realtime: Any
    def table(self, name: str) -> Any: ...
    def rpc(self, fn: str, *args: Any, **kwargs: Any) -> Any: ...

def create_client(*args: Any, **kwargs: Any) -> Client: ...
