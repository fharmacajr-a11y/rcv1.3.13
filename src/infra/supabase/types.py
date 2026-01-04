from __future__ import annotations

import os
from typing import Final

from src.config.environment import load_env, env_str

load_env()

# Supabase connection credentials
SUPABASE_URL: str | None = env_str("SUPABASE_URL")
SUPABASE_ANON_KEY: str | None = env_str("SUPABASE_ANON_KEY")
SUPABASE_BUCKET: str = env_str("SUPABASE_BUCKET") or "rc-docs"

# Health check configuration
HEALTHCHECK_INTERVAL_SECONDS: Final[float] = float(os.getenv("RC_HEALTHCHECK_INTERVAL", "30"))
HEALTHCHECK_UNSTABLE_THRESHOLD: Final[float] = float(os.getenv("RC_HEALTHCHECK_UNSTABLE", "60"))
HEALTHCHECK_USE_RPC: Final[bool] = True
HEALTHCHECK_RPC_NAME: Final[str] = "ping"
HEALTHCHECK_FALLBACK_TABLE: Final[str] = "profiles"
HEALTHCHECK_DISABLED: Final[bool] = os.getenv("RC_HEALTHCHECK_DISABLE", "0") == "1"
