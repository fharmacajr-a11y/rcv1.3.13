"""Hotfix em runtime para forçar modo cloud-only e evitar escritas no FS local."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

# Force cloud-only mode early
os.environ.setdefault("RC_NO_LOCAL_FS", "1")

# Provide conventional temp dirs used by legacy code, if any
TMP_BASE: Path = Path(tempfile.gettempdir()) / "rc_void"
TMP_BASE.mkdir(parents=True, exist_ok=True)

log = logging.getLogger(__name__)

# Best-effort monkeypatch for config.paths if already imported
try:
    import importlib

    paths = importlib.import_module("config.paths")
    try:
        setattr(paths, "CLOUD_ONLY", True)
    except Exception as exc:
        log.debug("Não foi possível forçar CLOUD_ONLY em config.paths", exc_info=exc)
    for name in ("DB_DIR", "DOCS_DIR"):
        try:
            setattr(paths, name, TMP_BASE / name.lower())
            (TMP_BASE / name.lower()).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            log.debug("Falha ao ajustar path %s para cloud-only", name, exc_info=exc)
except Exception as exc:
    # If config.paths isn't imported yet, that's fine: the env flag will take effect on first import.
    log.debug("config.paths não carregado ao aplicar hotfix cloud-only", exc_info=exc)
