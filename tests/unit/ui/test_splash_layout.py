# -*- coding: utf-8 -*-
"""Testes lógicos para helpers do splash (sem Tk/ttkbootstrap)."""

from __future__ import annotations

from src.ui.splash import (
    SPLASH_MIN_DURATION_MS,
    SPLASH_PROGRESS_MAX,
    SPLASH_PROGRESS_STEPS,
    _center_coords,
    _compute_remaining_ms,
)


def test_center_coords_centers_within_bounds() -> None:
    x, y = _center_coords(1920, 1080, 640, 480)
    assert x == (1920 - 640) // 2
    assert y == (1080 - 480) // 2
    assert x >= 0 and y >= 0
    assert x + 640 <= 1920
    assert y + 480 <= 1080


def test_center_coords_never_negative_when_window_larger() -> None:
    x, y = _center_coords(800, 600, 1600, 1200)
    assert x == 0
    assert y == 0


def test_compute_remaining_ms_returns_delta_when_not_elapsed() -> None:
    created = 10.0
    now = 10.5  # 500ms depois
    remaining = _compute_remaining_ms(created, now, 2000)
    assert remaining == 1500


def test_compute_remaining_ms_zero_when_elapsed_or_more() -> None:
    created = 5.0
    now = 8.0  # 3000ms depois
    remaining = _compute_remaining_ms(created, now, 2000)
    assert remaining == 0


def test_compute_remaining_ms_never_negative_even_if_clock_skews() -> None:
    created = 5.0
    now = 4.0  # clock voltou; elapsed negativo
    remaining = _compute_remaining_ms(created, now, 2000)
    assert remaining == 2000


def test_splash_constants_are_positive() -> None:
    assert SPLASH_MIN_DURATION_MS >= 1000
    assert SPLASH_PROGRESS_MAX > 0
    assert SPLASH_PROGRESS_STEPS > 0
