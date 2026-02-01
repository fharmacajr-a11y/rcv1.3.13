# -*- coding: utf-8 -*-
"""Dashboard data access functions.

Contains functions for fetching/loading data from repositories and services.
This module should NOT import from service.py to avoid circular imports.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from src.modules.hub.dashboard_formatters import _parse_timestamp

__all__ = [
    "fetch_client_names_impl",
    "load_pending_tasks_impl",
    "load_clients_of_the_day_impl",
    "load_recent_activity_impl",
]

logger = logging.getLogger(__name__)


def fetch_client_names_impl(client_ids: list[int]) -> dict[int, str]:
    """Fetch client names for a list of client IDs.

    Args:
        client_ids: List of client IDs to fetch.

    Returns:
        Dictionary mapping client_id to client name (razao_social or fallback).
    """
    if not client_ids:
        return {}

    try:
        from src.modules.clientes.core.service import fetch_cliente_by_id

        names: dict[int, str] = {}
        for cid in client_ids:
            try:
                cliente = fetch_cliente_by_id(cid)
                if cliente:
                    names[cid] = cliente.get("razao_social") or cliente.get("nome_fantasia") or f"Cliente #{cid}"
                else:
                    names[cid] = f"Cliente #{cid}"
            except Exception:  # noqa: BLE001
                names[cid] = f"Cliente #{cid}"
        return names
    except ImportError:
        logger.warning("Could not import clientes service for client names")
        return {cid: f"Cliente #{cid}" for cid in client_ids}


def load_pending_tasks_impl(
    org_id: str,
    today: date,
    limit: int = 5,
    *,
    fetch_client_names_fn: Any = None,
) -> list[dict[str, Any]]:
    """Load pending tasks for the dashboard.

    Args:
        org_id: UUID of the organization.
        today: Reference date for ordering (tasks are shown from earliest due_date).
        limit: Maximum number of tasks to return (default: 5).
        fetch_client_names_fn: Optional function to fetch client names (for testing).

    Returns:
        List of pending task dictionaries with due_date, client_id, client_name,
        title, and priority fields.
    """
    # Use provided function or default
    _fetch_names = fetch_client_names_fn or fetch_client_names_impl

    try:
        from src.features.tasks.repository import list_tasks_for_org

        # Get pending tasks, ordered by due_date and priority (already done in repo)
        tasks = list_tasks_for_org(org_id, status="pending")

        # Take only the first `limit` tasks
        tasks = tasks[:limit]

        # Fetch client names for tasks that have client_id
        client_ids_raw = [task.get("client_id") for task in tasks if task.get("client_id") is not None]
        client_ids: list[int] = [cid for cid in client_ids_raw if cid is not None]
        client_names = _fetch_names(client_ids)

        # Build pending tasks list
        pending: list[dict[str, Any]] = []
        for task in tasks:
            cid = task.get("client_id")
            pending.append(
                {
                    "due_date": task.get("due_date"),
                    "client_id": cid,
                    "client_name": client_names.get(cid, f"Cliente #{cid}") if cid else "N/A",
                    "title": task.get("title", ""),
                    "priority": task.get("priority", "normal"),
                }
            )
        return pending

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load pending tasks: %s", e)
        return []


def load_clients_of_the_day_impl(
    org_id: str,
    today: date,
    *,
    fetch_client_names_fn: Any = None,
) -> list[dict[str, Any]]:
    """Load clients with obligations due today.

    Args:
        org_id: UUID of the organization.
        today: Reference date (obligations with due_date == today).
        fetch_client_names_fn: Optional function to fetch client names (for testing).

    Returns:
        List of clients with obligations due today, each containing:
        - client_id: int
        - client_name: str
        - obligation_kinds: list[str]
    """
    # Use provided function or default
    _fetch_names = fetch_client_names_fn or fetch_client_names_impl

    try:
        from src.features.regulations.repository import list_obligations_for_org

        # Get obligations for today
        obligations_today = list_obligations_for_org(
            org_id,
            start_date=today,
            end_date=today,
            status=None,
            kind=None,
            limit=None,
        )

        # Filter: only pending or overdue, and due_date == today
        filtered_obligations = []
        for obl in obligations_today:
            status = obl.get("status", "")
            if status not in ("pending", "overdue"):
                continue

            due_date_raw = obl.get("due_date")
            if due_date_raw is None:
                continue

            # Convert to date if string
            if isinstance(due_date_raw, str):
                try:
                    due_date = date.fromisoformat(due_date_raw)
                except ValueError:
                    continue
            elif isinstance(due_date_raw, date):
                due_date = due_date_raw
            else:
                continue

            if due_date == today:
                filtered_obligations.append(obl)

        # Group by client_id
        client_kinds: dict[int, set[str]] = {}
        for obl in filtered_obligations:
            client_id = obl.get("client_id")
            if client_id is None:
                continue

            kind = obl.get("kind", "")
            if client_id not in client_kinds:
                client_kinds[client_id] = set()
            if kind:
                client_kinds[client_id].add(kind)

        # Fetch client names
        client_ids = list(client_kinds.keys())
        client_names = _fetch_names(client_ids)

        # Build final list
        clients_of_the_day: list[dict[str, Any]] = []
        for client_id, kinds in client_kinds.items():
            clients_of_the_day.append(
                {
                    "client_id": client_id,
                    "client_name": client_names.get(client_id, f"Cliente #{client_id}"),
                    "obligation_kinds": sorted(list(kinds)),
                }
            )

        # Sort by client_name
        clients_of_the_day.sort(key=lambda x: x["client_name"])

        return clients_of_the_day

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load clients of the day: %s", e)
        return []


def load_recent_activity_impl(
    org_id: str,
    today: date,
) -> list[dict[str, Any]]:
    """Load recent team activity (tasks and obligations).

    Args:
        org_id: UUID of the organization.
        today: Reference date for calculating cutoff.

    Returns:
        List of recent activity items (up to 20), each containing:
        - timestamp: datetime
        - category: str ("task" or "obligation")
        - user_id: str (UUID of creator)
        - user_name: str (display name of creator, if available)
        - text: str (includes user_name prefix if available)
    """
    try:
        # Define cutoff: last 7 days
        cutoff = today - timedelta(days=7)

        events: list[dict[str, Any]] = []

        # Get tasks
        try:
            from src.features.tasks.repository import list_tasks_for_org

            task_rows = list_tasks_for_org(org_id, status=None)

            for row in task_rows:
                raw_created_at = row.get("created_at")
                created_at = _parse_timestamp(raw_created_at)
                if created_at is None:
                    continue
                if created_at.date() < cutoff:
                    continue

                title = (row.get("title") or "").strip()
                client_id = row.get("client_id")
                user_id = row.get("created_by") or ""

                if title:
                    base_text = f"Nova tarefa: {title}"
                else:
                    base_text = "Nova tarefa criada"

                if client_id is not None:
                    text = f"{base_text} para cliente #{client_id}"
                else:
                    text = base_text

                events.append(
                    {
                        "timestamp": created_at,
                        "category": "task",
                        "user_id": user_id,
                        "text": text,
                    }
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load tasks for recent activity: %s", e)

        # Get obligations
        try:
            from src.features.regulations.repository import list_obligations_for_org

            obligation_rows = list_obligations_for_org(
                org_id,
                start_date=None,
                end_date=None,
                status=None,
                kind=None,
                limit=None,
            )

            for row in obligation_rows:
                raw_created_at = row.get("created_at")
                created_at = _parse_timestamp(raw_created_at)
                if created_at is None:
                    continue
                if created_at.date() < cutoff:
                    continue

                kind = (row.get("kind") or "Obrigação").upper()
                client_id = row.get("client_id")
                user_id = row.get("created_by") or ""

                # Map kind to human-readable label
                kind_label = {
                    "SNGPC": "SNGPC",
                    "FARMACIA_POPULAR": "Farmácia Popular",
                    "SIFAP": "Sifap",
                    "LICENCA_SANITARIA": "Licença Sanitária",
                }.get(kind, "Obrigação")

                if client_id is not None:
                    text = f"Nova obrigação {kind_label} para cliente #{client_id}"
                else:
                    text = f"Nova obrigação {kind_label}"

                events.append(
                    {
                        "timestamp": created_at,
                        "category": "obligation",
                        "user_id": user_id,
                        "text": text,
                    }
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load obligations for recent activity: %s", e)

        # Map user_ids to display names
        user_ids = [e["user_id"] for e in events if e.get("user_id")]
        user_names_map: dict[str, str] = {}

        if user_ids:
            try:
                from src.core.services.profiles_service import get_display_names_by_user_ids

                user_names_map = get_display_names_by_user_ids(org_id, user_ids)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to load user names for recent activity: %s", e)

        # Enrich events with user names and prefix text
        for event in events:
            user_id = event.get("user_id") or ""
            user_name = user_names_map.get(user_id, "")

            event["user_name"] = user_name

            # Prefix text with user name if available
            if user_name:
                base_text = str(event.get("text") or "").strip()
                if base_text:
                    event["text"] = f"{user_name}: {base_text}"
                else:
                    event["text"] = user_name

        # Sort by timestamp (most recent first) and limit to 20
        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:20]

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load recent activity: %s", e)
        return []
