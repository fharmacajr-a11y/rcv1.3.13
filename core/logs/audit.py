
# core/logs/audit.py — compat sem SQLite
# -*- coding: utf-8 -*-
from datetime import datetime

def ensure_schema():
    return None

def log_client_action(user: str, client_id: int, action: str, details: str | None=None) -> None:
    # No-op; se desejar, criar tabela 'client_audit' no Supabase futuramente.
    return None

def last_action_of_user(user_id: int) -> str | None:
    return None


def last_client_activity_many(client_ids) -> dict[int, tuple[str, str]]:
    # Compat: retorna dict vazio
    return {}
