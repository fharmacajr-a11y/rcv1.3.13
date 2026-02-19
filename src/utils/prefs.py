# -*- coding: utf-8 -*-
"""Utilitários para persistência de preferências do usuário."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, cast

try:
    from filelock import FileLock  # type: ignore[import-untyped]

    HAS_FILELOCK: bool = True
except ImportError:
    FileLock = Any  # type: ignore[misc,assignment]
    HAS_FILELOCK: bool = False

log = logging.getLogger(__name__)

APP_FOLDER_NAME: str = "RegularizeConsultoria"
PREFS_FILENAME: str = "columns_visibility.json"
BROWSER_STATE_FILENAME: str = "browser_state.json"
BROWSER_STATUS_FILENAME: str = "browser_status.json"
LOGIN_PREFS_FILENAME: str = "login_prefs.json"
AUTH_SESSION_FILENAME: str = "auth_session.json"


def _get_base_dir() -> str:
    """Retorna diretório base para armazenar preferências."""
    # Windows
    appdata: Optional[str] = os.getenv("APPDATA")
    if appdata and os.path.isdir(appdata):
        path: str = os.path.join(appdata, APP_FOLDER_NAME)
        os.makedirs(path, exist_ok=True)
        return path
    # Unix-like
    home: str = os.path.expanduser("~")
    path: str = os.path.join(home, f".{APP_FOLDER_NAME.lower()}")
    os.makedirs(path, exist_ok=True)
    return path


def _prefs_path() -> str:
    """Retorna caminho completo do arquivo de preferências."""
    return os.path.join(_get_base_dir(), PREFS_FILENAME)


def _login_prefs_path() -> str:
    base: str = _get_base_dir()
    return os.path.join(base, LOGIN_PREFS_FILENAME)


def _auth_session_path() -> str:
    base: str = _get_base_dir()
    return os.path.join(base, AUTH_SESSION_FILENAME)


# =============================================================================
# KEYRING HELPERS - P1-001: Armazenamento seguro de tokens Supabase
# =============================================================================
# Implementa armazenamento via keyring (DPAPI no Windows) com fallback para arquivo.
# Durante testes (pytest), keyring é desabilitado automaticamente.

KEYRING_SERVICE_NAME: str = "RC-Gestor-Clientes"
KEYRING_USERNAME: str = "supabase_auth_session"


def _keyring_is_available() -> bool:
    """
    Verifica se keyring está disponível e pode ser usado.

    Retorna False automaticamente em ambientes de teste (pytest) para não
    depender do keyring real do SO durante testes automatizados.
    """
    # Detectar ambiente de teste
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("RC_TESTING") == "1":
        return False

    try:
        import keyring  # Lazy import

        # Tenta obter o backend para validar disponibilidade
        backend = keyring.get_keyring()
        if backend is None:
            return False
        # Verifica se não é o backend "fail" (fallback quando nenhum backend real existe)
        backend_name = type(backend).__name__
        if "fail" in backend_name.lower() or "null" in backend_name.lower():
            return False
        return True
    except Exception as exc:
        log.debug("Keyring não disponível: %s", exc)
        return False


def _keyring_get_session_json() -> str | None:
    """
    Obtém sessão JSON do keyring.
    Retorna None se não existir ou houver erro.
    """
    if not _keyring_is_available():
        return None

    try:
        import keyring

        value = keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME)
        return value if value else None
    except Exception as exc:
        log.debug("Erro ao ler sessão do keyring: %s", exc)
        return None


def _keyring_set_session_json(payload: str) -> bool:
    """
    Salva sessão JSON no keyring.
    Retorna True se sucesso, False caso contrário.
    """
    if not _keyring_is_available():
        return False

    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME, payload)
        return True
    except Exception as exc:
        log.warning("Erro ao salvar sessão no keyring: %s", exc)
        return False


def _keyring_clear_session() -> None:
    """Remove sessão do keyring (best-effort)."""
    if not _keyring_is_available():
        return

    try:
        import keyring

        keyring.delete_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME)
    except Exception as exc:
        log.debug("Erro ao limpar sessão do keyring: %s", exc)


def load_columns_visibility(user_key: str) -> dict[str, bool]:
    """
    Lê visibilidade das colunas para o user_key (ex.: email).
    Retorna {} se não existir.
    """
    path: str = _prefs_path()
    if not os.path.exists(path):
        return {}

    lock_path: Optional[str] = path + ".lock" if HAS_FILELOCK else None
    lock: Optional[Any] = FileLock(lock_path, timeout=5) if HAS_FILELOCK and lock_path else None  # type: ignore[misc]

    try:
        if lock:
            with lock:
                return _load_prefs_unlocked(path, user_key)
        else:
            return _load_prefs_unlocked(path, user_key)
    except Exception as e:
        log.exception("Erro ao ler preferências para %s: %s", user_key, e)
        return {}


def _load_prefs_unlocked(path: str, user_key: str) -> dict[str, bool]:
    """Lê preferências sem lock (internal)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
        return cast(dict[str, bool], data.get(user_key, {}))
    except Exception:
        return {}


