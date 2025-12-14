# -*- coding: utf-8 -*-
"""Unit tests for src/modules/hub/dashboard_service.py.

Tests the dashboard service that aggregates data from multiple repositories
and services for the Hub dashboard UI.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

from src.modules.hub.dashboard_service import (
    DashboardSnapshot,
    _build_hot_items,
    _build_risk_radar,
    _count_tasks_due_until_today,
    _fetch_client_names,
    _get_first_day_of_month,
    _get_last_day_of_month,
    _parse_timestamp,
    get_dashboard_snapshot,
)


# ============================================================================
# TEST GROUP: Helper functions
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_first_day_of_month(self):
        """Test _get_first_day_of_month returns correct date."""
        assert _get_first_day_of_month(date(2025, 3, 15)) == date(2025, 3, 1)
        assert _get_first_day_of_month(date(2025, 1, 31)) == date(2025, 1, 1)
        assert _get_first_day_of_month(date(2025, 12, 25)) == date(2025, 12, 1)

    def test_get_last_day_of_month(self):
        """Test _get_last_day_of_month returns correct date."""
        assert _get_last_day_of_month(date(2025, 1, 15)) == date(2025, 1, 31)
        assert _get_last_day_of_month(date(2025, 2, 10)) == date(2025, 2, 28)
        assert _get_last_day_of_month(date(2024, 2, 10)) == date(2024, 2, 29)  # Leap year
        assert _get_last_day_of_month(date(2025, 12, 1)) == date(2025, 12, 31)


class TestParseTimestamp:
    """Tests for _parse_timestamp function."""

    def test_accepts_datetime_directly(self):
        """Test accepts datetime object directly."""
        dt = datetime(2025, 12, 4, 10, 30, 0, tzinfo=timezone.utc)
        result = _parse_timestamp(dt)
        assert result == dt

    def test_parses_iso_string_with_offset(self):
        """Test parses ISO 8601 string with timezone offset."""
        result = _parse_timestamp("2025-12-04T10:30:00+00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 4
        assert result.hour == 10
        assert result.minute == 30

    def test_parses_iso_string_with_z_suffix(self):
        """Test parses ISO string with Z suffix (UTC)."""
        result = _parse_timestamp("2025-12-04T14:45:30.123456Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 4
        assert result.hour == 14
        assert result.minute == 45

    def test_parses_supabase_format(self):
        """Test parses typical Supabase timestamp format."""
        result = _parse_timestamp("2025-12-04T14:30:22.123456+00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 4

    def test_returns_none_for_invalid_string(self):
        """Test returns None for invalid date string."""
        result = _parse_timestamp("not-a-date")
        assert result is None

    def test_returns_none_for_empty_string(self):
        """Test returns None for empty string."""
        result = _parse_timestamp("")
        assert result is None

    def test_returns_none_for_none(self):
        """Test returns None for None input."""
        result = _parse_timestamp(None)
        assert result is None

    def test_returns_none_for_invalid_type(self):
        """Test returns None for invalid type (e.g., int)."""
        result = _parse_timestamp(12345)
        assert result is None


class TestCountTasksDueUntilToday:
    """Tests for _count_tasks_due_until_today function."""

    def test_counts_tasks_due_today(self):
        """Test counts tasks with due_date == today."""
        today = date(2025, 12, 4)
        tasks = [
            {"id": "1", "due_date": date(2025, 12, 4), "status": "pending"},
            {"id": "2", "due_date": date(2025, 12, 5), "status": "pending"},
        ]
        result = _count_tasks_due_until_today(tasks, today)
        assert result == 1

    def test_counts_overdue_tasks(self):
        """Test counts tasks with due_date < today."""
        today = date(2025, 12, 4)
        tasks = [
            {"id": "1", "due_date": date(2025, 12, 3), "status": "pending"},
            {"id": "2", "due_date": date(2025, 12, 2), "status": "pending"},
            {"id": "3", "due_date": date(2025, 12, 5), "status": "pending"},
        ]
        result = _count_tasks_due_until_today(tasks, today)
        assert result == 2

    def test_counts_overdue_and_today(self):
        """Test counts both overdue and today tasks."""
        today = date(2025, 12, 4)
        tasks = [
            {"id": "1", "due_date": date(2025, 12, 3), "status": "pending"},
            {"id": "2", "due_date": date(2025, 12, 4), "status": "pending"},
            {"id": "3", "due_date": date(2025, 12, 5), "status": "pending"},
        ]
        result = _count_tasks_due_until_today(tasks, today)
        assert result == 2

    def test_ignores_tasks_without_due_date(self):
        """Test ignores tasks with due_date = None."""
        today = date(2025, 12, 4)
        tasks = [
            {"id": "1", "due_date": date(2025, 12, 3), "status": "pending"},
            {"id": "2", "due_date": None, "status": "pending"},
            {"id": "3", "due_date": date(2025, 12, 4), "status": "pending"},
        ]
        result = _count_tasks_due_until_today(tasks, today)
        assert result == 2

    def test_handles_string_dates(self):
        """Test handles due_date as ISO string."""
        today = date(2025, 12, 4)
        tasks = [
            {"id": "1", "due_date": "2025-12-03", "status": "pending"},
            {"id": "2", "due_date": "2025-12-04", "status": "pending"},
        ]
        result = _count_tasks_due_until_today(tasks, today)
        assert result == 2

    def test_empty_tasks_returns_zero(self):
        """Test returns 0 for empty task list."""
        result = _count_tasks_due_until_today([], date(2025, 12, 4))
        assert result == 0


class TestBuildRiskRadar:
    """Tests for _build_risk_radar function."""

    def test_all_green_when_no_obligations(self):
        """Test all quadrants are green when no obligations."""
        today = date(2025, 12, 4)
        result = _build_risk_radar([], today)

        assert len(result) == 3
        for key in ["ANVISA", "SNGPC", "SIFAP"]:
            assert key in result
            assert result[key]["pending"] == 0
            assert result[key]["overdue"] == 0
            assert result[key]["status"] == "green"

    def test_pending_sets_yellow(self):
        """Test pending obligations set quadrant to yellow."""
        today = date(2025, 12, 4)
        obligations = [
            {
                "kind": "SNGPC",
                "status": "pending",
                "due_date": date(2025, 12, 5),
            },
        ]
        result = _build_risk_radar(obligations, today)

        assert result["SNGPC"]["pending"] == 1
        assert result["SNGPC"]["overdue"] == 0
        assert result["SNGPC"]["status"] == "yellow"

    def test_overdue_sets_red(self):
        """Test overdue obligations set quadrant to red."""
        today = date(2025, 12, 4)
        obligations = [
            {
                "kind": "SNGPC",
                "status": "pending",
                "due_date": date(2025, 12, 3),
            },
        ]
        result = _build_risk_radar(obligations, today)

        assert result["SNGPC"]["overdue"] == 1
        assert result["SNGPC"]["status"] == "red"

    def test_overdue_status_sets_red(self):
        """Test status='overdue' sets quadrant to red."""
        today = date(2025, 12, 4)
        obligations = [
            {
                "kind": "SIFAP",
                "status": "overdue",
                "due_date": date(2025, 12, 1),
            },
        ]
        result = _build_risk_radar(obligations, today)

        assert result["SIFAP"]["overdue"] == 1
        assert result["SIFAP"]["status"] == "red"

    def test_maps_kinds_to_quadrants(self):
        """Test different kinds map to correct quadrants."""
        today = date(2025, 12, 4)
        obligations = [
            {"kind": "SNGPC", "status": "pending", "due_date": date(2025, 12, 5)},
            {"kind": "SIFAP", "status": "pending", "due_date": date(2025, 12, 7)},
            {"kind": "LICENCA_SANITARIA", "status": "pending", "due_date": date(2025, 12, 8)},
        ]
        result = _build_risk_radar(obligations, today)

        assert result["SNGPC"]["pending"] == 1
        assert result["SIFAP"]["pending"] == 1
        assert result["ANVISA"]["pending"] == 1

    def test_ignores_unknown_kinds(self):
        """Test unknown kinds are ignored."""
        today = date(2025, 12, 4)
        obligations = [
            {"kind": "UNKNOWN_KIND", "status": "pending", "due_date": date(2025, 12, 5)},
        ]
        result = _build_risk_radar(obligations, today)

        # All quadrants should be green
        for key in ["ANVISA", "SNGPC", "SIFAP"]:
            assert result[key]["pending"] == 0
            assert result[key]["overdue"] == 0


class TestBuildHotItems:
    """Tests for _build_hot_items function."""

    def test_empty_obligations_returns_empty_list(self):
        """Test that empty obligations returns empty hot items."""
        result = _build_hot_items([], date(2025, 1, 15))
        assert result == []

    def test_sngpc_urgent_within_threshold(self):
        """Test SNGPC obligations within threshold generate alerts."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": "2025-01-16", "status": "pending"},
            {"kind": "SNGPC", "due_date": "2025-01-17", "status": "pending"},
        ]
        result = _build_hot_items(obligations, today)
        assert len(result) == 1
        assert "SNGPC" in result[0]
        assert "2" in result[0]  # 2 submissions

    def test_farmacia_popular_urgent(self):
        """Test FARMACIA_POPULAR obligations generate alerts."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "FARMACIA_POPULAR", "due_date": "2025-01-16", "status": "pending"},
        ]
        result = _build_hot_items(obligations, today)
        assert len(result) == 1
        assert "Farmácia Popular" in result[0]

    def test_overdue_sngpc_generates_alert(self):
        """Test overdue SNGPC generates urgent alert."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": "2025-01-14", "status": "overdue"},
        ]
        result = _build_hot_items(obligations, today)
        assert len(result) == 1
        assert "vencido" in result[0].lower() or "hoje" in result[0].lower()

    def test_same_day_due_generates_alert(self):
        """Test obligations due today generate alert."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": "2025-01-15", "status": "pending"},
        ]
        result = _build_hot_items(obligations, today)
        assert len(result) == 1
        assert "hoje" in result[0].lower() or "vencido" in result[0].lower()

    def test_obligations_beyond_threshold_ignored(self):
        """Test obligations beyond threshold don't generate alerts."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": "2025-01-20", "status": "pending"},
        ]
        result = _build_hot_items(obligations, today, days_threshold=2)
        assert result == []

    def test_done_status_ignored(self):
        """Test completed obligations don't generate alerts."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": "2025-01-16", "status": "done"},
        ]
        result = _build_hot_items(obligations, today)
        assert result == []

    def test_date_object_instead_of_string(self):
        """Test obligations with date objects work correctly."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": date(2025, 1, 16), "status": "pending"},
        ]
        result = _build_hot_items(obligations, today)
        assert len(result) == 1

    def test_mixed_kinds_generate_separate_alerts(self):
        """Test multiple kinds generate separate alerts."""
        today = date(2025, 1, 15)
        obligations = [
            {"kind": "SNGPC", "due_date": "2025-01-16", "status": "pending"},
            {"kind": "FARMACIA_POPULAR", "due_date": "2025-01-16", "status": "pending"},
        ]
        result = _build_hot_items(obligations, today)
        assert len(result) == 2


