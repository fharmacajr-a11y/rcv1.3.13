# -*- coding: utf-8 -*-
"""Small helper to persist UI settings such as window geometry."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

try:
    from src.config.paths import APP_DATA, CLOUD_ONLY  # type: ignore
except Exception:  # pragma: no cover - fallback when src package is unavailable
    try:
        from config.paths import APP_DATA, CLOUD_ONLY  # type: ignore
    except Exception:
        APP_DATA = Path.cwd()
        CLOUD_ONLY = False

log = logging.getLogger(__name__)

SettingsStore = dict[str, Any]

_SETTINGS_FILE: Path = Path(APP_DATA) / "settings.json"
_LOCK: RLock = RLock()
_CACHE: SettingsStore | None = None
_MEMORY_STORE: SettingsStore = {}


def _load_from_disk() -> SettingsStore:
    if not _SETTINGS_FILE.exists():
        return {}
    try:
        with _SETTINGS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        log.debug("settings: falha ao ler settings.json", exc_info=True)
        return {}


def _read_store() -> SettingsStore:
    global _CACHE
    with _LOCK:
        if CLOUD_ONLY:
            return dict(_MEMORY_STORE)
        if _CACHE is None:
            _CACHE = _load_from_disk()
        return dict(_CACHE)


def get_value(key: str, default: Any = None) -> Any:
    """Return a persisted setting or the provided default."""
    store = _read_store()
    return store.get(key, default)


def update_values(mapping: Mapping[str, Any]) -> None:
    """Merge a mapping of settings and persist them."""
    if not isinstance(mapping, dict):
        return
    with _LOCK:
        store = _read_store()
        store.update(dict(mapping))
        _write_store(store)


def set_value(key: str, value: Any) -> None:
    """Persist a single setting value."""
    with _LOCK:
        store = _read_store()
        if value is None:
            store.pop(key, None)
        else:
            store[key] = value
        _write_store(store)


def _write_store(store: SettingsStore) -> None:
    global _CACHE
    if CLOUD_ONLY:
        _MEMORY_STORE.clear()
        _MEMORY_STORE.update(store)
        _CACHE = dict(_MEMORY_STORE)
        return

    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = _SETTINGS_FILE.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(store, fh, ensure_ascii=False, indent=2)
        tmp_path.replace(_SETTINGS_FILE)
        _CACHE = dict(store)
    except Exception:
        log.debug("settings: falha ao escrever settings.json", exc_info=True)
        # mantém cache anterior para não propagar erro ao caller


__all__ = ["get_value", "set_value", "update_values"]
