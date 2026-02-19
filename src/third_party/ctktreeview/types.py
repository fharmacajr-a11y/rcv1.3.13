from __future__ import annotations
from typing import TYPE_CHECKING
import tkinter as _tk

if TYPE_CHECKING:
    from typing import TypeAlias

Anchor: TypeAlias = _tk._Anchor
Color: TypeAlias = str | tuple[str, str]
ImageSpec: TypeAlias = _tk._ImageSpec
ScreenUnits: TypeAlias = str | float
Padding: TypeAlias = (
    ScreenUnits
    | tuple[ScreenUnits]
    | tuple[ScreenUnits, ScreenUnits]
    | tuple[ScreenUnits, ScreenUnits, ScreenUnits]
    | tuple[ScreenUnits, ScreenUnits, ScreenUnits, ScreenUnits]
)
