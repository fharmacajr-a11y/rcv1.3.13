"""Type stubs for tkinter standard library (minimal coverage for RC Gestor).

This stub file provides type hints for tkinter widgets and methods that trigger
false positives in Pyright due to incomplete upstream stubs or ttkbootstrap extensions.

Created for CompatPack-15 on 2025-11-13.
"""

from __future__ import annotations
from typing import Any, Callable, Protocol, overload, runtime_checkable

# Base Protocol for Misc widgets
@runtime_checkable
class Misc(Protocol):
    """Protocol for tkinter Misc mixin."""

    def wm_transient(self, master: Misc | None = None) -> str | None: ...

    def grid_bbox(
        self,
        column: int | None = None,
        row: int | None = None,
        col2: int | None = None,
        row2: int | None = None,
    ) -> tuple[int, int, int, int]: ...

    def grid_columnconfigure(
        self,
        index: int,
        weight: int | None = None,
        minsize: int | None = None,
        pad: int | None = None,
        **kw: Any
    ) -> Any: ...

    def grid_rowconfigure(
        self,
        index: int,
        weight: int | None = None,
        minsize: int | None = None,
        pad: int | None = None,
        **kw: Any
    ) -> Any: ...

    def winfo_exists(self) -> bool: ...
    def winfo_toplevel(self) -> Misc: ...
    def update_idletasks(self) -> None: ...
    def after(self, ms: int, func: Callable[..., Any] | None = None, *args: Any) -> str: ...
    def bind(self, sequence: str, func: Callable[..., Any] | None = None, add: str | None = None) -> str: ...
    def configure(self, **kwargs: Any) -> None: ...
    def config(self, **kwargs: Any) -> None: ...


# Toplevel window
class Toplevel(Misc):
    """tkinter Toplevel window."""

    def __init__(
        self,
        master: Misc | None = None,
        **kwargs: Any
    ) -> None: ...

    def destroy(self) -> None: ...
    def title(self, string: str | None = None) -> str | None: ...
    def geometry(self, newGeometry: str | None = None) -> str | None: ...
    def grab_set(self) -> None: ...
    def grab_release(self) -> None: ...
    def focus_set(self) -> None: ...
    def protocol(self, name: str, func: Callable[[], Any] | None = None) -> str | None: ...


# Wm Protocol
@runtime_checkable
class Wm(Protocol):
    """Protocol for window manager methods."""

    def wm_transient(self, master: Misc | None = None) -> str | None: ...
    def wm_attributes(self, *args: Any) -> Any: ...
    def wm_title(self, string: str | None = None) -> str | None: ...
    def wm_geometry(self, newGeometry: str | None = None) -> str | None: ...


# Tcl_Obj placeholder (used in some tkinter stubs)
class Tcl_Obj:
    """Placeholder for Tcl object type."""
    ...
