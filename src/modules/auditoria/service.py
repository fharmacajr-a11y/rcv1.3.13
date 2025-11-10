"""Service layer para Auditoria - Funções de integração com Supabase.

Nota: Este módulo não é mais usado ativamente pela view.py (que faz queries diretas),
mas mantém-se para referência ou uso futuro.
"""
from __future__ import annotations

from typing import Any

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:
    def get_supabase():  # type: ignore[no-redef]
        return None


def list_clients_minimal() -> list[dict[str, Any]]:
    """
    Retorna lista mínima de clients (id BIGINT, name, tax_id) ordenada por id.

    Returns:
        Lista de dicts com dados do client
    """
    sb = get_supabase()
    if not sb:
        return []

    try:
        res = (
            sb.table("clients")
            .select("*")
            .order("id")
            .execute()
        )
        return getattr(res, "data", []) or []
    except Exception:
        return []


def list_auditorias() -> list[dict[str, Any]]:
    """
    Retorna lista de auditorias (sem FK embed).

    Returns:
        Lista de dicts com chaves: id, status, created_at, updated_at, cliente_id
    """
    sb = get_supabase()
    if not sb:
        return []

    try:
        res = (
            sb.table("auditorias")
            .select("id, status, created_at, updated_at, cliente_id")
            .order("created_at", desc=True)
            .execute()
        )
        return getattr(res, "data", []) or []
    except Exception:
        return []


def start_auditoria(cliente_id: int) -> dict[str, Any] | None:
    """
    Inicia uma nova auditoria para o cliente especificado.

    Args:
        cliente_id: ID do cliente (BIGINT)

    Returns:
        Dict com dados da auditoria criada, ou None se falhar
    """
    sb = get_supabase()
    if not sb:
        return None

    try:
        res = (
            sb.table("auditorias")
            .insert({"cliente_id": cliente_id, "status": "em_andamento"})
            .execute()
        )
        data = getattr(res, "data", None)
        return data[0] if data else None
    except Exception:
        return None
