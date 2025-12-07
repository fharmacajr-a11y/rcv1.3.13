"""Tests for build_main_screen_state function."""

from __future__ import annotations

import sys
from unittest import mock

# Mock tkinter before importing anything from src
sys.modules['tkinter'] = mock.MagicMock()
sys.modules['tkinter.messagebox'] = mock.MagicMock()
sys.modules['tkinter.filedialog'] = mock.MagicMock()

from src.modules.clientes.views.main_screen_controller import (
    MainScreenState,
    build_main_screen_state,
)


class TestBuildMainScreenState:
    """Tests for build_main_screen_state function."""

    def test_build_main_screen_state_default_parameters(self):
        """Test build_main_screen_state with default parameters."""
        state = build_main_screen_state()

        assert isinstance(state, MainScreenState)
        assert state.order_by == "id"
        assert state.order_direction == "ASC"
        assert state.is_online is False

    def test_build_main_screen_state_with_is_online_true(self):
        """Test build_main_screen_state accepts is_online parameter."""
        state = build_main_screen_state(is_online=True)

        assert state.is_online is True
        assert state.order_by == "id"
        assert state.order_direction == "ASC"

    def test_build_main_screen_state_with_is_online_false(self):
        """Test build_main_screen_state with is_online=False."""
        state = build_main_screen_state(is_online=False)

        assert state.is_online is False

    def test_build_main_screen_state_with_all_parameters(self):
        """Test build_main_screen_state with all parameters."""
        state = build_main_screen_state(
            order_by="nome",
            order_direction="DESC",
            is_online=True,
        )

        assert state.order_by == "nome"
        assert state.order_direction == "DESC"
        assert state.is_online is True

    def test_build_main_screen_state_without_is_online(self):
        """Test build_main_screen_state works when is_online is not provided."""
        # This tests backward compatibility
        state = build_main_screen_state(order_by="razao", order_direction="ASC")

        assert state.order_by == "razao"
        assert state.order_direction == "ASC"
        assert state.is_online is False  # Should default to False
