# -*- coding: utf-8 -*-
"""Testes do helper _destroy_splash com callback."""

from __future__ import annotations

from typing import Callable

from src.core import auth_bootstrap


class DummySplash:
    """Dublê simples de splash com close(on_closed)."""

    def __init__(self) -> None:
        self.closed = False
        self.callback: Callable[[], None] | None = None

    def close(self, on_closed: Callable[[], None] | None = None) -> None:
        self.closed = True
        self.callback = on_closed
        if on_closed is not None:
            on_closed()


def test_destroy_splash_calls_close_and_callback() -> None:
    splash = DummySplash()
    called: list[str] = []

    def marker() -> None:
        called.append("done")

    auth_bootstrap._destroy_splash(splash, on_closed=marker)

    assert splash.closed is True
    assert called == ["done"]


def test_destroy_splash_without_splash_calls_callback_immediately() -> None:
    called: list[str] = []

    def marker() -> None:
        called.append("done")

    auth_bootstrap._destroy_splash(None, on_closed=marker)

    assert called == ["done"]
