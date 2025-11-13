import os
from typing import Final


def env(key: str, default: str = "") -> str:
    """Get environment variable with fallback default."""
    return os.getenv(key, default) or default


# Chaves centrais (pode expandir conforme o projeto)
DEFAULT_PASSWORD: Final[str] = env("APP_DEFAULT_PASSWORD", "")
SUPABASE_URL: Final[str] = env("SUPABASE_URL", "")
SUPABASE_KEY: Final[str] = env("SUPABASE_KEY", "")
