# core/logs/audit.py — v3.3.2 (batch+utf8)
# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime
from config.paths import USERS_DB_PATH

def _conn():
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(USERS_DB_PATH))

def ensure_schema():
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS client_audit (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                user_id   INTEGER,
                action    TEXT,
                ts        TEXT,
                details   TEXT
            )
            """
        )
        # Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_client_audit_client ON client_audit(client_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_client_audit_user   ON client_audit(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_client_audit_ts     ON client_audit(ts)")
        c.commit()

def _create_user_if_needed(username: str | None) -> int | None:
    """Tenta obter/criar o usuário na tabela 'users'. Se a tabela não existir, retorna None."""
    if not username:
        return None
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            r = cur.fetchone()
            if r:
                return r[0]
            cur.execute("INSERT INTO users (username) VALUES (?)", (username,))
            c.commit()
            return cur.lastrowid
    except Exception:
        # Tabela 'users' ainda não existe — não é crítico para auditar
        return None

def log_client_action(username: str | None, client_id: int, action: str, details: str = "") -> None:
    ensure_schema()
    uid = _create_user_if_needed(username)
    with _conn() as c:
        c.execute(
            "INSERT INTO client_audit (client_id, user_id, action, ts, details) VALUES (?,?,?,?,?)",
            (client_id, uid, action, datetime.now().isoformat(timespec="seconds"), details)
        )
        c.commit()

def last_client_activity(client_id: int) -> tuple[str, str] | None:
    """Retorna (ts, username) da última ação. Fallback se 'users' não existir."""
    ensure_schema()
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute(
                """
                SELECT a.ts, COALESCE(u.username, '') AS uname
                  FROM client_audit a
             LEFT JOIN users u ON u.id = a.user_id
                 WHERE a.client_id=?
              ORDER BY a.id DESC LIMIT 1
                """,
                (client_id,),
            )
            r = cur.fetchone()
            return (r[0], r[1]) if r else None
    except Exception:
        with _conn() as c:
            cur = c.cursor()
            cur.execute(
                "SELECT ts FROM client_audit WHERE client_id=? ORDER BY id DESC LIMIT 1",
                (client_id,),
            )
            r = cur.fetchone()
            return (r[0], "") if r else None

def last_client_activity_many(client_ids) -> dict[int, tuple[str, str]]:
    """
    Versão em lote para evitar N+1.
    Retorna {client_id: (ts, username)} apenas para os ids encontrados.
    """
    ensure_schema()
    ids = []
    for cid in (client_ids or []):
        try:
            ids.append(int(cid))
        except Exception:
            continue
    if not ids:
        return {}

    ids = sorted(set(ids))
    placeholders = ",".join(["?"] * len(ids))

    # Seleciona o último registro (maior id) por cliente e faz LEFT JOIN com users
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            f"""
            WITH max_row AS (
                SELECT client_id, MAX(id) AS max_id
                  FROM client_audit
                 WHERE client_id IN ({placeholders})
              GROUP BY client_id
            )
            SELECT a.client_id, a.ts, COALESCE(u.username, '') AS uname
              FROM client_audit a
         LEFT JOIN users u ON u.id = a.user_id
              JOIN max_row m ON m.max_id = a.id
            """,
            ids,
        )
        out = {}
        for row in cur.fetchall() or []:
            cid, ts, uname = row
            out[int(cid)] = (ts, uname)
        return out

def last_action_of_user(user_id: int) -> str | None:
    ensure_schema()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("SELECT MAX(ts) FROM client_audit WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        return r[0] if (r and r[0]) else None
