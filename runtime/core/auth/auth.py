# core/auth/auth.py
from __future__ import annotations

import os
import sqlite3
from hashlib import pbkdf2_hmac
from datetime import datetime
from typing import Tuple, Optional

from config.paths import USERS_DB_PATH
from infra.supabase_client import supabase  # create_client conforme doc.


# ------------------ Hash de senha (formato legível futuro) ------------------ #
def pbkdf2_hash(
    password: str,
    *,
    iterations: int = 600_000,
    salt: Optional[bytes] = None,
    dklen: int = 32,
) -> str:
    """
    Gera hash PBKDF2-SHA256 no formato:
      pbkdf2_sha256$<iter>$<hex_salt>$<hex_hash>
    """
    if not password:
        raise ValueError("password vazio")
    if salt is None:
        salt = os.urandom(16)
    dk = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen)
    return "pbkdf2_sha256${iterations}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


# ------------------------- Banco local de usuários ------------------------- #
def ensure_users_db() -> None:
    """Garante a existência da tabela 'users' no SQLite local (ou /tmp em cloud)."""
    # O SQLite cria o arquivo do DB, mas NÃO cria diretórios. Garanta a pasta-mãe.
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(USERS_DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        con.commit()


def create_user(username: str, password: Optional[str] = None) -> int:
    """Cria usuário local (SQLite). Se já existir, atualiza a senha se fornecida e retorna o ID."""
    if not (username or "").strip():
        raise ValueError("username obrigatório")

    ensure_users_db()
    now = datetime.utcnow().isoformat()
    pwd_hash = pbkdf2_hash(password) if password else None

    with sqlite3.connect(str(USERS_DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row:
            uid = int(row[0])
            if pwd_hash:
                cur.execute(
                    "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
                    (pwd_hash, now, uid),
                )
            else:
                cur.execute(
                    "UPDATE users SET updated_at=? WHERE id=?",
                    (now, uid),
                )
            con.commit()
            return uid

        cur.execute(
            "INSERT INTO users (username, password_hash, is_active, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
            (username, pwd_hash, now, now),
        )
        con.commit()
        return int(cur.lastrowid)


# ------------------------- Autenticação (Supabase) ------------------------- #
def authenticate_user(email: str, password: str) -> Tuple[bool, str]:
    """Autentica via Supabase Auth (email/senha). Retorna (ok, mensagem_erro)."""
    try:
        # conforme documentação oficial do client Python
        supabase.auth.sign_in_with_password({"email": email, "password": password})
        return True, ""
    except Exception as e:
        return False, f"Falha de autenticação: {e}"
