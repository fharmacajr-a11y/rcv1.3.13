# -*- coding: utf-8 -*-
# core/auth/auth.py
from __future__ import annotations

import binascii
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from typing import Any

import logging
from threading import Lock

from infra.supabase_client import get_supabase  # cliente lazy singleton
from src.config.paths import USERS_DB_PATH

log = logging.getLogger(__name__)


def _safe_import_yaml() -> Any | None:
    """
    Tenta importar 'yaml'. Se falhar (ImportError ou outro erro de import),
    retorna None em vez de explodir.

    Esta função existe para permitir testes simularem falha de import
    sem precisar usar importlib.reload() no módulo inteiro.
    """
    try:
        import yaml

        return yaml
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao importar yaml: %s", exc)
        return None


# Import opcional de yaml para leitura de config
yaml = _safe_import_yaml()


def _get_auth_pepper() -> str:
    """
    Obtém o 'pepper' a partir de variável de ambiente AUTH_PEPPER ou, se ausente,
    de um arquivo 'config.yml' na raiz do projeto (chave: AUTH_PEPPER).
    Nunca loga o valor do pepper.

    SEC-005: Validação de YAML para prevenir injeção.
    """
    pep = os.getenv("AUTH_PEPPER", "") or os.getenv("RC_AUTH_PEPPER", "")
    if pep:
        return pep
    # tenta carregar de config.yml (opcional)
    try:
        if yaml is not None:
            for candidate in ("config.yml", "config.yaml"):
                if os.path.isfile(candidate):
                    # SEC-005: Validação de tamanho de arquivo antes de carregar
                    file_size = os.path.getsize(candidate)
                    if file_size > 1024 * 1024:  # 1MB máximo
                        log.warning("SEC-005: Arquivo de config muito grande, ignorando: %s", candidate)
                        continue

                    with open(candidate, "r", encoding="utf-8") as fh:
                        # SEC-005: safe_load já previne execução de código arbitrário
                        data = yaml.safe_load(fh)

                        # SEC-005: Validação de tipo do resultado
                        if not isinstance(data, dict):
                            log.warning("SEC-005: Config YAML não é um dict, ignorando: %s", candidate)
                            continue

                        pep = str(data.get("AUTH_PEPPER") or data.get("auth_pepper") or "") or ""

                        # SEC-005: Validação de formato do pepper
                        if pep and (len(pep) < 16 or len(pep) > 256):
                            log.warning("SEC-005: AUTH_PEPPER com tamanho suspeito, ignorando")
                            pep = ""

                        if pep:
                            return pep
    except Exception as exc:  # noqa: BLE001
        # SEC-005: Erro de parsing YAML ou outro erro
        if yaml is not None and isinstance(exc, yaml.YAMLError):
            log.warning("SEC-005: Erro ao parsear YAML config: %s", type(exc).__name__)
        else:
            # não revelar detalhes para não vazar path/pepper
            log.debug("Falha ao obter AUTH_PEPPER via arquivo: %s", exc)
    return ""


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_login_lock = Lock()
login_attempts: dict[str, tuple[int, float]] = {}  # key_email_lower: (count, last_time)


def _reset_auth_for_tests() -> None:
    """
    Helper interno para testes.
    Limpa o estado global de rate limiting e qualquer cache de autenticação.
    NÃO deve ser usado em código de produção.
    """
    global login_attempts
    with _login_lock:
        login_attempts.clear()


def _set_login_attempts_for_tests(email: str, count: int, timestamp: float) -> None:
    """
    Helper interno para testes.
    Define manualmente o estado de tentativas de login para um email.
    NÃO deve ser usado em código de produção.
    """
    key = email.strip().lower()
    with _login_lock:
        login_attempts[key] = (count, timestamp)


def _get_login_attempts_for_tests(email: str) -> tuple[int, float] | None:
    """
    Helper interno para testes.
    Retorna o estado de tentativas de login para um email ou None.
    NÃO deve ser usado em código de produção.
    """
    key = email.strip().lower()
    with _login_lock:
        return login_attempts.get(key)


