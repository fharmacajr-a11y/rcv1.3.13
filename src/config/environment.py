from __future__ import annotations

import os
from typing import Optional

# Carrega .env usando resource_path, sem falhar se não houver python-dotenv


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    try:
        from src.utils.resource_path import resource_path

        load_dotenv(resource_path(".env"), override=False)
    except Exception:
        pass


def env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable as string with optional default."""
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    """Get environment variable as boolean.
    
    Treats '1', 'true', 'yes', 'y', 'on' (case-insensitive) as True.
    """
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int = 0) -> int:
    """Get environment variable as integer with fallback to default."""
    try:
        raw_val = os.getenv(name, str(default))
        return int(raw_val)
    except (ValueError, TypeError):
        return default


def cloud_only_default() -> bool:
    """Determine if app should run in cloud-only mode (no local filesystem)."""
    return env_bool("RC_NO_LOCAL_FS", True)
