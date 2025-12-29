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
        anvisa_only: Flag indicating ANVISA-only mode where Pendências/Tarefas clicks are disabled.
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
    anvisa_only: bool = False


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


def _parse_due_date_iso(due: str) -> date | None:
    """Parse ISO date string (YYYY-MM-DD) to date object.

    Args:
        due: ISO date string.

    Returns:
        Date object or None if invalid.
    """
    try:
        return date.fromisoformat(due.strip())
    except (ValueError, AttributeError):
        return None


def _format_due_br(d: date | None) -> str:
    """Format due date in Brazilian format (dd/mm/YYYY).

    Args:
        d: Date object or None.

    Returns:
        Formatted date string or "—" if None/invalid.
    """
    if d is None:
        return "—"
    try:
        return d.strftime("%d/%m/%Y")
    except (ValueError, AttributeError):
        return "—"


def _due_badge(due: date | None, today: date) -> tuple[str, int]:
    """Generate status badge for a due date and calculate days delta.

    Args:
        due: Due date or None.
        today: Reference date.

    Returns:
        Tuple of (status_text, days_delta):
        - status_text: "Sem prazo", "Hoje", "Faltam Xd", "Atrasada Xd"
        - days_delta: Days until/since due date, or 99999 if no due date
    """
    if due is None:
        return ("Sem prazo", 99999)

    try:
        delta = (due - today).days

        if delta < 0:
            # Atrasada
            return (f"Atrasada {abs(delta)}d", delta)
        elif delta == 0:
            # Hoje
            return ("Hoje", delta)
        else:
            # Faltam X dias
            return (f"Faltam {delta}d", delta)
    except (ValueError, AttributeError, TypeError):
        return ("Sem prazo", 99999)


def _count_anvisa_open_and_due(
    requests: Sequence[Mapping[str, Any]],
    today: date,
) -> tuple[int, int]:
    """Count open ANVISA requests and those due until today with daily check.

    Regras:
    - total_open = todas as demandas com status em STATUS_OPEN (draft, submitted, in_progress)
    - due_until_today = demandas abertas com:
        * payload.check_daily == True (precisa acompanhar no Solicita)
        * payload.due_date <= today

    Args:
        requests: Sequence of ANVISA request mappings.
        today: Reference date.

    Returns:
        Tuple of (total_open, due_until_today).
    """
    # Try to import STATUS_OPEN from ANVISA module
    try:
        from src.modules.anvisa.constants import STATUS_OPEN

        open_status = STATUS_OPEN
    except ImportError:
        # Fallback: common open statuses
        open_status = {"draft", "submitted", "in_progress"}

    open_total = 0
    due_until_today = 0

    for req in requests:
        status = req.get("status", "")
        if status not in open_status:
            continue

        open_total += 1

        # Check if due until today AND needs daily check
        payload = req.get("payload")
        if isinstance(payload, dict):
            # Só conta em "tarefas hoje" se check_daily=True
            check_daily = payload.get("check_daily", False)
            if not check_daily:
                continue

            due_str = str(payload.get("due_date") or "").strip()
            if due_str:
                due_date = _parse_due_date_iso(due_str)
                if due_date and due_date <= today:
                    due_until_today += 1

    return open_total, due_until_today


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


