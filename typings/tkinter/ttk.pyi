"""Type stubs for tkinter.ttk widgets (minimal coverage for RC Gestor).

This stub file extends tkinter.ttk with type hints for ttkbootstrap extensions
(bootstyle parameter) and other methods that trigger Pyright false positives.

Created for CompatPack-15 on 2025-11-13.
"""

from __future__ import annotations
from typing import Any, Callable, Sequence
from tkinter import Misc

# Common type aliases
Bootstyle = str  # ttkbootstrap style extension (e.g., "success", "danger")


class Frame(Misc):
    """ttk.Frame widget with ttkbootstrap extensions."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        padding: int | tuple[int, ...] | Sequence[int] | None = None,
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    def place(self, **kwargs: Any) -> None: ...


class Label(Misc):
    """ttk.Label widget with ttkbootstrap extensions."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        text: str = "",
        textvariable: Any = None,
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    def configure(self, **kwargs: Any) -> None: ...
    def cget(self, key: str) -> Any: ...


class Button(Misc):
    """ttk.Button widget with ttkbootstrap extensions."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        text: str = "",
        command: Callable[[], Any] | None = None,
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    def configure(self, **kwargs: Any) -> None: ...
    def invoke(self) -> Any: ...


class Entry(Misc):
    """ttk.Entry widget with ttkbootstrap extensions."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        textvariable: Any = None,
        width: int | None = None,
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    def get(self) -> str: ...
    def insert(self, index: int | str, string: str) -> None: ...
    def delete(self, first: int | str, last: int | str | None = None) -> None: ...


class Combobox(Entry):
    """ttk.Combobox widget with ttkbootstrap extensions."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        textvariable: Any = None,
        values: Sequence[str] = (),
        state: str = "normal",
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def configure(self, **kwargs: Any) -> None: ...
    def current(self, newindex: int | None = None) -> int: ...


class Treeview(Misc):
    """ttk.Treeview widget."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        columns: Sequence[str] = (),
        show: str = "tree headings",
        selectmode: str = "extended",
        **kwargs: Any
    ) -> None: ...

    def heading(self, column: str, option: str | None = None, **kw: Any) -> Any: ...
    def column(self, column: str, option: str | None = None, **kw: Any) -> Any: ...
    def insert(self, parent: str, index: int | str, iid: str | None = None, **kw: Any) -> str: ...
    def delete(self, *items: str) -> None: ...
    def get_children(self, item: str | None = None) -> tuple[str, ...]: ...
    def selection(self) -> tuple[str, ...]: ...
    def set(self, item: str, column: str, value: Any = None) -> Any: ...
    def item(self, item: str, option: str | None = None, **kw: Any) -> Any: ...
    def bbox(self, item: str, column: str | None = None) -> tuple[int, int, int, int] | None: ...
    def yview_moveto(self, fraction: float) -> None: ...
    def bind(self, sequence: str, func: Callable[..., Any] | None = None, add: str | None = None) -> str: ...


class Scrollbar(Misc):
    """ttk.Scrollbar widget."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        orient: str = "vertical",
        command: Callable[..., Any] | None = None,
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    def set(self, first: float, last: float) -> None: ...
    def configure(self, command: Callable[..., Any] | None = None, **kwargs: Any) -> None: ...


class Progressbar(Misc):
    """ttk.Progressbar widget."""

    def __init__(
        self,
        master: Misc | None = None,
        *,
        orient: str = "horizontal",
        length: int = 200,
        mode: str = "determinate",
        maximum: float = 100.0,
        value: float = 0.0,
        bootstyle: Bootstyle | None = None,
        **kwargs: Any
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    def start(self, interval: int | None = None) -> None: ...
    def stop(self) -> None: ...
    def step(self, amount: float = 1.0) -> None: ...
    def configure(self, **kwargs: Any) -> None: ...
    def cget(self, key: str) -> Any: ...
    def __setitem__(self, key: str, value: Any) -> None: ...
    def __getitem__(self, key: str) -> Any: ...
