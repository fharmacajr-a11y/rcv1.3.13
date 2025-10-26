import os


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# Chaves centrais (pode expandir conforme o projeto)
DEFAULT_PASSWORD = env("APP_DEFAULT_PASSWORD", "")
SUPABASE_URL = env("SUPABASE_URL", "")
SUPABASE_KEY = env("SUPABASE_KEY", "")
