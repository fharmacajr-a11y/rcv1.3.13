
"""Runtime hotfix to force cloud-only behavior and avoid local FS writes.
- Sets RC_NO_LOCAL_FS=1 before any path resolution.
- Provides safe temp directories for any accidental writes.
"""
from __future__ import annotations
import os, tempfile
from pathlib import Path

# Force cloud-only mode early
os.environ.setdefault("RC_NO_LOCAL_FS", "1")

# Provide conventional temp dirs used by legacy code, if any
TMP_BASE = Path(tempfile.gettempdir()) / "rc_void"
TMP_BASE.mkdir(parents=True, exist_ok=True)

# Best-effort monkeypatch for config.paths if already imported
try:
    import importlib
    paths = importlib.import_module("config.paths")
    try:
        setattr(paths, "CLOUD_ONLY", True)
    except Exception:
        pass
    for name in ("DB_DIR", "DOCS_DIR"):
        try:
            setattr(paths, name, TMP_BASE / name.lower())
            (TMP_BASE / name.lower()).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
except Exception:
    # If config.paths isn't imported yet, that's fine: the env flag will take effect on first import.
    pass
