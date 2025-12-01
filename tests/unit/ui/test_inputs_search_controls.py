import tkinter as tk

import pytest

from src.ui.components.inputs import PLACEHOLDER_FG, PLACEHOLDER_TEXT, create_search_controls


@pytest.fixture
def tk_root(tk_root_session: tk.Tk):
    """Reutiliza o root de teste compartilhado definido em conftest.py."""
    return tk_root_session


def _has_selection(widget: tk.Widget) -> bool:
    try:
        return bool(widget.selection_present())
    except Exception:
        try:
            widget.index("sel.first")
            return True
        except Exception:
            return False


def test_search_placeholder_focus_cycle(tk_root: tk.Tk) -> None:
    controls = create_search_controls(
        tk_root,
        order_choices=["Razao Social (A-Z)", "CNPJ (A-Z)"],
        default_order="Razao Social (A-Z)",
        on_search=None,
        on_clear=None,
        on_order_change=None,
        on_status_change=None,
    )
    tk_root.update_idletasks()

    placeholder = controls.placeholder_label
    entry = controls.entry
    assert placeholder is not None
    assert placeholder.cget("text") == PLACEHOLDER_TEXT
    assert placeholder.cget("foreground") == PLACEHOLDER_FG
    assert placeholder.winfo_manager() == "place"

    entry.event_generate("<FocusIn>")
    tk_root.update_idletasks()
    assert not placeholder.winfo_ismapped()

    dummy = tk.Entry(tk_root)
    dummy.pack()
    dummy.focus_set()
    entry.event_generate("<FocusOut>")
    controls.search_var.set("reset")
    controls.search_var.set("")
    if controls.placeholder_updater:
        controls.placeholder_updater()
    tk_root.update_idletasks()
    assert placeholder.place_info()


def test_order_combobox_clears_text_selection(tk_root: tk.Tk) -> None:
    controls = create_search_controls(
        tk_root,
        order_choices=["Razao Social (A-Z)", "CNPJ (A-Z)"],
        default_order="Razao Social (A-Z)",
        on_search=None,
        on_clear=None,
        on_order_change=None,
        on_status_change=None,
    )
    tk_root.update_idletasks()

    combo = controls.order_combobox
    combo.selection_range(0, tk.END)
    assert _has_selection(combo)

    controls.order_var.set("CNPJ (A-Z)")
    tk_root.update_idletasks()

    assert not _has_selection(combo)


def test_status_combobox_clears_text_selection(tk_root: tk.Tk) -> None:
    controls = create_search_controls(
        tk_root,
        order_choices=["Razao Social (A-Z)", "CNPJ (A-Z)"],
        default_order="Razao Social (A-Z)",
        on_search=None,
        on_clear=None,
        on_order_change=None,
        on_status_change=None,
        status_choices=["Aguardando pagamento", "Pago"],
    )
    tk_root.update_idletasks()

    combo = controls.status_combobox
    combo.selection_range(0, tk.END)
    assert _has_selection(combo)

    controls.status_var.set("Pago")
    tk_root.update_idletasks()

    assert not _has_selection(combo)
