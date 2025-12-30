# -*- coding: utf-8 -*-
"""Unit tests for dashboard_formatters module.

Tests pure formatting functions extracted from dashboard_service.py.
"""

from __future__ import annotations

from datetime import date, datetime

from src.modules.hub.dashboard_formatters import (
    due_badge,
    format_due_br,
    get_first_day_of_month,
    get_last_day_of_month,
    parse_due_date_iso,
    parse_timestamp,
)


class TestGetFirstDayOfMonth:
    """Tests for get_first_day_of_month."""

    def test_first_day_of_january(self) -> None:
        assert get_first_day_of_month(date(2025, 1, 15)) == date(2025, 1, 1)

    def test_first_day_of_december(self) -> None:
        assert get_first_day_of_month(date(2025, 12, 25)) == date(2025, 12, 1)

    def test_already_first_day(self) -> None:
        assert get_first_day_of_month(date(2025, 6, 1)) == date(2025, 6, 1)


class TestGetLastDayOfMonth:
    """Tests for get_last_day_of_month."""

    def test_last_day_of_january(self) -> None:
        assert get_last_day_of_month(date(2025, 1, 15)) == date(2025, 1, 31)

    def test_last_day_of_february_non_leap(self) -> None:
        assert get_last_day_of_month(date(2025, 2, 10)) == date(2025, 2, 28)

    def test_last_day_of_february_leap(self) -> None:
        assert get_last_day_of_month(date(2024, 2, 10)) == date(2024, 2, 29)

    def test_last_day_of_december(self) -> None:
        assert get_last_day_of_month(date(2025, 12, 1)) == date(2025, 12, 31)


class TestParseDueDateIso:
    """Tests for parse_due_date_iso."""

    def test_valid_iso_date(self) -> None:
        assert parse_due_date_iso("2025-12-29") == date(2025, 12, 29)

    def test_valid_iso_date_with_whitespace(self) -> None:
        assert parse_due_date_iso("  2025-06-15  ") == date(2025, 6, 15)

    def test_invalid_format_returns_none(self) -> None:
        assert parse_due_date_iso("29/12/2025") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_due_date_iso("") is None


class TestFormatDueBr:
    """Tests for format_due_br."""

    def test_valid_date(self) -> None:
        assert format_due_br(date(2025, 12, 29)) == "29/12/2025"

    def test_none_returns_dash(self) -> None:
        assert format_due_br(None) == "—"

    def test_single_digit_day_and_month(self) -> None:
        assert format_due_br(date(2025, 1, 5)) == "05/01/2025"


class TestDueBadge:
    """Tests for due_badge."""

    def test_due_none_returns_sem_prazo(self) -> None:
        today = date(2025, 12, 29)
        badge, delta = due_badge(None, today)
        assert badge == "Sem prazo"
        assert delta == 99999

    def test_due_today_returns_hoje(self) -> None:
        today = date(2025, 12, 29)
        badge, delta = due_badge(today, today)
        assert badge == "Hoje"
        assert delta == 0

    def test_due_in_future_returns_faltam(self) -> None:
        today = date(2025, 12, 29)
        due = date(2025, 12, 31)
        badge, delta = due_badge(due, today)
        assert badge == "Faltam 2d"
        assert delta == 2

    def test_due_in_past_returns_atrasada(self) -> None:
        today = date(2025, 12, 29)
        due = date(2025, 12, 27)
        badge, delta = due_badge(due, today)
        assert badge == "Atrasada 2d"
        assert delta == -2


class TestParseTimestamp:
    """Tests for parse_timestamp."""

    def test_datetime_object_passthrough(self) -> None:
        dt = datetime(2025, 12, 29, 10, 30, 0)
        assert parse_timestamp(dt) == dt

    def test_iso_string_without_timezone(self) -> None:
        result = parse_timestamp("2025-12-29T10:30:00")
        assert result == datetime(2025, 12, 29, 10, 30, 0)

    def test_iso_string_with_z_suffix(self) -> None:
        result = parse_timestamp("2025-12-29T10:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 29

    def test_empty_string_returns_none(self) -> None:
        assert parse_timestamp("") is None

    def test_none_returns_none(self) -> None:
        assert parse_timestamp(None) is None

    def test_invalid_string_returns_none(self) -> None:
        assert parse_timestamp("not-a-date") is None
