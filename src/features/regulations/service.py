# -*- coding: utf-8 -*-
"""Service layer for regulatory obligations.

Provides high-level business logic for managing regulatory obligations (CRUD operations).
Built on top of the repository layer.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Final, Literal
from uuid import uuid4

from src.db.domain_types import RegObligationRow
from src.features.regulations.repository import list_obligations_for_org

logger = logging.getLogger(__name__)

# Type aliases for clarity
ObligationKind = Literal["SNGPC", "FARMACIA_POPULAR", "SIFAP", "LICENCA_SANITARIA", "OUTRO"]
ObligationStatus = Literal["pending", "done", "overdue", "canceled"]

# ---------------------------------------------------------------------------
# Normalização de status e kind
# ---------------------------------------------------------------------------

CANONICAL_STATUSES: Final[set[str]] = {
    "pending",
    "done",
    "overdue",
    "canceled",
}

STATUS_MAP_PT_TO_EN: Final[dict[str, str]] = {
    "Pendente": "pending",
    "PENDENTE": "pending",
    "Concluída": "done",
    "Concluida": "done",
    "Concluído": "done",
    "Concluido": "done",
    "CONCLUIDA": "done",
    "CONCLUIDO": "done",
    "Atrasada": "overdue",
    "Atrasado": "overdue",
    "ATRASADA": "overdue",
    "ATRASADO": "overdue",
    "Cancelada": "canceled",
    "Cancelado": "canceled",
    "CANCELADA": "canceled",
    "CANCELADO": "canceled",
}

KIND_MAP_PT_TO_EN: Final[dict[str, str]] = {
    "SNGPC": "SNGPC",
    "sngpc": "SNGPC",
    "Farmácia Popular": "FARMACIA_POPULAR",
    "Farmacia Popular": "FARMACIA_POPULAR",
    "FARMACIA POPULAR": "FARMACIA_POPULAR",
    "farmacia popular": "FARMACIA_POPULAR",
    "FARMACIA_POPULAR": "FARMACIA_POPULAR",
    "Sifap": "SIFAP",
    "SIFAP": "SIFAP",
    "sifap": "SIFAP",
    "Licença Sanitária": "LICENCA_SANITARIA",
    "Licenca Sanitaria": "LICENCA_SANITARIA",
    "Licença Sanitaria": "LICENCA_SANITARIA",
    "LICENCA SANITARIA": "LICENCA_SANITARIA",
    "LICENCA_SANITARIA": "LICENCA_SANITARIA",
    "Outro": "OUTRO",
    "OUTRO": "OUTRO",
    "outro": "OUTRO",
}


def _normalize_status(value: str | None, default: str = "pending") -> str:
    """Normalize status value to canonical English lowercase.

    Args:
        value: Status value (can be PT-BR or English).
        default: Default value if normalization fails.

    Returns:
        Canonical status: pending, done, overdue, or canceled.
    """
    if not value:
        return default

    # Already canonical?
    if value in CANONICAL_STATUSES:
        return value

    # Try PT-BR mapping
    mapped = STATUS_MAP_PT_TO_EN.get(value)
    if mapped:
        return mapped

    # Fallback: lowercase and strip
    lowered = value.strip().lower()
    if lowered in CANONICAL_STATUSES:
        return lowered

    # Nothing matched, use default
    return default


def _normalize_kind(value: str) -> str:
    """Normalize kind value to canonical uppercase.

    Args:
        value: Kind value (can be PT-BR or English).

    Returns:
        Canonical kind: SNGPC, FARMACIA_POPULAR, SIFAP, LICENCA_SANITARIA, or OUTRO.
    """
    if not value:
        return "OUTRO"

    # Try exact mapping
    mapped = KIND_MAP_PT_TO_EN.get(value)
    if mapped:
        return mapped

    # Fallback to OUTRO
    return "OUTRO"


# ---------------------------------------------------------------------------
# Supabase client access (same pattern as repository)
# ---------------------------------------------------------------------------
def _get_client():
    """Get Supabase client instance."""
    try:
        from src.infra.supabase.db_client import get_client  # type: ignore[import-not-found]

        return get_client()
    except ImportError:
        from src.infra.supabase_client import get_supabase  # type: ignore[import-not-found]

        return get_supabase()


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_obligations_for_client(org_id: str, client_id: int) -> list[RegObligationRow]:
    """List all regulatory obligations for a specific client.

    Args:
        org_id: Organization ID.
        client_id: Client ID to filter obligations.

    Returns:
        List of obligation records for the client.
    """
    all_obligations = list_obligations_for_org(org_id)
    return [obl for obl in all_obligations if obl.get("client_id") == client_id]


def create_obligation(
    org_id: str,
    created_by: str,
    *,
    client_id: int,
    kind: str,  # Aceita PT-BR ou valores canônicos, normalizado internamente
    title: str,
    due_date: date,
    status: str = "pending",  # Aceita PT-BR ou valores canônicos, normalizado internamente
    reference_start: date | None = None,
    reference_end: date | None = None,
    notes: str | None = None,
) -> RegObligationRow:
    """Create a new regulatory obligation.

    Args:
        org_id: Organization ID.
        created_by: User ID who is creating the obligation.
        client_id: Client ID this obligation belongs to.
        kind: Type of obligation (accepts PT-BR or canonical: SNGPC, FARMACIA_POPULAR, etc.).
        title: Obligation title/description.
        due_date: Due date for the obligation.
        status: Obligation status (accepts PT-BR or canonical: pending, done, overdue, canceled).
        reference_start: Optional reference period start date.
        reference_end: Optional reference period end date.
        notes: Optional additional notes.

    Returns:
        The created obligation record.

    Raises:
        RuntimeError: If creation fails.
    """
    client = _get_client()

    # Normalize kind (handle PT-BR or canonical values)
    normalized_kind = _normalize_kind(kind)

    # Normalize status (handle PT-BR or canonical values)
    normalized_status = _normalize_status(status, default="pending")

    # Build insert data
    insert_data: dict = {
        "id": str(uuid4()),
        "org_id": org_id,
        "client_id": client_id,
        "kind": normalized_kind,
        "title": title,
        "due_date": due_date.isoformat(),
        "status": normalized_status,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Add optional fields
    if reference_start is not None:
        insert_data["reference_start"] = reference_start.isoformat()
    if reference_end is not None:
        insert_data["reference_end"] = reference_end.isoformat()
    if notes is not None:
        insert_data["notes"] = notes

    try:
        response = client.table("reg_obligations").insert(insert_data).execute()

        if not response.data:
            raise RuntimeError("Failed to create obligation: no data returned")

        return response.data[0]

    except Exception as exc:
        logger.error("Failed to create obligation: %s", exc)
        raise RuntimeError(f"Failed to create obligation: {exc}") from exc


def update_obligation(
    org_id: str,
    obligation_id: str,
    *,
    title: str | None = None,
    kind: str | None = None,  # Aceita PT-BR ou valores canônicos, normalizado internamente
    due_date: date | None = None,
    status: str | None = None,  # Aceita PT-BR ou valores canônicos, normalizado internamente
    reference_start: date | None = None,
    reference_end: date | None = None,
    notes: str | None = None,
) -> RegObligationRow:
    """Update an existing regulatory obligation.

    Args:
        org_id: Organization ID.
        obligation_id: ID of the obligation to update.
        title: New title (if provided).
        kind: New kind (if provided, accepts PT-BR or canonical values).
        due_date: New due date (if provided).
        status: New status (if provided, accepts PT-BR or canonical values).
        reference_start: New reference start date (if provided).
        reference_end: New reference end date (if provided).
        notes: New notes (if provided).

    Returns:
        The updated obligation record.

    Raises:
        RuntimeError: If update fails.
    """
    client = _get_client()

    # Build update data (only non-None fields)
    update_data: dict = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if title is not None:
        update_data["title"] = title
    if kind is not None:
        # Normalize kind (handle PT-BR or canonical values)
        normalized_kind = _normalize_kind(kind)
        update_data["kind"] = normalized_kind
    if due_date is not None:
        update_data["due_date"] = due_date.isoformat()
    if status is not None:
        # Normalize status (handle PT-BR or canonical values)
        normalized_status = _normalize_status(status, default="pending")
        update_data["status"] = normalized_status
        # Set completed_at when marking as done
        if normalized_status == "done":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    if reference_start is not None:
        update_data["reference_start"] = reference_start.isoformat()
    if reference_end is not None:
        update_data["reference_end"] = reference_end.isoformat()
    if notes is not None:
        update_data["notes"] = notes

    try:
        response = (
            client.table("reg_obligations").update(update_data).eq("id", obligation_id).eq("org_id", org_id).execute()
        )

        if not response.data:
            raise RuntimeError("Failed to update obligation: no data returned")

        return response.data[0]

    except Exception as exc:
        logger.error("Failed to update obligation: %s", exc)
        raise RuntimeError(f"Failed to update obligation: {exc}") from exc


def delete_obligation(org_id: str, obligation_id: str) -> None:
    """Delete a regulatory obligation.

    Args:
        org_id: Organization ID.
        obligation_id: ID of the obligation to delete.

    Raises:
        RuntimeError: If deletion fails.
    """
    client = _get_client()

    try:
        client.table("reg_obligations").delete().eq("id", obligation_id).eq("org_id", org_id).execute()
        logger.info("Deleted obligation %s", obligation_id)

    except Exception as exc:
        logger.error("Failed to delete obligation: %s", exc)
        raise RuntimeError(f"Failed to delete obligation: {exc}") from exc
