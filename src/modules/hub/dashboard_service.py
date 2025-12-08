# -*- coding: utf-8 -*-
"""Dashboard service for Hub module.

Provides aggregated data snapshot for the Hub dashboard UI.
This service uses existing repositories and services - it does NOT
call the Supabase client directly.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DashboardSnapshot:
    """Aggregated data for the Hub dashboard.

    Attributes:
        active_clients: Count of active (non-deleted) clients in the organization.
        pending_obligations: Count of regulatory obligations with status 'pending' or 'overdue'.
        tasks_today: Count of pending tasks due until today (overdue + today).
        cash_in_month: Total cash inflow for the current month.
        upcoming_deadlines: List of upcoming obligations (up to 5), each containing
            client_id, client_name, kind, title, due_date, status.
        hot_items: List of alert strings for urgent items (e.g., SNGPC deadlines).
        pending_tasks: List of pending tasks (up to 5), each containing
            due_date, client_id, client_name, title, priority.
        clients_of_the_day: List of clients with obligations due today, each containing
            client_id, client_name, obligation_kinds.
        risk_radar: Risk radar with 3 quadrants (ANVISA, SNGPC, SIFAP),
            each containing pending, overdue counts and status (green/yellow/red).
        recent_activity: Recent team activity (up to 20 items), each containing
            timestamp, category, text.
    """

    active_clients: int = 0
    pending_obligations: int = 0
    tasks_today: int = 0
    cash_in_month: float = 0.0
    upcoming_deadlines: list[dict[str, Any]] = field(default_factory=list)
    hot_items: list[str] = field(default_factory=list)
    pending_tasks: list[dict[str, Any]] = field(default_factory=list)
    clients_of_the_day: list[dict[str, Any]] = field(default_factory=list)
    risk_radar: dict[str, dict[str, Any]] = field(default_factory=dict)
    recent_activity: list[dict[str, Any]] = field(default_factory=list)


def _get_first_day_of_month(d: date) -> date:
    """Returns the first day of the month for a given date."""
    return d.replace(day=1)


def _get_last_day_of_month(d: date) -> date:
    """Returns the last day of the month for a given date."""
    # Go to next month's first day, then subtract one day
    if d.month == 12:
        next_month = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
    return next_month - timedelta(days=1)


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse timestamp from datetime or ISO string.

    Args:
        value: Timestamp value (datetime, string, or other).

    Returns:
        Parsed datetime or None if invalid.
    """
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        # Try parsing ISO 8601 string
        text = value.strip()
        if not text:
            return None

        # Supabase often sends 'Z' suffix or offset (+00:00)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    return None


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
    """Build risk radar with 3 quadrants (ANVISA, SNGPC, SIFAP).

    Args:
        obligations: Sequence of obligation mappings.
        today: Reference date for calculating overdue status.

    Returns:
        Dictionary with 3 quadrants, each containing pending, overdue counts and status.
    """
    # Initialize quadrants
    quadrants: dict[str, dict[str, Any]] = {
        "ANVISA": {"pending": 0, "overdue": 0},
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
        elif kind == "LICENCA_SANITARIA":
            key = "ANVISA"
        else:
            continue  # Unknown or unmapped kind (FARMACIA_POPULAR não aparece no radar)

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
    if not client_ids:
        return {}

    try:
        from src.modules.clientes.service import fetch_cliente_by_id

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
    try:
        from src.features.tasks.repository import list_tasks_for_org

        # Get pending tasks, ordered by due_date and priority (already done in repo)
        tasks = list_tasks_for_org(org_id, status="pending")

        # Take only the first `limit` tasks
        tasks = tasks[:limit]

        # Fetch client names for tasks that have client_id
        client_ids_raw = [task.get("client_id") for task in tasks if task.get("client_id") is not None]
        client_ids: list[int] = [cid for cid in client_ids_raw if cid is not None]
        client_names = _fetch_client_names(client_ids)

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


def _load_clients_of_the_day(
    org_id: str,
    today: date,
) -> list[dict[str, Any]]:
    """Load clients with obligations due today.

    Args:
        org_id: UUID of the organization.
        today: Reference date (obligations with due_date == today).

    Returns:
        List of clients with obligations due today, each containing:
        - client_id: int
        - client_name: str
        - obligation_kinds: list[str]
    """
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
        client_names = _fetch_client_names(client_ids)

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


def _load_recent_activity(
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

    # 3) Tasks due today (pending tasks with due_date <= today)
    try:
        from src.features.tasks.repository import list_tasks_for_org

        # Get all pending tasks
        pending_task_rows = list_tasks_for_org(org_id, status="pending")

        # Count tasks due until today (overdue + today)
        snapshot.tasks_today = _count_tasks_due_until_today(pending_task_rows, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to count tasks for today: %s", e)
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

    # 5) Upcoming deadlines (obligations pending/overdue, ordered by due_date)
    try:
        from src.features.regulations.repository import list_obligations_for_org

        # Get pending obligations starting from today
        pending_obls = list_obligations_for_org(
            org_id,
            start_date=today,
            status="pending",
            limit=5,
        )
        # Also get overdue (before today, still pending)
        overdue_obls = list_obligations_for_org(
            org_id,
            end_date=today - timedelta(days=1),
            status="overdue",
            limit=5,
        )

        # Combine and sort by due_date, take top 5
        all_obls = list(overdue_obls) + list(pending_obls)
        all_obls.sort(
            key=lambda x: x.get("due_date", "9999-12-31")
            if isinstance(x.get("due_date"), str)
            else (x.get("due_date") or date.max).isoformat()
        )
        top_obls = all_obls[:5]

        # Fetch client names (filter out None values)
        client_ids_raw = [obl.get("client_id") for obl in top_obls if obl.get("client_id") is not None]
        client_ids: list[int] = [cid for cid in client_ids_raw if cid is not None]
        client_names = _fetch_client_names(client_ids)

        # Build upcoming deadlines list
        upcoming: list[dict[str, Any]] = []
        for obl in top_obls:
            cid = obl.get("client_id")
            upcoming.append(
                {
                    "client_id": cid,
                    "client_name": client_names.get(cid, f"Cliente #{cid}") if cid else "N/A",
                    "kind": obl.get("kind", ""),
                    "title": obl.get("title", ""),
                    "due_date": obl.get("due_date"),
                    "status": obl.get("status", ""),
                }
            )
        snapshot.upcoming_deadlines = upcoming

        # 6) Hot items (urgent alerts)
        # Use all obligations for hot items calculation, not just top 5
        all_for_hot = list_obligations_for_org(
            org_id,
            start_date=today - timedelta(days=30),  # Include recent overdue
            end_date=today + timedelta(days=2),
            limit=50,
        )
        snapshot.hot_items = _build_hot_items(list(all_for_hot), today)

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to get upcoming deadlines: %s", e)
        snapshot.upcoming_deadlines = []
        snapshot.hot_items = []

    # 7) Pending tasks (up to 5)
    snapshot.pending_tasks = _load_pending_tasks(org_id, today, limit=5)

    # 8) Clients of the day (clients with obligations due today)
    snapshot.clients_of_the_day = _load_clients_of_the_day(org_id, today)

    # 9) Risk radar (4 quadrants: ANVISA, SNGPC, FARMACIA_POPULAR, SIFAP)
    try:
        from src.features.regulations.repository import list_obligations_for_org

        # Get all obligations for risk radar
        all_obligations = list_obligations_for_org(
            org_id,
            start_date=None,
            end_date=None,
            status=None,
            kind=None,
            limit=None,
        )
        snapshot.risk_radar = _build_risk_radar(list(all_obligations), today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to build risk radar: %s", e)
        snapshot.risk_radar = {}

    # 10) Recent activity (up to 20 items)
    snapshot.recent_activity = _load_recent_activity(org_id, today)

    return snapshot
