"""Compatibility bridge for helpers package relocated under src."""

from importlib import import_module
from types import ModuleType
import sys as _sys

_src_pkg: ModuleType = import_module("src.helpers")
__all__ = getattr(_src_pkg, "__all__", [])  # type: ignore[assignment]
__path__ = list(getattr(_src_pkg, "__path__", []))  # type: ignore[assignment]


def __getattr__(name: str):
    return getattr(_src_pkg, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_src_pkg)))


_sys.modules.setdefault(__name__, _sys.modules.get("src.helpers", _src_pkg))