def _check_key_limit(key: str, now: float) -> tuple[bool, float]:
    """
    Verifica rate limit para uma chave específica (email ou IP).

    SEC-002: Helper interno para dual-key rate limiting.

    Args:
        key: Chave de rate limiting (email ou IP)
        now: Timestamp atual

    Returns:
        (allowed, remaining_seconds): True se permitido, False se bloqueado
    """
    if key in login_attempts:
        count, last = login_attempts[key]
        elapsed = now - last
        if elapsed > 60:  # Reset após 1 minuto
            del login_attempts[key]
            return True, 0.0
        if count >= 5:
            remaining = max(0.0, 60 - elapsed)
            return False, remaining
    return True, 0.0


def check_rate_limit(email: str, ip_address: str | None = None) -> tuple[bool, float]:
    """
    Verifica se excedeu limite, retorna (allowed, remaining_seconds).

    SEC-002: Rate limiting por email E por IP para prevenir ataques distribuídos.

    Args:
        email: Email do usuário
        ip_address: Endereço IP (opcional, mas recomendado)

    Returns:
        (allowed, remaining_seconds): True se permitido, senão tempo de espera
    """
    now: float = time.time()

    # Verifica rate limit por email
    email_key: str = email.strip().lower()
    email_allowed, email_remaining = _check_key_limit(email_key, now)
    if not email_allowed:
        log.warning("Tentativas excedidas para email %s (aguardar %.1fs)", email_key, email_remaining)
        return False, email_remaining

    # SEC-002: Verifica rate limit por IP (se fornecido)
    if ip_address:
        ip_key = f"ip:{ip_address}"
        ip_allowed, ip_remaining = _check_key_limit(ip_key, now)
        if not ip_allowed:
            log.warning("Tentativas excedidas para IP %s (aguardar %.1fs)", ip_address, ip_remaining)
            return False, ip_remaining

    return True, 0.0


# ------------------ Hash de senha (formato legível futuro) ------------------ #
def pbkdf2_hash(
    password: str,
    *,
    iterations: int = 1_000_000,
    salt: bytes | None = None,
    dklen: int = 32,
) -> str:
    """
    Gera hash PBKDF2-SHA256 no formato:
      pbkdf2_sha256$<iter>$<hex_salt>$<hex_hash>

    Para testes, pode-se reduzir iterações via RC_PBKDF2_ITERS (PERF-001).
    Se iterations for passado explicitamente (diferente do default), ele tem prioridade.
    """
    if not password:
        raise ValueError("password vazio")
    if salt is None:
        salt = os.urandom(16)

    # PERF-001: Permitir override de iterações para testes via env var
    # Somente se iterations for o default (1_000_000), aplicar o override
    if iterations == 1_000_000:
        env_iters = os.getenv("RC_PBKDF2_ITERS")
        if env_iters:
            try:
                iterations = int(env_iters)
            except ValueError:
                pass  # Usar default se inválido

    pepper: str = _get_auth_pepper()
    dk: bytes = pbkdf2_hmac("sha256", (password + pepper).encode("utf-8"), salt, iterations, dklen)
    return f"pbkdf2_sha256${iterations}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


def _validate_username(username: str) -> str | None:
    """
    Valida formato de username para prevenir SQL injection.

    SEC-003: Regex whitelist para usernames seguros.
    Permite apenas caracteres alfanuméricos, ponto, underscore, arroba e hífen.

    Args:
        username: Nome de usuário a validar

    Returns:
        None se válido, mensagem de erro caso contrário
    """
    if not username or not username.strip():
        return "Username não pode ser vazio."

    username = username.strip()

    if len(username) > 255:
        return "Username muito longo (máximo 255 caracteres)."

    # SEC-003: Whitelist de caracteres permitidos
    if not re.match(r"^[a-zA-Z0-9._@-]+$", username):
        return "Username contém caracteres inválidos. Use apenas letras, números, ponto, underscore, arroba ou hífen."

    return None


