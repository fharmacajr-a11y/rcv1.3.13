from __future__ import annotations
import sqlite3, os, time, hashlib, hmac, secrets
from typing import Optional
from datetime import datetime
from config.paths import USERS_DB_PATH

# ---------- Password hashing helpers (PBKDF2-SHA256) ----------
def _pbkdf2_hash(password: str, *, iterations: int = 130000) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"

def _pbkdf2_verify(password: str, stored: str) -> bool:
    try:
        algo, iters_str, salt_hex, dk_hex = stored.split('$', 3)
        assert algo == 'pbkdf2_sha256'
        iterations = int(iters_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except Exception:
        return False
    cand = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(expected, cand)

# ---------- DB init ----------
def ensure_users_db() -> None:
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(USERS_DB_PATH)
    try:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        con.commit()

        # Seed default admin if empty
        cur.execute("SELECT COUNT(*) FROM users")
        (count,) = cur.fetchone()
        if count == 0:
            now = datetime.utcnow().isoformat()
            cur.execute(
                "INSERT INTO users (username, password_hash, is_active, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
                ("admin", _pbkdf2_hash("admin123"), now, now),
            )
            con.commit()
    finally:
        con.close()

# ---------- CRUD helpers ----------
def get_user(username: str) -> Optional[tuple]:
    con = sqlite3.connect(USERS_DB_PATH)
    try:
        cur = con.cursor()
        cur.execute("SELECT id, username, password_hash, is_active FROM users WHERE username = ?", (username,))
        return cur.fetchone()
    finally:
        con.close()

def create_user(username: str, password: str) -> int:
    con = sqlite3.connect(USERS_DB_PATH)
    try:
        cur = con.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO users (username, password_hash, is_active, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
            (username, _pbkdf2_hash(password), now, now),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def authenticate_user(username: str, password: str) -> bool:
    row = get_user(username)
    if not row:
        return False
    _id, _username, pwd_hash, is_active = row
    if not is_active:
        return False
    return _pbkdf2_verify(password, pwd_hash)
