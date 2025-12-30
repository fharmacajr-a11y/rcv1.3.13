# -*- coding: utf-8 -*-
"""Pure formatting functions for Hub dashboard.

This module contains date/string/label formatting helpers that do NOT access
DB, network, or UI directly. They are extracted from dashboard_service.py
to reduce coupling and improve testability.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def get_first_day_of_month(d: date) -> date:
    """Returns the first day of the month for a given date."""
    return d.replace(day=1)


def get_last_day_of_month(d: date) -> date:
    """Returns the last day of the month for a given date."""
    # Go to next month's first day, then subtract one day
    if d.month == 12:
        next_month = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
    return next_month - timedelta(days=1)


def parse_due_date_iso(due: str) -> date | None:
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


def format_due_br(d: date | None) -> str:
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


def due_badge(due: date | None, today: date) -> tuple[str, int]:
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


def parse_timestamp(value: object) -> datetime | None:
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


# Aliases with underscore prefix for backward compatibility
_get_first_day_of_month = get_first_day_of_month
_get_last_day_of_month = get_last_day_of_month
_parse_due_date_iso = parse_due_date_iso
_format_due_br = format_due_br
_due_badge = due_badge
_parse_timestamp = parse_timestamp
