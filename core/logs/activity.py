
# core/logs/activity.py — compat sem SQLite
from datetime import datetime

def ensure_schema():
    return None

def log_activity(user_id: int, action: str):
    # No-op / could be extended to Supabase Storage or table 'activity'
    return None

def last_action_of_user(user_id: int) -> str | None:
    return None
