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
        from src.infra.repositories.anvisa_requests_repository import list_requests as list_anvisa_requests

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
