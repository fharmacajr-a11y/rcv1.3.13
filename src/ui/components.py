from __future__ import annotations

import importlib
import os

__path__ = [os.path.join(os.path.dirname(__file__), "components")]

_MODULES = ("buttons", "inputs", "lists", "modals", "misc")

for _name in _MODULES:
    _module = importlib.import_module(
        f".components.{_name}", package=__package__ or "ui"
    )
    globals().update(
        {k: v for k, v in _module.__dict__.items() if not k.startswith("_")}
    )

__all__ = [name for name in globals().keys() if not name.startswith("_")]
