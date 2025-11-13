# -*- coding: utf-8 -*-
# core/auth/auth.py
from __future__ import annotations

import binascii
import os
import re
import sqlite3
import time
from datetime import datetime
from hashlib import pbkdf2_hmac
from typing import Optional, Tuple

try:
    import yaml  # opcional
except Exception:
    yaml = None
import logging
from threading import Lock

from infra.supabase_client import get_supabase  # cliente lazy singleton
from src.config.paths import USERS_DB_PATH

log = logging.getLogger(__name__)


def _get_auth_pepper() -> str:
    """
    Obtém o 'pepper' a partir de variável de ambiente AUTH_PEPPER ou, se ausente,
    de um arquivo 'config.yml' na raiz do projeto (chave: AUTH_PEPPER).
    Nunca loga o valor do pepper.
    """
    pep = os.getenv("AUTH_PEPPER", "") or os.getenv("RC_AUTH_PEPPER", "")
    if pep:
        return pep
    # tenta carregar de config.yml (opcional)
    try:
        if yaml is not None:
            for candidate in ("config.yml", "config.yaml"):
                if os.path.isfile(candidate):
                    with open(candidate, "r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                        pep = str(data.get("AUTH_PEPPER") or data.get("auth_pepper") or "") or ""
                        if pep:
                            return pep
    except Exception:
        # não revelar detalhes para não vazar path/pepper
        pass
    return ""


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_login_lock = Lock()
login_attempts: dict[str, tuple[int, float]] = {}  # key_email_lower: (count, last_time)


def check_rate_limit(email: str) -> Tuple[bool, float]:
    """Verifica se excedeu limite, retorna (allowed, remaining_seconds)."""
    key = email.strip().lower()
    now = time.time()
    if key in login_attempts:
        count, last = login_attempts[key]
        elapsed = now - last
        if elapsed > 60:  # Reset após 1 minuto
            del login_attempts[key]
            return True, 0.0
        if count >= 5:
            remaining = max(0.0, 60 - elapsed)
            log.warning("Tentativas excedidas para %s (aguardar %.1fs)", key, remaining)
            return False, remaining
    return True, 0.0


# ------------------ Hash de senha (formato legível futuro) ------------------ #
def pbkdf2_hash(
    password: str,
    *,
    iterations: int = 1_000_000,
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
    pepper = _get_auth_pepper()
    dk = pbkdf2_hmac("sha256", (password + pepper).encode("utf-8"), salt, iterations, dklen)
    return f"pbkdf2_sha256${iterations}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


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
        return int(cur.lastrowid)  # pyright: ignore[reportArgumentType]


# ------------------------- Validação de credenciais ------------------------- #
def validate_credentials(email: str, password: str) -> Optional[str]:
    """
    Valida formato de e-mail e tamanho de senha.
    Retorna mensagem de erro ou None se válido.
    """
    if not EMAIL_RE.match(email or ""):
        return "Informe um e-mail válido."
    if not password or len(password) < 6:
        return "A senha deve ter ao menos 6 caracteres."
    return None


# ------------------------- Autenticação (Supabase) ------------------------- #
def authenticate_user(email: str, password: str) -> Tuple[bool, str]:
    """
    Autentica via Supabase Auth (email/senha).
    Retorna (ok, msg). ok=True somente se houver user+session válidos.
    msg contém e-mail do usuário quando ok=True; caso contrário, mensagem de erro.
    """
    key = email.strip().lower()

    with _login_lock:
        allowed, remaining = check_rate_limit(key)
        if not allowed:
            return False, f"Muitas tentativas recentes. Aguarde {int(remaining)}s."

    err = validate_credentials(email, password)
    if err:
        with _login_lock:
            now = time.time()
            count, _ = login_attempts.get(key, (0, 0.0))
            login_attempts[key] = (count + 1, now)
        return False, err

    sb = get_supabase()
    try:
        # sign_in_with_password lança exceção se falhar
        res = sb.auth.sign_in_with_password({"email": email, "password": password})

        # Confirma sessão e usuário
        sess = sb.auth.get_session()
        if getattr(res, "user", None) and sess and getattr(sess, "access_token", None):
            with _login_lock:
                if key in login_attempts:
                    del login_attempts[key]
            return True, res.user.email or email

        raise Exception("Credenciais inválidas.")  # Força falha
    except Exception as e:
        msg = str(e)
        with _login_lock:
            now = time.time()
            count, _ = login_attempts.get(key, (0, 0.0))
            login_attempts[key] = (count + 1, now)
        # Mensagens mais amigáveis
        if "invalid" in msg.lower() or "credentials" in msg.lower():
            return False, "E-mail ou senha incorretos."
        return False, f"Falha ao conectar no Supabase: {msg}"
