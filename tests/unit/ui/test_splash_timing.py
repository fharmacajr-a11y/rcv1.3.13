# -*- coding: utf-8 -*-
"""Testes da lógica de tempo mínimo do splash (sem UI real)."""

from __future__ import annotations

from src.ui import splash as splash_module


def test_splash_remaining_time_not_negative() -> None:
    """Se já passou mais que o tempo mínimo, o restante deve ser zero."""
    min_ms = splash_module.SPLASH_MIN_DURATION_MS
    created_at = 0.0
    now = 10.0  # 10 segundos depois

    remaining = splash_module._compute_remaining_ms(created_at, now, min_ms)
    assert remaining == 0


def test_splash_remaining_time_positive_when_early() -> None:
    """Se ainda não passou o tempo mínimo, parte restante deve ser positiva."""
    min_ms = splash_module.SPLASH_MIN_DURATION_MS
    created_at = 0.0
    now = 1.5  # 1.5s depois => ainda falta

    remaining = splash_module._compute_remaining_ms(created_at, now, min_ms)
    assert 3000 <= remaining <= 4000  # tolerância a arredondamento
