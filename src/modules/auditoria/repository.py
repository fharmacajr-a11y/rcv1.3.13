"""Supabase data-access helpers for the Auditoria module."""

from __future__ import annotations

from typing import Any, Sequence


def fetch_clients(sb: Any) -> list[dict[str, Any]]:
    """Return ordered list of clients from Supabase (dict rows only)."""

    res = sb.table("clients").select("*").order("id").execute()
    data = getattr(res, "data", None) or []
    return [row for row in data if isinstance(row, dict)]


def fetch_auditorias(sb: Any) -> list[dict[str, Any]]:
    """Return ordered list of auditorias from Supabase (dict rows only)."""

    res = (
        sb.table("auditorias")
        .select("id, status, created_at, updated_at, cliente_id")
        .order("updated_at", desc=True)
        .execute()
    )
    data = getattr(res, "data", None) or []
    return [row for row in data if isinstance(row, dict)]


def insert_auditoria(sb: Any, payload: dict[str, Any]) -> Any:
    """Insert a new auditoria record and return execution result."""

    return sb.table("auditorias").insert(payload).execute()


def update_auditoria(sb: Any, auditoria_id: str, status: str) -> Any:
    """Update auditoria status and return selection result."""

    return (
        sb.table("auditorias").update({"status": status}).eq("id", auditoria_id).select("status, updated_at").execute()
    )


def delete_auditorias(sb: Any, auditoria_ids: Sequence[str]) -> None:
    """Delete a batch of auditorias (no-op when list is empty)."""

    if not auditoria_ids:
        return
    sb.table("auditorias").delete().in_("id", list(auditoria_ids)).execute()


def fetch_current_user_id(sb: Any) -> str:
    """Return the Supabase user id for the authenticated session."""

    user = sb.auth.get_user()
    user_obj = getattr(user, "user", None)
    if not user_obj or not getattr(user_obj, "id", None):
        raise LookupError("Usuario autenticado nao encontrado.")
    return str(user_obj.id)


def fetch_org_id_for_user(sb: Any, user_id: str) -> str:
    """Return the organization id linked to the given Supabase user."""

    res = sb.table("memberships").select("org_id").eq("user_id", user_id).limit(1).execute()
    data = getattr(res, "data", None) or []
    org_id = data[0].get("org_id") if data else ""
    if not org_id:
        raise LookupError("Membership sem org_id para o usuario atual.")
    return str(org_id)
