"""Módulo de agregação Supabase (barrel module).

Este módulo centraliza e re-exporta funcionalidades relacionadas ao Supabase:
- Cliente DB (get_supabase, exec_postgrest, health checks)
- Cliente Storage (baixar_pasta_zip, DownloadCancelledError)
- Cliente Auth (bind_postgrest_auth_if_any)
- Cliente HTTP (HTTPX_CLIENT, timeouts)

Permite importar tudo de um único local:
    from src.infra.supabase_client import get_supabase, baixar_pasta_zip

Em vez de múltiplos imports específicos:
    from src.infra.supabase.db_client import get_supabase
    from src.infra.supabase.storage_client import baixar_pasta_zip
"""

from __future__ import annotations

from src.infra.supabase.auth_client import bind_postgrest_auth_if_any
from src.infra.supabase.db_client import (
    exec_postgrest,
    get_cloud_status_for_ui,
    get_supabase,
    get_supabase_state,
    is_really_online,
    is_supabase_online,
    supabase,
)
from src.infra.supabase.http_client import HTTPX_CLIENT, HTTPX_TIMEOUT
from src.infra.supabase.storage_client import DownloadCancelledError, baixar_pasta_zip

__all__ = [
    # DB Client
    "supabase",
    "get_supabase",
    "exec_postgrest",
    # Health Checks
    "is_supabase_online",
    "is_really_online",
    "get_supabase_state",
    "get_cloud_status_for_ui",
    # Storage Client
    "baixar_pasta_zip",
    "DownloadCancelledError",
    # Auth Client
    "bind_postgrest_auth_if_any",
    # HTTP Client
    "HTTPX_CLIENT",
    "HTTPX_TIMEOUT",
]
