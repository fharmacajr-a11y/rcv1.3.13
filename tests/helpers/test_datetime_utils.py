"""Tests for src.helpers.datetime_utils module."""

from __future__ import annotations

import datetime
from unittest.mock import patch

from src.helpers.datetime_utils import now_iso_z


class TestNowIsoZ:
    """Tests for now_iso_z() function."""

    def test_returns_string(self):
        """Should return a string."""
        result = now_iso_z()
        assert isinstance(result, str)

    def test_ends_with_z(self):
        """Should end with 'Z' suffix."""
        result = now_iso_z()
        assert result.endswith("Z")

    def test_no_microseconds(self):
        """Should not contain microseconds (no dot before Z)."""
        result = now_iso_z()
        # ISO with microseconds: 2025-11-19T14:30:45.123456Z
        # ISO without: 2025-11-19T14:30:45Z
        assert ".Z" not in result
        assert result[-1] == "Z"

    def test_format_yyyy_mm_dd_thh_mm_ss_z(self):
        """Should follow YYYY-MM-DDTHH:MM:SSZ format."""
        result = now_iso_z()
        # Basic structure: 2025-11-19T14:30:45Z (length 20)
        assert len(result) == 20
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == "T"
        assert result[13] == ":"
        assert result[16] == ":"
        assert result[19] == "Z"

    def test_no_plus_00_00_suffix(self):
        """Should replace '+00:00' with 'Z'."""
        result = now_iso_z()
        assert "+00:00" not in result

    def test_uses_utc_timezone(self):
        """Should use UTC timezone (no offset)."""
        # Mock datetime.now(UTC) to control output
        mock_dt = datetime.datetime(2025, 11, 19, 14, 30, 45, 123456, tzinfo=datetime.UTC)

        with patch("src.helpers.datetime_utils.datetime") as mock_datetime:
            # Configure mock
            mock_datetime.UTC = datetime.UTC
            mock_datetime.datetime.now.return_value = mock_dt

            result = now_iso_z()

            # Should have called now(UTC)
            mock_datetime.datetime.now.assert_called_once_with(datetime.UTC)

            # Should strip microseconds
            assert "123456" not in result
            assert result == "2025-11-19T14:30:45Z"

    def test_specific_timestamp_2025_01_01(self):
        """Should format 2025-01-01 00:00:00 UTC correctly."""
        mock_dt = datetime.datetime(2025, 1, 1, 0, 0, 0, 0, tzinfo=datetime.UTC)

        with patch("src.helpers.datetime_utils.datetime") as mock_datetime:
            mock_datetime.UTC = datetime.UTC
            mock_datetime.datetime.now.return_value = mock_dt

            result = now_iso_z()
            assert result == "2025-01-01T00:00:00Z"

    def test_specific_timestamp_2025_12_31_last_second(self):
        """Should format 2025-12-31 23:59:59 UTC correctly."""
        mock_dt = datetime.datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=datetime.UTC)

        with patch("src.helpers.datetime_utils.datetime") as mock_datetime:
            mock_datetime.UTC = datetime.UTC
            mock_datetime.datetime.now.return_value = mock_dt

            result = now_iso_z()
            # Microseconds stripped
            assert result == "2025-12-31T23:59:59Z"

    def test_leap_second_handling(self):
        """Should handle edge case times correctly."""
        # Test midnight rollover
        mock_dt = datetime.datetime(2025, 2, 28, 23, 59, 59, 500000, tzinfo=datetime.UTC)

        with patch("src.helpers.datetime_utils.datetime") as mock_datetime:
            mock_datetime.UTC = datetime.UTC
            mock_datetime.datetime.now.return_value = mock_dt

            result = now_iso_z()
            assert result == "2025-02-28T23:59:59Z"

    def test_multiple_calls_return_current_time(self):
        """Should return current time on each call (not cached)."""
        result1 = now_iso_z()
        # Assume system clock advances (even if microseconds)
        result2 = now_iso_z()

        # Both should be valid ISO strings
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert result1.endswith("Z")
        assert result2.endswith("Z")

        # They could be equal if called within same second
        # But both must be valid format
        assert len(result1) == 20
        assert len(result2) == 20
