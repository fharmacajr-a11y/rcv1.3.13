# -*- coding: utf-8 -*-
"""UI compatibility layer for tests - NO ttkbootstrap dependency.

This module provides widget aliases that tests can use instead of directly
importing ttkbootstrap. Uses tkinter.ttk for themed widgets.

Usage in tests:
    from tests import ui_compat as tb
    frame = tb.Frame(parent)
    label = tb.Label(parent, text="Test")
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


class Frame(ttk.Frame):
    """Frame alias using ttk.Frame (supports padding)."""

    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        # Ignore bootstyle if passed (for backward compat with old tests)
        kwargs.pop("bootstyle", None)
        super().__init__(master, **kwargs)


class Label(tk.Label):  # type: ignore[misc]
    """Label alias using tk.Label."""

    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        # Ignore bootstyle if passed
        kwargs.pop("bootstyle", None)
        super().__init__(master, **kwargs)


class Button(ttk.Button):
    """Button alias using ttk.Button."""

    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        # Ignore bootstyle if passed
        kwargs.pop("bootstyle", None)
        super().__init__(master, **kwargs)


class Labelframe(ttk.LabelFrame):  # type: ignore[misc]
    """Labelframe alias using ttk.LabelFrame (supports padding)."""

    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        # Ignore bootstyle if passed
        kwargs.pop("bootstyle", None)
        super().__init__(master, **kwargs)


# Aliases
LabelFrame = Labelframe


class Toplevel(tk.Toplevel):  # type: ignore[misc]
    """Toplevel alias using tk.Toplevel."""

    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        # Ignore bootstyle if passed
        kwargs.pop("bootstyle", None)
        super().__init__(master, **kwargs)


# TTK widgets that are already compatible
Treeview = ttk.Treeview
Scrollbar = ttk.Scrollbar
Separator = ttk.Separator  # type: ignore[misc]
