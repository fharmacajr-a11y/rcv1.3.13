# -*- coding: utf-8 -*-
"""Dashboard models and data structures.

Contains dataclasses, TypedDicts, and type aliases used by the dashboard service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "DashboardSnapshot",
]


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