def save_columns_visibility(user_key: str, mapping: dict[str, bool]) -> None:
    """
    Salva visibilidade das colunas para o user_key (ex.: email).
    Preserva outras chaves (outros usuários).
    """
    path: str = _prefs_path()
    lock_path: Optional[str] = path + ".lock" if HAS_FILELOCK else None
    lock: Optional[Any] = FileLock(lock_path, timeout=5) if HAS_FILELOCK and lock_path else None  # type: ignore[misc]

    try:
        if lock:
            with lock:
                _save_prefs_unlocked(path, user_key, mapping)
        else:
            _save_prefs_unlocked(path, user_key, mapping)
    except Exception as e:
        log.exception("Erro ao salvar preferências para %s: %s", user_key, e)


def _save_prefs_unlocked(path: str, user_key: str, mapping: dict[str, bool]) -> None:
    """Salva preferências sem lock (internal)."""
    db: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f) or {}
        except Exception:
            db = {}
    db[user_key] = mapping
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def load_login_prefs() -> dict[str, Any]:
    """Carrega preferências do login (e-mail e flag lembrar)."""
    path: str = _login_prefs_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f) or {}
        if not isinstance(data, dict):
            log.warning("login_prefs: estrutura inválida (esperado dict).")
            return {}
        email: str = str(data.get("email", "")).strip()
        remember_email: bool = bool(data.get("remember_email", True))
        return {"email": email, "remember_email": remember_email}
    except Exception as exc:
        log.warning("Erro ao ler preferências de login: %s", exc)
        return {}


def save_login_prefs(email: str, remember_email: bool) -> None:
    """Persiste e-mail do login quando lembrar estiver marcado."""
    path: str = _login_prefs_path()

    if not remember_email:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as exc:
                log.warning("Erro ao limpar preferências de login: %s", exc, exc_info=True)
        return

    data: dict[str, Any] = {"email": email.strip(), "remember_email": True}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lock_path: Optional[str] = path + ".lock" if HAS_FILELOCK else None
        lock: Optional[Any] = FileLock(lock_path, timeout=5) if HAS_FILELOCK and lock_path else None  # type: ignore[misc]
        if lock:
            with lock:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.exception("Erro ao salvar preferências de login: %s", exc)


def load_auth_session() -> dict[str, Any]:
    """
    Carrega sessão persistida (tokens) do Supabase.

    P1-001: Migração para keyring (DPAPI no Windows):
    1. Tenta carregar do keyring (armazenamento seguro)
    2. Se não houver no keyring, tenta carregar do arquivo auth_session.json
    3. Se carregar do arquivo com sucesso, migra para keyring e remove arquivo
    """
    # 1. Tentar carregar do keyring primeiro (armazenamento seguro)
    keyring_json = _keyring_get_session_json()
    if keyring_json:
        try:
            data: Any = json.loads(keyring_json)
            if not isinstance(data, dict):
                log.warning("Sessão no keyring tem formato inválido")
                _keyring_clear_session()
                return {}

            access_token: Any = data.get("access_token") or ""
            refresh_token: Any = data.get("refresh_token") or ""
            created_at: Any = data.get("created_at") or ""
            keep_logged: bool = bool(data.get("keep_logged", False))

            if not access_token or not refresh_token or not created_at:
                log.warning("Sessão no keyring incompleta")
                _keyring_clear_session()
                return {}

            return {
                "access_token": str(access_token),
                "refresh_token": str(refresh_token),
                "created_at": str(created_at),
                "keep_logged": keep_logged,
            }
        except Exception as exc:
            log.warning("Erro ao parsear sessão do keyring: %s", exc)
            _keyring_clear_session()
            return {}

    # 2. Fallback: tentar carregar do arquivo (legado)
    path: str = _auth_session_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f) or {}
        if not isinstance(data, dict):
            return {}

        access_token: Any = data.get("access_token") or ""
        refresh_token: Any = data.get("refresh_token") or ""
        created_at: Any = data.get("created_at") or ""
        keep_logged: bool = bool(data.get("keep_logged", False))

        if not access_token or not refresh_token or not created_at:
            return {}

        session_data = {
            "access_token": str(access_token),
            "refresh_token": str(refresh_token),
            "created_at": str(created_at),
            "keep_logged": keep_logged,
        }

        # 3. Migração automática: se carregou do arquivo, tentar migrar para keyring
        if _keyring_is_available():
            try:
                session_json = json.dumps(session_data, ensure_ascii=False)
                if _keyring_set_session_json(session_json):
                    log.info("Sessão migrada de arquivo para keyring (armazenamento seguro)")
                    # Remover arquivo após migração bem-sucedida
                    try:
                        os.remove(path)
                        log.info("Arquivo auth_session.json removido após migração")
                    except Exception as rm_exc:
                        log.debug("Não foi possível remover arquivo após migração: %s", rm_exc)
            except Exception as mig_exc:
                log.debug("Não foi possível migrar sessão para keyring: %s", mig_exc)

        return session_data

    except Exception as exc:
        log.warning("Erro ao ler sessão persistida: %s", exc, exc_info=True)
        try:
            os.remove(path)
        except Exception as rm_exc:
            log.warning("Falha ao remover sessão inválida: %s", rm_exc, exc_info=True)
        return {}


