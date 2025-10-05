# Project path helpers for Gestor de Clientes.
from __future__ import annotations

import sys
from pathlib import Path

def _base_dir() -> Path:
    """Return the base directory for both PyInstaller and source execution."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR: Path = _base_dir()
DB_PATH: Path = BASE_DIR / "db" / "clientes.db"
DOCS_DIR: Path = BASE_DIR / "clientes_docs"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

__all__ = ["BASE_DIR", "DB_PATH", "DOCS_DIR"]

USERS_DB_PATH: Path = BASE_DIR / "db" / "users.db"
__all__.extend(["USERS_DB_PATH"]) 
