# -*- coding: utf-8 -*-
"""Dashboard service for Hub module.

Provides aggregated data snapshot for the Hub dashboard UI.
This service uses existing repositories and services - it does NOT
call the Supabase client directly.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

# Import models
from src.modules.hub.dashboard.models import DashboardSnapshot

# Re-export formatters for backward compatibility
from src.modules.hub.dashboard_formatters import (
    _due_badge,
    _format_due_br,
    _get_first_day_of_month,
    _get_last_day_of_month,
    _parse_due_date_iso,
    _parse_timestamp,
    due_badge,
    format_due_br,
    get_first_day_of_month,
    get_last_day_of_month,
    parse_due_date_iso,
    parse_timestamp,
)

__all__ = [
    "DashboardSnapshot",
    "get_dashboard_snapshot",
    # Re-exported formatters (public API)
    "get_first_day_of_month",
    "get_last_day_of_month",
    "parse_due_date_iso",
    "format_due_br",
    "due_badge",
    "parse_timestamp",
    # Internal symbols re-exported for test monkeypatching
    "_due_badge",
    "_format_due_br",
    "_get_first_day_of_month",
    "_get_last_day_of_month",
    "_parse_due_date_iso",
    "_parse_timestamp",
]

logger = logging.getLogger(__name__)


def _count_tasks_due_until_today(
    tasks: Sequence[Mapping[str, Any]],
    today: date,
) -> int:
    """Conta tarefas pendentes com due_date <= hoje (ignora due_date None).

    Args:
        tasks: Sequência de tarefas (já filtradas por status='pending').
        today: Data de referência.

    Returns:
        Quantidade de tarefas com vencimento até hoje.
    """
    count = 0
    for task in tasks:
        due_date_raw = task.get("due_date")
        if due_date_raw is None:
            continue

        # Converter para date se for string
        if isinstance(due_date_raw, str):
            try:
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                continue
        elif isinstance(due_date_raw, date):
            due_date = due_date_raw
        else:
            continue

        if due_date <= today:
            count += 1

    return count


def _build_hot_items(
    obligations: Sequence[Mapping[str, Any]],
    today: date,
    days_threshold: int = 2,
) -> list[str]:
    """Build hot items alerts based on upcoming obligations.

    Generates alert strings for obligations due within the threshold period.
    Currently supports SNGPC and FARMACIA_POPULAR kinds.

    Args:
        obligations: Sequence of obligation mappings with 'kind', 'due_date', 'status'.
        today: Reference date for calculating urgency.
        days_threshold: Number of days to consider as "urgent" (default: 2).

    Returns:
        List of alert strings.
    """
    hot_items: list[str] = []
    threshold_date = today + timedelta(days=days_threshold)

    # Count urgent obligations by kind
    sngpc_urgent: list[Mapping[str, Any]] = []
    farmacia_popular_urgent: list[Mapping[str, Any]] = []

    for obl in obligations:
        status = obl.get("status", "")
        if status not in ("pending", "overdue"):
            continue

        due_date_raw = obl.get("due_date")
        if due_date_raw is None:
            continue

        # Parse due_date if it's a string
        if isinstance(due_date_raw, str):
            try:
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                continue
        elif isinstance(due_date_raw, date):
            due_date = due_date_raw
        else:
            continue

        if due_date > threshold_date:
            continue

        kind = obl.get("kind", "")
        if kind == "SNGPC":
            sngpc_urgent.append(obl)
        elif kind == "FARMACIA_POPULAR":
            farmacia_popular_urgent.append(obl)

    # Generate alert strings
    if sngpc_urgent:
        count = len(sngpc_urgent)
        # Find minimum days remaining
        min_days = None
        for obl in sngpc_urgent:
            due_date_raw = obl.get("due_date")
            if due_date_raw is None:
                continue
            if isinstance(due_date_raw, str):
                try:
                    due_date = date.fromisoformat(due_date_raw)
                except ValueError:
                    continue
            elif isinstance(due_date_raw, date):
                due_date = due_date_raw
            else:
                continue
            days_left = (due_date - today).days
            if min_days is None or days_left < min_days:
                min_days = days_left

        if min_days is not None:
            if min_days <= 0:
                hot_items.append(f"{count} envio(s) SNGPC vencido(s) ou para hoje!")
            elif min_days == 1:
                hot_items.append(f"Falta 1 dia para {count} envio(s) SNGPC")
            else:
                hot_items.append(f"Faltam {min_days} dias para {count} envio(s) SNGPC")

    if farmacia_popular_urgent:
        count = len(farmacia_popular_urgent)
        min_days = None
        for obl in farmacia_popular_urgent:
            due_date_raw = obl.get("due_date")
            if due_date_raw is None:
                continue
            if isinstance(due_date_raw, str):
                try:
                    due_date = date.fromisoformat(due_date_raw)
                except ValueError:
                    continue
            elif isinstance(due_date_raw, date):
                due_date = due_date_raw
            else:
                continue
            days_left = (due_date - today).days
            if min_days is None or days_left < min_days:
                min_days = days_left

        if min_days is not None:
            if min_days <= 0:
                hot_items.append(f"{count} obrigação(ões) Farmácia Popular vencida(s) ou para hoje!")
            elif min_days == 1:
                hot_items.append(f"Falta 1 dia para {count} obrigação(ões) Farmácia Popular")
            else:
                hot_items.append(f"Faltam {min_days} dias para {count} obrigação(ões) Farmácia Popular")

    return hot_items


def _build_risk_radar(
    obligations: Sequence[Mapping[str, Any]],
    today: date,
) -> dict[str, dict[str, Any]]:
    """Build risk radar with quadrants (SNGPC, SIFAP).

    Args:
        obligations: Sequence of obligation mappings.
        today: Reference date for calculating overdue status.

    Returns:
        Dictionary with quadrants, each containing pending, overdue counts and status.
    """
    # Initialize quadrants
    quadrants: dict[str, dict[str, Any]] = {
        "SNGPC": {"pending": 0, "overdue": 0},
        "SIFAP": {"pending": 0, "overdue": 0},
    }

    # Map kinds to quadrants
    for obl in obligations:
        kind = obl.get("kind", "")

        # Map kind to quadrant key
        if kind == "SNGPC":
            key = "SNGPC"
        elif kind == "SIFAP":
            key = "SIFAP"
        else:
            continue  # Unknown or unmapped kind

        status = obl.get("status", "")
        due_date_raw = obl.get("due_date")

        # Parse due_date
        due_date: date | None = None
        if isinstance(due_date_raw, str):
            try:
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                pass
        elif isinstance(due_date_raw, date):
            due_date = due_date_raw

        # Determine if overdue or pending
        is_overdue = False
        is_pending = False

        if status == "overdue":
            is_overdue = True
        elif status == "pending":
            if due_date is not None and due_date < today:
                is_overdue = True
            else:
                is_pending = True

        if is_overdue:
            quadrants[key]["overdue"] += 1
        elif is_pending:
            quadrants[key]["pending"] += 1

    # Calculate status for each quadrant
    def _quadrant_status(pending: int, overdue: int) -> str:
        if pending == 0 and overdue == 0:
            return "green"
        if overdue > 0:
            return "red"
        return "yellow"

    for key, data in quadrants.items():
        pending = data["pending"]
        overdue = data["overdue"]
        data["status"] = _quadrant_status(pending, overdue)

    return quadrants


def _fetch_client_names(client_ids: list[int]) -> dict[int, str]:
    """Fetch client names for a list of client IDs.

    Args:
        client_ids: List of client IDs to fetch.

    Returns:
        Dictionary mapping client_id to client name (razao_social or fallback).
    """
    from . import data_access

    return data_access.fetch_client_names_impl(client_ids)


def _load_pending_tasks(
    org_id: str,
    today: date,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Load pending tasks for the dashboard.

    Args:
        org_id: UUID of the organization.
        today: Reference date for ordering (tasks are shown from earliest due_date).
        limit: Maximum number of tasks to return (default: 5).

    Returns:
        List of pending task dictionaries with due_date, client_id, client_name,
        title, and priority fields.
    """
    from . import data_access

    return data_access.load_pending_tasks_impl(org_id, today, limit, fetch_client_names_fn=_fetch_client_names)


