# -*- coding: utf-8 -*-
"""Controllers headless do MainWindow."""

from __future__ import annotations

from .main_window_pollers import MainWindowPollers
from .screen_registry import register_main_window_screens
from .screen_router import ScreenRouter

__all__ = ["ScreenRouter", "register_main_window_screens", "MainWindowPollers"]
