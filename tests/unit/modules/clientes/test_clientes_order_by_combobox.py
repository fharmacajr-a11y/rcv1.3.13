from __future__ import annotations

import tkinter as tk

from src.modules.clientes.views.main_screen import MainScreenFrame


def _make_dummy_main_screen(root: tk.Misc, current_order: str) -> MainScreenFrame:
    ms: MainScreenFrame = object.__new__(MainScreenFrame)
    ms.var_ordem = tk.StringVar(master=root, value=current_order)
    ms._current_order_by = current_order
    ms.carregar_called = 0

    def _fake_carregar():
        ms.carregar_called += 1

    ms.carregar = _fake_carregar  # type: ignore[assignment]
    return ms


def test_order_by_no_refresh_when_unchanged(tk_root_session):
    ms = _make_dummy_main_screen(tk_root_session, "Razão Social (A→Z)")
    ms.var_ordem.set("Razão Social (A→Z)")

    ms._on_order_changed()

    assert ms.carregar_called == 0


def test_order_by_refresh_when_changed(tk_root_session):
    ms = _make_dummy_main_screen(tk_root_session, "Razão Social (A→Z)")
    ms.var_ordem.set("Última Alteração (mais recente)")

    ms._on_order_changed()

    assert ms.carregar_called == 1
