from __future__ import annotations

from infra.supabase.auth_client import bind_postgrest_auth_if_any
from infra.supabase.db_client import (
    exec_postgrest,
    get_cloud_status_for_ui,
    get_supabase,
    get_supabase_state,
    is_really_online,
    is_supabase_online,
    supabase,
)
from infra.supabase.http_client import HTTPX_CLIENT, HTTPX_TIMEOUT
from infra.supabase.storage_client import DownloadCancelledError, baixar_pasta_zip

__all__ = [
    "supabase",
    "get_supabase",
    "baixar_pasta_zip",
    "DownloadCancelledError",
    "is_supabase_online",
    "is_really_online",
    "get_supabase_state",
    "get_cloud_status_for_ui",
    "bind_postgrest_auth_if_any",
    "exec_postgrest",
    "HTTPX_CLIENT",
    "HTTPX_TIMEOUT",
]
