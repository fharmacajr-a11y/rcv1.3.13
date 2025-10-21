from __future__ import annotations

import os
from typing import Optional

from shared.config.environment import load_env, env_str

load_env()

SUPABASE_URL: Optional[str] = env_str("SUPABASE_URL")
SUPABASE_ANON_KEY: Optional[str] = env_str("SUPABASE_ANON_KEY")
SUPABASE_BUCKET: str = env_str("SUPABASE_BUCKET") or "rc-docs"

HEALTHCHECK_INTERVAL_SECONDS = float(os.getenv("RC_HEALTHCHECK_INTERVAL", "30"))
HEALTHCHECK_UNSTABLE_THRESHOLD = float(os.getenv("RC_HEALTHCHECK_UNSTABLE", "60"))
HEALTHCHECK_USE_RPC = True
HEALTHCHECK_RPC_NAME = "ping"
HEALTHCHECK_FALLBACK_TABLE = "profiles"
HEALTHCHECK_DISABLED = os.getenv("RC_HEALTHCHECK_DISABLE", "0") == "1"