def _load_obligations(org_id: str) -> list[dict[str, Any]]:
    """Load all obligations for the organization.

    Args:
        org_id: UUID of the organization.

    Returns:
        List of obligation dictionaries.
    """
    try:
        from src.features.regulations.repository import list_obligations_for_org

        return list(list_obligations_for_org(org_id))
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load obligations: %s", e)
        return []


def _load_clients_of_the_day(
    org_id: str,
    today: date,
) -> list[dict[str, Any]]:
    """Load clients with obligations due today.

    Wrapper that delegates to data_access.load_clients_of_the_day_impl.
    Kept here to preserve test monkeypatch points.

    Args:
        org_id: UUID of the organization.
        today: Reference date (obligations with due_date == today).

    Returns:
        List of clients with obligations due today, each containing:
        - client_id: int
        - client_name: str
        - obligation_kinds: list[str]
    """
    from . import data_access

    return data_access.load_clients_of_the_day_impl(
        org_id,
        today,
        fetch_client_names_fn=_fetch_client_names,
    )


def _load_recent_activity(
    org_id: str,
    today: date,
) -> list[dict[str, Any]]:
    """Load recent team activity (tasks and obligations).

    Wrapper that delegates to data_access.load_recent_activity_impl.
    Kept here to preserve test monkeypatch points.

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
    from . import data_access

    return data_access.load_recent_activity_impl(org_id, today)


def _build_upcoming_deadlines(
    obligations: Sequence[Mapping[str, Any]],
    today: date,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Build upcoming deadlines from obligations (pending/overdue, sorted by due_date).

    Args:
        obligations: Sequence of obligation mappings.
        today: Reference date.
        limit: Maximum number of deadlines to return.

    Returns:
        List of deadline dicts with due_date, client_id, client_name, kind, title, status.
    """
    deadlines: list[dict[str, Any]] = []

    for obl in obligations:
        status = obl.get("status", "")
        if status not in ("pending", "overdue"):
            continue

        due_date_raw = obl.get("due_date")
        if due_date_raw is None:
            continue

        # Parse due_date
        due_date: date | None = None
        if isinstance(due_date_raw, str):
            try:
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                continue
        elif isinstance(due_date_raw, date):
            due_date = due_date_raw
        else:
            continue

        # Only include future or today deadlines
        if due_date < today:
            # Include overdue items too (they are urgent)
            pass

        client_id = str(obl.get("client_id", ""))
        kind = obl.get("kind", "")
        title = obl.get("title", kind)

        status_badge, days_delta = _due_badge(due_date, today)

        deadlines.append(
            {
                "due_date": _format_due_br(due_date),
                "client_id": client_id,
                "client_name": f"Cliente #{client_id}",
                "kind": kind,
                "title": title,
                "status": status_badge,
                "_days_delta": days_delta,
            }
        )

    # Sort by days_delta (closest first)
    deadlines.sort(key=lambda x: x["_days_delta"])

    # Remove internal sort field and limit
    for item in deadlines:
        item.pop("_days_delta", None)

    return deadlines[:limit]


