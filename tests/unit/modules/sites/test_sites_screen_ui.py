from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import webbrowser

import pytest

from src.modules.sites.views.sites_screen import SITES, SitesScreen


def _create_root_or_skip() -> tk.Tk:
    try:
        return tk.Tk()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tkinter indisponível para testes: {exc}")


def _collect_buttons(widget: tk.Widget) -> list[ttk.Button]:
    buttons: list[ttk.Button] = []
    for child in widget.winfo_children():
        if isinstance(child, ttk.Button):
            buttons.append(child)
        else:
            buttons.extend(_collect_buttons(child))
    return buttons


def test_sites_screen_creates_one_button_per_site() -> None:
    root = _create_root_or_skip()
    try:
        screen = SitesScreen(root)
        buttons = _collect_buttons(screen)
        assert len(buttons) == len(SITES)
        texts = {btn.cget("text") for btn in buttons}
        for site in SITES:
            assert site.name in texts
    finally:
        root.destroy()


def test_sites_screen_opens_url_in_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _create_root_or_skip()
    try:
        screen = SitesScreen(root)
        open_calls: list[str] = []

        def fake_open(url: str) -> None:
            open_calls.append(url)

        monkeypatch.setattr(webbrowser, "open_new_tab", fake_open)

        test_url = SITES[0].url
        screen._open_site(test_url)

        assert open_calls == [test_url]
    finally:
        root.destroy()
