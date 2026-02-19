# core/logs/activity.py
import sqlite3
from datetime import datetime
from config.paths import USERS_DB_PATH


def _conn():
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(USERS_DB_PATH))


def ensure_schema():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                action   TEXT    NOT NULL,
                ts       TEXT    NOT NULL
            )
        """)
        c.commit()


def log_activity(user_id: int, action: str):
    """Registra uma atividade para o usuário."""
    ensure_schema()
    with _conn() as c:
        c.execute(
            "INSERT INTO user_activity (user_id, action, ts) VALUES (?,?,?)",
            (user_id, action, datetime.now().isoformat(timespec="seconds")),
        )
        c.commit()


def last_activity_of(user_id: int) -> str | None:
    """Retorna a última data/hora registrada para o usuário (ou None)."""
    ensure_schema()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("SELECT ts FROM user_activity WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None
