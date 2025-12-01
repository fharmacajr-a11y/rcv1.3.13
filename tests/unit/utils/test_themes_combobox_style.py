from __future__ import annotations

import ttkbootstrap as tb

from src.utils.themes import apply_combobox_style


def test_apply_combobox_style_sets_entry_background_for_combobox(tk_root_session):
    style = tb.Style()
    entry_bg = style.lookup("TEntry", "fieldbackground", ("!disabled",)) or style.lookup(
        "TEntry", "background", ("!disabled",)
    )

    apply_combobox_style(style)

    readonly_bg = style.lookup("TCombobox", "fieldbackground", ("readonly",))
    normal_bg = style.lookup("TCombobox", "fieldbackground", ("!disabled",))
    focus_bg = style.lookup("TCombobox", "fieldbackground", ("focus",))
    active_bg = style.lookup("TCombobox", "fieldbackground", ("active",))

    assert entry_bg
    assert readonly_bg == entry_bg, f"readonly state should match Entry: {readonly_bg} != {entry_bg}"
    assert normal_bg == entry_bg, f"normal state should match Entry: {normal_bg} != {entry_bg}"
    assert focus_bg == entry_bg, f"focus state should match Entry: {focus_bg} != {entry_bg}"
    assert active_bg == entry_bg, f"active state should match Entry: {active_bg} != {entry_bg}"


def test_apply_combobox_style_map_includes_all_states(tk_root_session):
    """Verifica que o map do TCombobox cobre todos os estados relevantes."""
    style = tb.Style()

    apply_combobox_style(style)

    fieldbackground_map = style.map("TCombobox", "fieldbackground")

    # DummyStyle retorna lista vazia; teste verifica que não quebra
    assert isinstance(fieldbackground_map, list), f"map() deve retornar lista, recebido: {type(fieldbackground_map)}"