def get_dashboard_snapshot(
    org_id: str,
    today: date | None = None,
) -> DashboardSnapshot:
    """Get aggregated dashboard data for an organization.

    This function collects data from multiple repositories and services to
    build a comprehensive snapshot for the Hub dashboard.

    Args:
        org_id: UUID of the organization.
        today: Reference date (defaults to date.today() if None).

    Returns:
        DashboardSnapshot with aggregated data.
    """
    if today is None:
        today = date.today()

    snapshot = DashboardSnapshot()

    # 1) Active clients count
    try:
        from src.core.services.clientes_service import count_clients

        snapshot.active_clients = count_clients()
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to count active clients: %s", e)
        snapshot.active_clients = 0

    # 2) Pending obligations count
    try:
        from src.features.regulations.repository import count_pending_obligations

        snapshot.pending_obligations = count_pending_obligations(org_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to count pending obligations: %s", e)
        snapshot.pending_obligations = 0

    # 3) Tasks due today
    try:
        from src.features.tasks.repository import list_tasks_for_org

        pending_tasks_all = list_tasks_for_org(org_id, status="pending")
        snapshot.tasks_today = _count_tasks_due_until_today(pending_tasks_all, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to count tasks due today: %s", e)
        snapshot.tasks_today = 0

    # 4) Cash inflow for current month
    try:
        from src.features.cashflow.repository import totals as cashflow_totals

        first_day = _get_first_day_of_month(today)
        last_day = _get_last_day_of_month(today)
        month_totals = cashflow_totals(first_day, last_day, org_id=org_id)
        snapshot.cash_in_month = month_totals.get("in", 0.0)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to get cash inflow: %s", e)
        snapshot.cash_in_month = 0.0

    # 5) Load obligations (used for deadlines, hot_items, risk_radar)
    obligations = _load_obligations(org_id)

    # 6) Upcoming deadlines from obligations (pending/overdue, sorted by due_date, top 5)
    try:
        snapshot.upcoming_deadlines = _build_upcoming_deadlines(obligations, today, limit=5)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to build upcoming deadlines: %s", e)
        snapshot.upcoming_deadlines = []

    # 7) Pending tasks (top 5)
    try:
        snapshot.pending_tasks = _load_pending_tasks(org_id, today, limit=5)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load pending tasks: %s", e)
        snapshot.pending_tasks = []

    # 8) Clients of the day
    try:
        snapshot.clients_of_the_day = _load_clients_of_the_day(org_id, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load clients of the day: %s", e)
        snapshot.clients_of_the_day = []

    # 9) Hot items (urgent alerts)
    try:
        snapshot.hot_items = _build_hot_items(obligations, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to build hot items: %s", e)
        snapshot.hot_items = []

    # 10) Risk radar from obligations
    try:
        snapshot.risk_radar = _build_risk_radar(obligations, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to build risk radar: %s", e)
        snapshot.risk_radar = {}

    # 11) Recent activity
    try:
        snapshot.recent_activity = _load_recent_activity(org_id, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load recent activity: %s", e)
        snapshot.recent_activity = []

    # Not in ANVISA-only mode anymore
    snapshot.anvisa_only = False

    return snapshot