# ------------------------- Banco local de usuários ------------------------- #
def ensure_users_db() -> None:
    """Garante a existência da tabela 'users' no SQLite local (ou /tmp em cloud)."""
    # O SQLite cria o arquivo do DB, mas NÃO cria diretórios. Garanta a pasta-mãe.
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(USERS_DB_PATH))
    try:
        cur: sqlite3.Cursor = con.cursor()
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
    finally:
        con.close()


def create_user(username: str, password: str | None = None) -> int:
    """
    Cria usuário local (SQLite). Se já existir, atualiza a senha se fornecida e retorna o ID.

    SEC-003: Valida username antes de qualquer query SQL.
    """
    # SEC-003: Validação de username
    validation_error = _validate_username(username)
    if validation_error:
        raise ValueError(validation_error)

    ensure_users_db()
    now: str = datetime.now(timezone.utc).isoformat()
    pwd_hash: str | None = pbkdf2_hash(password) if password else None

    con = sqlite3.connect(str(USERS_DB_PATH))
    try:
        cur: sqlite3.Cursor = con.cursor()
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        row: tuple[Any, ...] | None = cur.fetchone()
        if row:
            uid: int = int(row[0])
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
    finally:
        con.close()


# ------------------------- Validação de credenciais ------------------------- #
def validate_credentials(email: str, password: str) -> str | None:
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
def authenticate_user(email: str, password: str, ip_address: str | None = None) -> tuple[bool, str]:
    """
    Autentica via Supabase Auth (email/senha).
    Retorna (ok, msg). ok=True somente se houver user+session válidos.
    msg contém e-mail do usuário quando ok=True; caso contrário, mensagem de erro.

    SEC-002: Suporta rate limiting por IP.

    Args:
        email: Email do usuário
        password: Senha do usuário
        ip_address: Endereço IP (opcional, para rate limiting)
    """
    key: str = email.strip().lower()

    with _login_lock:
        allowed: bool
        remaining: float
        allowed, remaining = check_rate_limit(key, ip_address)
        if not allowed:
            return False, f"Muitas tentativas recentes. Aguarde {int(remaining)}s."

    err: str | None = validate_credentials(email, password)
    if err:
        with _login_lock:
            now: float = time.time()
            count: int
            _: float
            count, _ = login_attempts.get(key, (0, 0.0))
            login_attempts[key] = (count + 1, now)
            # SEC-002: Registra tentativa por IP também
            if ip_address:
                ip_key = f"ip:{ip_address}"
                ip_count, _ = login_attempts.get(ip_key, (0, 0.0))
                login_attempts[ip_key] = (ip_count + 1, now)
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
                # SEC-002: Limpa tentativas de IP também
                if ip_address:
                    ip_key = f"ip:{ip_address}"
                    if ip_key in login_attempts:
                        del login_attempts[ip_key]
            return True, res.user.email or email

        raise Exception("Credenciais inválidas.")  # Força falha
    except Exception as e:
        msg: str = str(e)
        with _login_lock:
            now: float = time.time()
            count: int
            _: float
            count, _ = login_attempts.get(key, (0, 0.0))
            login_attempts[key] = (count + 1, now)
            # SEC-002: Registra tentativa por IP também
            if ip_address:
                ip_key = f"ip:{ip_address}"
                ip_count, _ = login_attempts.get(ip_key, (0, 0.0))
                login_attempts[ip_key] = (ip_count + 1, now)

        # OFFLINE-SUPABASE-UX-001 (Parte C): Mensagens mais amigáveis para erros de rede
        msg_lower = msg.lower()
        if "getaddrinfo" in msg_lower or "nodename" in msg_lower or "temporary failure" in msg_lower:
            return False, "Sem conexão com a internet. Verifique sua rede e tente novamente."
        if "timeout" in msg_lower or "timed out" in msg_lower:
            return False, "Tempo de conexão esgotado. Verifique sua internet e tente novamente."
        if "connection" in msg_lower and ("refused" in msg_lower or "reset" in msg_lower):
            return False, "Não foi possível conectar ao servidor. Tente novamente mais tarde."

        # Mensagens genéricas amigáveis
        if "invalid" in msg_lower or "credentials" in msg_lower:
            return False, "E-mail ou senha incorretos."

        return False, f"Falha ao conectar: {msg}"