def _build_anvisa_radar_from_requests(
    requests: Sequence[Mapping[str, Any]],
    today: date,
) -> dict[str, Any]:
    """Build ANVISA radar quadrant from client_anvisa_requests.

    Args:
        requests: Sequence of ANVISA request mappings from client_anvisa_requests table.
        today: Reference date for calculating overdue status.

    Returns:
        Dictionary with pending, overdue counts, status, and enabled flag.
    """
    # Try to import STATUS_OPEN from ANVISA module, fallback to default
    try:
        from src.modules.anvisa.constants import STATUS_OPEN

        open_status = STATUS_OPEN
    except ImportError:
        # Fallback: common open statuses
        open_status = {"draft", "submitted", "in_progress"}

    pending = 0
    overdue = 0

    for request in requests:
        status = request.get("status", "")
        if status not in open_status:
            continue

        # Count as pending (open)
        pending += 1

        # Check if overdue based on payload.due_date
        payload = request.get("payload")
        if isinstance(payload, dict):
            due_str = payload.get("due_date")
            if due_str and isinstance(due_str, str):
                try:
                    due_date = date.fromisoformat(due_str)
                    if due_date < today:
                        overdue += 1
                except ValueError:
                    pass  # Invalid date format, skip

    # Determine quadrant status
    if overdue > 0:
        status_color = "red"
    elif pending > 0:
        status_color = "yellow"
    else:
        status_color = "green"

    # pending here = open but not overdue
    pending_not_overdue = pending - overdue

    return {
        "pending": pending_not_overdue,
        "overdue": overdue,
        "status": status_color,
        "enabled": True,
    }


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

    Currently in ANVISA-only mode: Pendencies and tasks are calculated
    from client_anvisa_requests table only.

    Args:
        org_id: UUID of the organization.
        today: Reference date (defaults to date.today() if None).

    Returns:
        DashboardSnapshot with aggregated data.
    """
    if today is None:
        today = date.today()

    snapshot = DashboardSnapshot()

    # Fetch ANVISA requests once (used for multiple calculations)
    try:
        from infra.repositories.anvisa_requests_repository import list_requests as list_anvisa_requests

        anvisa_requests = list_anvisa_requests(org_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to fetch ANVISA requests: %s", e)
        anvisa_requests = []

    # 1) Active clients count
    try:
        from src.core.services.clientes_service import count_clients

        snapshot.active_clients = count_clients()
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to count active clients: %s", e)
        snapshot.active_clients = 0

    # 2) Pending obligations count - ANVISA only (total open requests)
    # 3) Tasks due today - ANVISA only (open requests with due_date <= today)
    try:
        open_total, due_until_today = _count_anvisa_open_and_due(anvisa_requests, today)
        snapshot.pending_obligations = open_total
        snapshot.tasks_today = due_until_today
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to count ANVISA open/due: %s", e)
        snapshot.pending_obligations = 0
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

    # 5-8) Build ANVISA lists from requests
    # Populate upcoming_deadlines, pending_tasks, and clients_of_the_day
    try:
        from src.modules.anvisa.constants import STATUS_OPEN

        open_status = STATUS_OPEN
    except ImportError:
        open_status = {"draft", "submitted", "in_progress"}

    # Filter open requests
    open_reqs = [req for req in anvisa_requests if req.get("status", "") in open_status]

    # (A) Build upcoming_deadlines: top 5 closest deadlines (sorted by due_date)
    deadlines_data = []
    for req in open_reqs:
        client_id = str(req.get("client_id", ""))
        request_id = str(req.get("id", ""))
        client_data = req.get("clients", {}) or {}
        client_name = client_data.get("razao_social") or f"Cliente #{client_id}"
        request_type = str(req.get("request_type") or "—")

        payload = req.get("payload")
        due_date = None
        if isinstance(payload, dict):
            due_iso = str(payload.get("due_date") or "").strip()
            if due_iso:
                try:
                    due_date = date.fromisoformat(due_iso)
                except (ValueError, AttributeError):
                    pass

        status_badge, days_delta = _due_badge(due_date, today)

        deadlines_data.append(
            {
                "due_date": _format_due_br(due_date),
                "client_id": client_id,
                "client_name": client_name,
                "kind": "ANVISA",
                "title": request_type,
                "status": status_badge,
                "request_id": request_id,
                "_days_delta": days_delta,  # Para ordenação
            }
        )

    # Ordenar por days_delta (menor primeiro = mais urgente)
    deadlines_data.sort(key=lambda x: x["_days_delta"])

    # Remover campo interno de ordenação e pegar top 5
    for item in deadlines_data:
        item.pop("_days_delta", None)
    snapshot.upcoming_deadlines = deadlines_data[:5]

    # (B) Build pending_tasks: tasks with check_daily=True and due_date <= today
    tasks_data = []
    for req in open_reqs:
        payload = req.get("payload")
        if not isinstance(payload, dict):
            continue

        # Só inclui se check_daily=True
        if not payload.get("check_daily", False):
            continue

        due_iso = str(payload.get("due_date") or "").strip()
        if not due_iso:
            continue

        try:
            due_date = date.fromisoformat(due_iso)
        except (ValueError, AttributeError):
            continue

        # Só inclui se due_date <= today
        if due_date > today:
            continue

        client_id = str(req.get("client_id", ""))
        request_id = str(req.get("id", ""))
        client_data = req.get("clients", {}) or {}
        client_name = client_data.get("razao_social") or f"Cliente #{client_id}"
        request_type = str(req.get("request_type") or "—")

        days_overdue = (today - due_date).days

        if days_overdue > 0:
            # Atrasada
            title = f"{request_type} (Atrasada {days_overdue}d)"
            priority = "urgent"
        else:
            # Hoje
            title = f"{request_type} (Hoje)"
            priority = "high"

        tasks_data.append(
            {
                "due_date": _format_due_br(due_date),
                "client_id": client_id,
                "client_name": client_name,
                "title": title,
                "priority": priority,
                "request_id": request_id,
                "_due_date_obj": due_date,  # Para ordenação
            }
        )

    # Ordenar por due_date (mais antigas primeiro)
    tasks_data.sort(key=lambda x: x["_due_date_obj"])

    # Remover campo interno e pegar top 5
    for item in tasks_data:
        item.pop("_due_date_obj", None)
    snapshot.pending_tasks = tasks_data[:5]

    # Atualizar contador de tarefas para refletir todas as tarefas (não só top 5)
    snapshot.tasks_today = len(tasks_data)

    # (C) Build clients_of_the_day: group pending_tasks by client_id
    clients_map: dict[str, dict[str, Any]] = {}
    for task in tasks_data:
        client_id = task["client_id"]
        if client_id not in clients_map:
            clients_map[client_id] = {
                "client_id": client_id,
                "client_name": task["client_name"],
                "obligation_kinds": [],
            }
        # Extrair tipo de demanda do título (remover parte entre parênteses)
        title = task["title"]
        req_type = title.split(" (")[0] if " (" in title else title
        if req_type not in clients_map[client_id]["obligation_kinds"]:
            clients_map[client_id]["obligation_kinds"].append(req_type)

    snapshot.clients_of_the_day = list(clients_map.values())

    # Clear hot_items (not used in ANVISA-only mode yet)
    snapshot.hot_items = []

    # 9) Risk radar - ANVISA uses client_anvisa_requests, SNGPC/SIFAP disabled
    try:
        anvisa_quad = _build_anvisa_radar_from_requests(anvisa_requests, today)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to build ANVISA radar from demands: %s", e)
        anvisa_quad = {"pending": 0, "overdue": 0, "status": "green", "enabled": True}

    snapshot.risk_radar = {
        "ANVISA": anvisa_quad,
        "SNGPC": {"pending": 0, "overdue": 0, "status": "disabled", "enabled": False},
        "SIFAP": {"pending": 0, "overdue": 0, "status": "disabled", "enabled": False},
    }

    # 10) Recent activity - empty in ANVISA-only mode
    snapshot.recent_activity = []

    # 11) Mark as ANVISA-only mode (disables Pendências/Tarefas clicks)
    snapshot.anvisa_only = True

    return snapshot