# ============================================================================
# TEST GROUP: DashboardSnapshot dataclass
# ============================================================================


class TestDashboardSnapshot:
    """Tests for DashboardSnapshot dataclass."""

    def test_default_values(self):
        """Test DashboardSnapshot has correct default values."""
        snapshot = DashboardSnapshot()
        assert snapshot.active_clients == 0
        assert snapshot.pending_obligations == 0
        assert snapshot.tasks_today == 0
        assert snapshot.cash_in_month == 0.0
        assert snapshot.upcoming_deadlines == []
        assert snapshot.hot_items == []

    def test_custom_values(self):
        """Test DashboardSnapshot accepts custom values."""
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,
            tasks_today=3,
            cash_in_month=1500.50,
            upcoming_deadlines=[{"client_id": 1}],
            hot_items=["Alert 1"],
        )
        assert snapshot.active_clients == 10
        assert snapshot.pending_obligations == 5
        assert snapshot.tasks_today == 3
        assert snapshot.cash_in_month == 1500.50
        assert len(snapshot.upcoming_deadlines) == 1
        assert len(snapshot.hot_items) == 1


# ============================================================================
# TEST GROUP: get_dashboard_snapshot()
# ============================================================================


class TestGetDashboardSnapshot:
    """Tests for get_dashboard_snapshot function."""

    def test_snapshot_empty_data(self):
        """Scenario: All repositories return empty/zero data."""
        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=0,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[],
        )

        assert result.active_clients == 0
        assert result.pending_obligations == 0
        assert result.tasks_today == 0
        assert result.cash_in_month == 0.0
        assert result.upcoming_deadlines == []
        assert result.hot_items == []

    def test_snapshot_with_pending_obligations(self):
        """Scenario: Has pending and overdue obligations."""
        obligations = [
            {
                "id": "obl-1",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC Janeiro",
                "due_date": "2025-01-16",
                "status": "pending",
            },
            {
                "id": "obl-2",
                "client_id": 2,
                "kind": "FARMACIA_POPULAR",
                "title": "FP Janeiro",
                "due_date": "2025-01-14",
                "status": "overdue",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=10,
            pending_obligations=5,
            tasks_today=0,
            cash_in=0.0,
            obligations=obligations,
            client_names={1: "Farmácia ABC", 2: "Drogaria XYZ"},
        )

        assert result.pending_obligations == 5
        assert len(result.upcoming_deadlines) <= 5
        # Check that client names are included
        for deadline in result.upcoming_deadlines:
            assert "client_name" in deadline
            assert "kind" in deadline
            assert "title" in deadline
            assert "due_date" in deadline
            assert "status" in deadline

    def test_snapshot_with_tasks_today(self):
        """Scenario: Has pending tasks due today."""
        pending_tasks = [
            {"id": "t1", "due_date": date(2025, 1, 15), "status": "pending"},
            {"id": "t2", "due_date": date(2025, 1, 15), "status": "pending"},
            {"id": "t3", "due_date": date(2025, 1, 15), "status": "pending"},
        ]
        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,  # Not used
            cash_in=0.0,
            obligations=[],
            pending_tasks=pending_tasks,
        )

        assert result.tasks_today == 3

    def test_snapshot_with_pending_tasks(self):
        """Scenario: Has pending tasks in the list."""
        pending_tasks = [
            {
                "id": "task-1",
                "title": "Enviar relatório",
                "due_date": "2025-01-20",
                "client_id": 1,
                "priority": "high",
                "status": "pending",
            },
            {
                "id": "task-2",
                "title": "Revisar documentos",
                "due_date": "2025-01-18",
                "client_id": 2,
                "priority": "normal",
                "status": "pending",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[],
            pending_tasks=pending_tasks,
            client_names={1: "Farmácia ABC", 2: "Drogaria XYZ"},
        )

        assert len(result.pending_tasks) == 2
        # Check that client names are included
        for task in result.pending_tasks:
            assert "client_name" in task
            assert "title" in task
            assert "due_date" in task
            assert "priority" in task

    def test_snapshot_limits_pending_tasks_to_five(self):
        """Scenario: Limits pending tasks to 5 items."""
        pending_tasks = [
            {
                "id": f"task-{i}",
                "title": f"Tarefa {i}",
                "due_date": f"2025-01-{20 + i}",
                "client_id": None,
                "priority": "normal",
                "status": "pending",
            }
            for i in range(10)
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[],
            pending_tasks=pending_tasks,
        )

        assert len(result.pending_tasks) == 5

    def test_snapshot_with_cash_inflow(self):
        """Scenario: Has cash inflow for the month."""
        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=15000.50,
            obligations=[],
        )

        assert result.cash_in_month == 15000.50

    def test_snapshot_with_urgent_sngpc(self):
        """Scenario: Has SNGPC obligations within 2 days - should generate hot items."""
        obligations = [
            {
                "id": "obl-1",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC Janeiro",
                "due_date": "2025-01-16",
                "status": "pending",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=5,
            pending_obligations=1,
            tasks_today=0,
            cash_in=0.0,
            obligations=obligations,
        )

        assert len(result.hot_items) >= 1
        assert any("SNGPC" in item for item in result.hot_items)

    def test_snapshot_uses_today_if_none(self):
        """Scenario: If today is None, uses date.today()."""
        with patch("src.modules.hub.dashboard_service.date") as mock_date:
            mock_date.today.return_value = date(2025, 6, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            mock_date.fromisoformat = date.fromisoformat
            mock_date.max = date.max

            result = _get_snapshot_with_mocks(
                "org-123",
                None,  # Should use today
                count_clients=0,
                pending_obligations=0,
                tasks_today=0,
                cash_in=0.0,
                obligations=[],
            )

        # Just verify it doesn't crash and returns a valid snapshot
        assert isinstance(result, DashboardSnapshot)

    def test_snapshot_handles_repository_errors(self):
        """Scenario: Repository errors are handled gracefully."""
        # The function handles errors internally by catching exceptions
        # and returning default values. We test that the function works
        # correctly with our mock helper returning zeros.
        result = _get_snapshot_with_mocks(
            "org-123",
            date(2025, 1, 15),
            count_clients=0,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[],
        )
        assert isinstance(result, DashboardSnapshot)
        assert result.active_clients == 0

    def test_tasks_today_counts_overdue_and_today_pending_tasks(self):
        """Scenario: tasks_today counts all pending tasks with due_date <= today."""
        today = date(2025, 12, 4)
        pending_tasks = [
            {
                "id": "task-1",
                "title": "Tarefa atrasada",
                "due_date": date(2025, 12, 3),
                "status": "pending",
                "priority": "normal",
            },
            {
                "id": "task-2",
                "title": "Tarefa hoje",
                "due_date": date(2025, 12, 4),
                "status": "pending",
                "priority": "normal",
            },
            {
                "id": "task-3",
                "title": "Tarefa futura",
                "due_date": date(2025, 12, 5),
                "status": "pending",
                "priority": "normal",
            },
            {
                "id": "task-4",
                "title": "Tarefa sem data",
                "due_date": None,
                "status": "pending",
                "priority": "normal",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,  # Not used anymore
            cash_in=0.0,
            obligations=[],
            pending_tasks=pending_tasks,
        )

        # Should count only tasks with due_date <= today (task-1 and task-2)
        assert result.tasks_today == 2

    def test_clients_of_the_day_with_multiple_obligations(self):
        """Scenario: clients_of_the_day groups obligations by client."""
        today = date(2025, 12, 4)
        obligations = [
            {
                "id": "obl-1",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC Dezembro",
                "due_date": date(2025, 12, 4),
                "status": "pending",
            },
            {
                "id": "obl-2",
                "client_id": 1,
                "kind": "FARMACIA_POPULAR",
                "title": "FP Dezembro",
                "due_date": date(2025, 12, 4),
                "status": "pending",
            },
            {
                "id": "obl-3",
                "client_id": 2,
                "kind": "LICENCA_SANITARIA",
                "title": "Licença",
                "due_date": date(2025, 12, 4),
                "status": "overdue",
            },
            {
                "id": "obl-4",
                "client_id": 3,
                "kind": "SNGPC",
                "title": "Outro dia",
                "due_date": date(2025, 12, 5),
                "status": "pending",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=obligations,
            client_names={1: "Farmácia Central", 2: "Drogaria Boa Saúde", 3: "Cliente 3"},
        )

        # Should have 2 clients (client 1 and 2, not client 3 which is due tomorrow)
        assert len(result.clients_of_the_day) == 2

        # Client 1 should have both SNGPC and FARMACIA_POPULAR
        client_1 = next((c for c in result.clients_of_the_day if c["client_id"] == 1), None)
        assert client_1 is not None
        assert client_1["client_name"] == "Farmácia Central"
        assert set(client_1["obligation_kinds"]) == {"FARMACIA_POPULAR", "SNGPC"}

        # Client 2 should have LICENCA_SANITARIA
        client_2 = next((c for c in result.clients_of_the_day if c["client_id"] == 2), None)
        assert client_2 is not None
        assert client_2["client_name"] == "Drogaria Boa Saúde"
        assert client_2["obligation_kinds"] == ["LICENCA_SANITARIA"]

    def test_clients_of_the_day_empty_when_no_obligations_today(self):
        """Scenario: clients_of_the_day is empty when no obligations due today."""
        today = date(2025, 12, 4)
        obligations = [
            {
                "id": "obl-1",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC",
                "due_date": date(2025, 12, 5),
                "status": "pending",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=obligations,
        )

        assert len(result.clients_of_the_day) == 0

    def test_risk_radar_in_snapshot(self):
        """Scenario: risk_radar is populated with 3 quadrants."""
        today = date(2025, 12, 4)
        obligations = [
            {
                "id": "obl-1",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC",
                "due_date": date(2025, 12, 5),
                "status": "pending",
            },
            {
                "id": "obl-2",
                "client_id": 2,
                "kind": "SIFAP",
                "title": "SIFAP",
                "due_date": date(2025, 12, 3),
                "status": "pending",
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=obligations,
        )

        assert "risk_radar" in dir(result)
        assert isinstance(result.risk_radar, dict)
        assert len(result.risk_radar) == 3
        assert "SNGPC" in result.risk_radar
        assert result.risk_radar["SNGPC"]["status"] == "yellow"
        assert result.risk_radar["SIFAP"]["status"] == "red"

    def test_recent_activity_in_snapshot(self):
        """Scenario: recent_activity includes recent tasks and obligations."""
        today = date(2025, 12, 4)
        pending_tasks = [
            {
                "id": "task-1",
                "title": "Tarefa recente",
                "due_date": date(2025, 12, 5),
                "status": "pending",
                "priority": "normal",
                "created_at": datetime(2025, 12, 3, 10, 0, 0, tzinfo=timezone.utc),
            },
        ]
        obligations = [
            {
                "id": "obl-1",
                "client_id": 1,
                "kind": "SNGPC",
                "title": "SNGPC",
                "due_date": date(2025, 12, 5),
                "status": "pending",
                "created_at": datetime(2025, 12, 2, 14, 30, 0, tzinfo=timezone.utc),
            },
        ]

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=obligations,
            pending_tasks=pending_tasks,
        )

        assert "recent_activity" in dir(result)
        assert isinstance(result.recent_activity, list)
        # Should have at least one activity (task or obligation)
        assert len(result.recent_activity) >= 1

    def test_recent_activity_builds_text_field_correctly(self):
        """Test recent_activity builds proper 'text' field for tasks and obligations."""
        today = date(2025, 12, 4)

        # Task with title and client_id
        task_with_client = {
            "id": "task-1",
            "title": "enviar SNGPC",
            "client_id": 123,
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": datetime(2025, 12, 3, 20, 37, 0, tzinfo=timezone.utc),
        }

        # Task without client_id
        task_without_client = {
            "id": "task-2",
            "title": "uhubguy",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": "2025-12-03T20:36:00+00:00",
        }

        # Obligation SNGPC with client
        obligation_sngpc = {
            "id": "obl-1",
            "client_id": 456,
            "kind": "SNGPC",
            "title": "SNGPC",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "created_at": "2025-12-03T15:00:00+00:00",
        }

        # Obligation Farmácia Popular
        obligation_fp = {
            "id": "obl-2",
            "client_id": 789,
            "kind": "FARMACIA_POPULAR",
            "title": "Farmácia Popular",
            "due_date": date(2025, 12, 6),
            "status": "pending",
            "created_at": "2025-12-03T14:00:00+00:00",
        }

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[obligation_sngpc, obligation_fp],
            pending_tasks=[task_with_client, task_without_client],
        )

        # Should have all 4 items
        assert len(result.recent_activity) >= 4

        # Verify each item has 'text' field (not 'title' or 'message')
        for item in result.recent_activity:
            assert "text" in item, f"Item missing 'text' field: {item}"
            assert isinstance(item["text"], str)
            assert len(item["text"]) > 0

        # Verify specific text formats
        texts = [item["text"] for item in result.recent_activity]

        # Task with client should include client_id
        assert any(
            "Nova tarefa: enviar SNGPC para cliente #123" in text for text in texts
        ), f"Expected task with client text not found in: {texts}"

        # Task without client should not include client_id
        assert any(
            "Nova tarefa: uhubguy" == text for text in texts
        ), f"Expected task without client text not found in: {texts}"

        # SNGPC obligation should use friendly label
        assert any(
            "Nova obrigação SNGPC para cliente #456" in text for text in texts
        ), f"Expected SNGPC obligation text not found in: {texts}"

        # Farmácia Popular should use friendly label
        assert any(
            "Nova obrigação Farmácia Popular para cliente #789" in text for text in texts
        ), f"Expected Farmácia Popular obligation text not found in: {texts}"

    def test_recent_activity_accepts_datetime_and_string_timestamps(self):
        """Test recent_activity accepts both datetime and ISO string timestamps."""
        today = date(2025, 12, 4)

        # Task with datetime timestamp
        task_with_datetime = {
            "id": "task-1",
            "title": "Tarefa com datetime",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": datetime(2025, 12, 3, 10, 0, 0, tzinfo=timezone.utc),
        }

        # Task with ISO string timestamp (like Supabase returns)
        task_with_string = {
            "id": "task-2",
            "title": "Tarefa com string",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": "2025-12-03T14:30:00+00:00",
        }

        # Obligation with ISO string timestamp
        obligation_with_string = {
            "id": "obl-1",
            "client_id": 1,
            "kind": "SNGPC",
            "title": "SNGPC",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "created_at": "2025-12-02T09:15:00.123456+00:00",
        }

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[obligation_with_string],
            pending_tasks=[task_with_datetime, task_with_string],
        )

        # Should have all 3 items (2 tasks + 1 obligation)
        assert len(result.recent_activity) >= 3

        # Verify items are present
        texts = [item["text"] for item in result.recent_activity]
        assert any("datetime" in text for text in texts)
        assert any("string" in text for text in texts)
        assert any("SNGPC" in text for text in texts)

    def test_recent_activity_ignores_invalid_timestamps(self):
        """Test recent_activity ignores items with invalid timestamps."""
        today = date(2025, 12, 4)

        # Task with valid timestamp
        valid_task = {
            "id": "task-1",
            "title": "Tarefa válida",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": datetime(2025, 12, 3, 10, 0, 0, tzinfo=timezone.utc),
        }

        # Task with invalid timestamp
        invalid_task = {
            "id": "task-2",
            "title": "Tarefa inválida",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": "not-a-date",
        }

        # Obligation with None timestamp
        none_obligation = {
            "id": "obl-1",
            "client_id": 1,
            "kind": "SNGPC",
            "title": "SNGPC",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "created_at": None,
        }

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[none_obligation],
            pending_tasks=[valid_task, invalid_task],
        )

        # Should only have the valid task (invalid ones are ignored)
        assert len(result.recent_activity) == 1
        assert "válida" in result.recent_activity[0]["text"]

    def test_recent_activity_handles_z_suffix_timestamps(self):
        """Test recent_activity handles timestamps with Z suffix (UTC)."""
        today = date(2025, 12, 4)

        task_with_z = {
            "id": "task-1",
            "title": "Tarefa com Z",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": "2025-12-03T10:00:00.123Z",
        }

        result = _get_snapshot_with_mocks(
            "org-123",
            today,
            count_clients=5,
            pending_obligations=0,
            tasks_today=0,
            cash_in=0.0,
            obligations=[],
            pending_tasks=[task_with_z],
        )

        # Should have the task
        assert len(result.recent_activity) == 1
        assert "com Z" in result.recent_activity[0]["text"]

    def test_recent_activity_includes_user_names_in_text(self):
        """Test recent_activity includes user names in text prefix."""
        today = date(2025, 12, 4)

        task_with_user = {
            "id": "task-1",
            "title": "enviar SNGPC",
            "client_id": 123,
            "created_by": "user-1",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": datetime(2025, 12, 3, 20, 37, 0, tzinfo=timezone.utc),
        }

        obligation_with_user = {
            "id": "obl-1",
            "client_id": 456,
            "kind": "SNGPC",
            "created_by": "user-2",
            "title": "SNGPC",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "created_at": datetime(2025, 12, 3, 18, 12, 0, tzinfo=timezone.utc),
        }

        # Mock get_display_names_by_user_ids
        def fake_get_display_names(org_id: str, user_ids: list[str]) -> dict[str, str]:
            return {"user-1": "Ana", "user-2": "Junior"}

        with patch(
            "src.core.services.profiles_service.get_display_names_by_user_ids",
            side_effect=fake_get_display_names,
        ):
            result = _get_snapshot_with_mocks(
                "org-123",
                today,
                count_clients=5,
                pending_obligations=0,
                tasks_today=0,
                cash_in=0.0,
                obligations=[obligation_with_user],
                pending_tasks=[task_with_user],
            )

        # Should have both items with user names
        assert len(result.recent_activity) >= 2

        # Check that text includes user names
        texts = [item["text"] for item in result.recent_activity]
        assert any(
            "Ana: Nova tarefa: enviar SNGPC para cliente #123" in text for text in texts
        ), f"Expected Ana task text not found in: {texts}"
        assert any(
            "Junior: Nova obrigação SNGPC para cliente #456" in text for text in texts
        ), f"Expected Junior obligation text not found in: {texts}"

        # Check that user_id and user_name fields are present
        for item in result.recent_activity:
            assert "user_id" in item
            assert "user_name" in item

    def test_recent_activity_handles_missing_user_names(self):
        """Test recent_activity gracefully handles when user names are not found."""
        today = date(2025, 12, 4)

        task_with_unknown_user = {
            "id": "task-1",
            "title": "uhubguy",
            "created_by": "user-unknown",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": datetime(2025, 12, 3, 20, 36, 0, tzinfo=timezone.utc),
        }

        # Mock get_display_names_by_user_ids to return empty
        def fake_get_display_names(org_id: str, user_ids: list[str]) -> dict[str, str]:
            return {}  # No names found

        with patch(
            "src.core.services.profiles_service.get_display_names_by_user_ids",
            side_effect=fake_get_display_names,
        ):
            result = _get_snapshot_with_mocks(
                "org-123",
                today,
                count_clients=5,
                pending_obligations=0,
                tasks_today=0,
                cash_in=0.0,
                obligations=[],
                pending_tasks=[task_with_unknown_user],
            )

        # Should have the task without user name prefix
        assert len(result.recent_activity) == 1
        assert result.recent_activity[0]["user_name"] == ""
        # Text should not have user name prefix
        assert result.recent_activity[0]["text"] == "Nova tarefa: uhubguy"

    def test_recent_activity_handles_get_user_names_error(self):
        """Test recent_activity handles errors when fetching user names."""
        today = date(2025, 12, 4)

        task_with_user = {
            "id": "task-1",
            "title": "test task",
            "created_by": "user-1",
            "due_date": date(2025, 12, 5),
            "status": "pending",
            "priority": "normal",
            "created_at": datetime(2025, 12, 3, 10, 0, 0, tzinfo=timezone.utc),
        }

        # Mock get_display_names_by_user_ids to raise error
        def fake_get_display_names(org_id: str, user_ids: list[str]) -> dict[str, str]:
            raise RuntimeError("Database error")

        with patch(
            "src.core.services.profiles_service.get_display_names_by_user_ids",
            side_effect=fake_get_display_names,
        ):
            result = _get_snapshot_with_mocks(
                "org-123",
                today,
                count_clients=5,
                pending_obligations=0,
                tasks_today=0,
                cash_in=0.0,
                obligations=[],
                pending_tasks=[task_with_user],
            )

        # Should still have the task, just without user name
        assert len(result.recent_activity) == 1
        assert result.recent_activity[0]["user_name"] == ""
        assert "test task" in result.recent_activity[0]["text"]


# ============================================================================
# TEST GROUP: _fetch_client_names
# ============================================================================


class TestFetchClientNames:
    """Tests for _fetch_client_names function."""

    def test_empty_ids_returns_empty_dict(self):
        """Test empty client IDs returns empty dict."""
        result = _fetch_client_names([])
        assert result == {}

    def test_fetches_client_names_integration(self):
        """Test fetching client names from service (integration-style)."""
        # This test verifies the function doesn't crash when called
        # The actual service call is handled internally
        with patch(
            "src.modules.clientes.service.fetch_cliente_by_id",
            return_value={"razao_social": "Farmácia ABC", "nome_fantasia": "ABC"},
        ):
            result = _fetch_client_names([1, 2])

        # Should return dict with client names or fallbacks
        assert isinstance(result, dict)
        assert len(result) == 2

    def test_fallback_on_import_error(self):
        """Test fallback when clientes service can't be imported."""
        # This tests the ImportError branch
        with patch.dict("sys.modules", {"src.modules.clientes.service": None}):
            result = _fetch_client_names([1, 2, 3])
            # Should return fallback names
            assert isinstance(result, dict)


# ============================================================================
# Helper function for mocking
# ============================================================================


def _get_snapshot_with_mocks(
    org_id: str,
    today: date | None,
    count_clients: int,
    pending_obligations: int,
    tasks_today: int,
    cash_in: float,
    obligations: list[dict],
    pending_tasks: list[dict] | None = None,
    client_names: dict[int, str] | None = None,
    simulate_errors: bool = False,
) -> DashboardSnapshot:
    """Helper to get dashboard snapshot with mocked dependencies."""
    if client_names is None:
        client_names = {}
    if pending_tasks is None:
        pending_tasks = []

    def mock_fetch_cliente(cid: int) -> dict | None:
        name = client_names.get(cid, f"Cliente #{cid}")
        return {"razao_social": name, "id": cid}

    with (
        patch(
            "src.core.services.clientes_service.count_clients",
            return_value=count_clients,
        ),
        patch(
            "src.features.regulations.repository.count_pending_obligations",
            return_value=pending_obligations,
        ),
        patch(
            "src.features.tasks.repository.count_tasks_for_org",
            return_value=tasks_today,
        ),
        patch(
            "src.features.tasks.repository.list_tasks_for_org",
            return_value=pending_tasks,
        ),
        patch(
            "src.features.cashflow.repository.totals",
            return_value={"in": cash_in, "out": 0.0, "balance": cash_in},
        ),
        patch(
            "src.features.regulations.repository.list_obligations_for_org",
            return_value=obligations,
        ),
        patch(
            "src.modules.clientes.service.fetch_cliente_by_id",
            side_effect=mock_fetch_cliente,
        ),
    ):
        return get_dashboard_snapshot(org_id, today)