def save_auth_session(access_token: str, refresh_token: str, keep_logged: bool) -> None:
    """
    Persiste tokens de sessão quando 'continuar conectado' estiver ativo.

    P1-001: Prioriza keyring (DPAPI no Windows), fallback para arquivo se necessário.
    """
    path: str = _auth_session_path()

    # Se não deve manter logado, limpar tudo
    if not keep_logged:
        _keyring_clear_session()
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as exc:
                log.warning("Erro ao limpar sessão persistida: %s", exc, exc_info=True)
        return

    from datetime import datetime, timezone

    created_at: str = datetime.now(timezone.utc).isoformat()
    data: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "created_at": created_at,
        "keep_logged": True,
    }

    # Tentar salvar no keyring (armazenamento seguro)
    session_json = json.dumps(data, ensure_ascii=False)
    if _keyring_set_session_json(session_json):
        log.debug("Sessão salva no keyring (armazenamento seguro)")
        # Se salvou no keyring, garantir que não há arquivo com tokens em texto plano
        if os.path.exists(path):
            try:
                os.remove(path)
                log.debug("Arquivo auth_session.json removido (tokens agora no keyring)")
            except Exception as rm_exc:
                log.debug("Não foi possível remover arquivo legado: %s", rm_exc)
        return

    # Fallback: salvar em arquivo (comportamento legado)
    log.debug("Keyring não disponível, usando fallback para arquivo")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lock_path: Optional[str] = path + ".lock" if HAS_FILELOCK else None
        lock: Optional[Any] = FileLock(lock_path, timeout=5) if HAS_FILELOCK and lock_path else None  # type: ignore[misc]
        if lock:
            with lock:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        log.exception("Erro ao salvar sessão de autenticação", exc_info=True)


def clear_auth_session() -> None:
    """
    Remove sessão persistida (best-effort).

    P1-001: Limpa tanto keyring quanto arquivo legado.
    """
    # Limpar keyring
    _keyring_clear_session()

    # Limpar arquivo legado
    path: str = _auth_session_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:
        log.warning("Erro ao limpar sessão persistida: %s", exc, exc_info=True)


# --- Browser state helpers ---


def _browser_state_path() -> str:
    base: str = _get_base_dir()
    return os.path.join(base, BROWSER_STATE_FILENAME)


def _browser_status_path() -> str:
    base: str = _get_base_dir()
    return os.path.join(base, BROWSER_STATUS_FILENAME)


def load_last_prefix(key: str) -> str:
    """Retorna o último prefixo salvo para a chave informada ou string vazia."""
    path: str = _browser_state_path()
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f) or {}
        value: Any = data.get(key, "")
        return str(value or "")
    except Exception:
        return ""


def save_last_prefix(key: str, prefix: str) -> None:
    """Salva o último prefixo visitado para a chave informada."""
    path: str = _browser_state_path()
    db: dict[str, str] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded_data: Any = json.load(f)
                db = loaded_data or {}
        except Exception:
            db = {}
    db[key] = prefix
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def load_browser_status_map(key: str) -> dict[str, str]:
    """Carrega o mapa de status do browser associado à chave fornecida."""
    path: str = _browser_status_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f) or {}
        raw: Any = data.get(key, {})
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    except Exception as exc:
        log.debug("Erro ao ler browser_status para %s", key, exc_info=exc)
    return {}


def save_browser_status_map(key: str, mapping: dict[str, str]) -> None:
    """Persiste o mapa de status do browser para a chave informada."""
    path: str = _browser_status_path()
    db: dict[str, dict[str, str]] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded_data: Any = json.load(f)
                db = loaded_data or {}
        except Exception:
            db = {}
    db[key] = mapping
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
