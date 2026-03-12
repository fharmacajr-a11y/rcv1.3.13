# -*- coding: utf-8 -*-
"""Utilitários para persistência de preferências do usuário."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
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


# ---------------------------------------------------------------------------
# Atomic write + resilient load helpers  (PR17)
# ---------------------------------------------------------------------------


def _atomic_write_json(path: str, data: object) -> None:
    """Grava *data* como JSON em *path* de forma atômica.

    Cria tempfile no mesmo diretório, escreve + fsync, depois usa
    ``os.replace`` para substituir o arquivo final.  Se qualquer etapa
    falhar antes do replace, o arquivo original permanece intacto.
    """
    target_dir = os.path.dirname(path) or "."
    os.makedirs(target_dir, exist_ok=True)
    fd = -1
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            fd = -1  # fdopen assume ownership
            json.dump(data, fp, ensure_ascii=False, indent=2)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp_path, path)
        tmp_path = None  # replace succeeded – nothing to clean up
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _resilient_load_json(path: str) -> Any:
    """Carrega JSON de *path*; em caso de corrupção, quarantina o arquivo.

    Se ``json.load`` lançar ``JSONDecodeError``, o arquivo é renomeado para
    ``<path>.corrupt.<timestamp>`` e a função retorna ``None``.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        ts = str(int(time.time()))
        corrupt_path = f"{path}.corrupt.{ts}"
        try:
            os.replace(path, corrupt_path)
        except OSError:
            pass
        log.warning("Arquivo de preferências corrompido; renomeado para quarentena " "e defaults serão usados.")
        return None
    except Exception:
        return None


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

    # Forçar fallback para arquivo criptografado (debug/testes manuais)
    if os.getenv("RC_FORCE_FILE_SESSION") == "1":
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
    data = _resilient_load_json(path)
    if not isinstance(data, dict):
        return {}
    return cast(dict[str, bool], data.get(user_key, {}))


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
    """Salva preferências sem lock (internal) — escrita atômica."""
    db: dict[str, Any] = {}
    if os.path.exists(path):
        loaded = _resilient_load_json(path)
        if isinstance(loaded, dict):
            db = loaded
    db[user_key] = mapping
    _atomic_write_json(path, db)


def load_login_prefs() -> dict[str, Any]:
    """Carrega preferências do login (e-mail e flag lembrar)."""
    path: str = _login_prefs_path()
    if not os.path.exists(path):
        return {}
    data = _resilient_load_json(path)
    if not isinstance(data, dict):
        return {}
    email: str = str(data.get("email", "")).strip()
    remember_email: bool = bool(data.get("remember_email", True))
    return {"email": email, "remember_email": remember_email}


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
                _atomic_write_json(path, data)
        else:
            _atomic_write_json(path, data)
    except Exception as exc:
        log.exception("Erro ao salvar preferências de login: %s", exc)


def _validate_session_dict(data: dict[str, Any]) -> dict[str, Any] | None:
    """Valida campos obrigatórios e retorna dict normalizado, ou *None*."""
    access_token = data.get("access_token") or ""
    refresh_token = data.get("refresh_token") or ""
    created_at = data.get("created_at") or ""
    keep_logged: bool = bool(data.get("keep_logged", False))

    if not access_token or not refresh_token or not created_at:
        return None

    return {
        "access_token": str(access_token),
        "refresh_token": str(refresh_token),
        "created_at": str(created_at),
        "keep_logged": keep_logged,
    }


def load_auth_session() -> dict[str, Any]:
    """
    Carrega sessão persistida (tokens) do Supabase.

    Ordem de tentativa:
    1. Keyring (DPAPI no Windows) — armazenamento mais seguro
    2. Arquivo criptografado ``auth_session.enc`` (fallback DPAPI)
    3. Arquivo legado ``auth_session.json`` (plain JSON) → migra
    """
    from src.utils.session_store import (
        encrypted_file_load,
        migrate_legacy_file,
    )

    base_dir = _get_base_dir()

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

    # 2. Fallback: arquivo criptografado (DPAPI)
    enc_data = encrypted_file_load(base_dir)
    if enc_data:
        session = _validate_session_dict(enc_data)
        if session:
            return session

    # 3. Migração de arquivo legado (plain JSON → encrypted)
    legacy_data = migrate_legacy_file(base_dir)
    if legacy_data:
        session = _validate_session_dict(legacy_data)
        if session:
            return session

    return {}


def save_auth_session(access_token: str, refresh_token: str, keep_logged: bool) -> None:
    """
    Persiste tokens de sessão quando 'continuar conectado' estiver ativo.

    Prioriza keyring (DPAPI no Windows).  Se indisponível, grava em arquivo
    criptografado (``auth_session.enc``) via DPAPI.  Tokens **nunca** são
    salvos em texto plano.
    """
    from src.utils.session_store import (
        _IS_WINDOWS,
        encrypted_file_clear,
        encrypted_file_save,
    )

    base_dir = _get_base_dir()

    # Se não deve manter logado, limpar tudo
    if not keep_logged:
        _keyring_clear_session()
        encrypted_file_clear(base_dir)
        return

    from datetime import datetime, timezone

    created_at: str = datetime.now(timezone.utc).isoformat()
    data: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "created_at": created_at,
        "keep_logged": True,
    }

    # 1. Tentar salvar no keyring (armazenamento seguro)
    session_json = json.dumps(data, ensure_ascii=False)
    if _keyring_set_session_json(session_json):
        log.debug("Sessão salva no keyring, token_present=True")
        # Garantir que não há arquivo legado ou criptografado
        encrypted_file_clear(base_dir)
        return

    # 2. Fallback: arquivo criptografado (DPAPI) — somente Windows
    if _IS_WINDOWS:
        try:
            encrypted_file_save(base_dir, data)
            log.debug("Sessão salva em arquivo DPAPI-encrypted, token_present=True")
            return
        except Exception:
            log.exception("Erro ao salvar sessão em arquivo criptografado")
    else:
        log.warning(
            "Keyring indisponível e DPAPI não suportado neste SO. "
            "Sessão NÃO será persistida (tokens apenas em memória)."
        )


def clear_auth_session() -> None:
    """
    Remove sessão persistida (best-effort).

    Limpa keyring + arquivo criptografado + arquivo legado.
    """
    from src.utils.session_store import encrypted_file_clear

    _keyring_clear_session()
    encrypted_file_clear(_get_base_dir())


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
    data = _resilient_load_json(path)
    if not isinstance(data, dict):
        return ""
    return str(data.get(key, "") or "")


def save_last_prefix(key: str, prefix: str) -> None:
    """Salva o último prefixo visitado para a chave informada."""
    path: str = _browser_state_path()
    db: dict[str, str] = {}
    if os.path.exists(path):
        loaded = _resilient_load_json(path)
        if isinstance(loaded, dict):
            db = loaded
    db[key] = prefix
    _atomic_write_json(path, db)


def load_browser_status_map(key: str) -> dict[str, str]:
    """Carrega o mapa de status do browser associado à chave fornecida."""
    path: str = _browser_status_path()
    if not os.path.exists(path):
        return {}
    data = _resilient_load_json(path)
    if not isinstance(data, dict):
        return {}
    raw: Any = data.get(key, {})
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def save_browser_status_map(key: str, mapping: dict[str, str]) -> None:
    """Persiste o mapa de status do browser para a chave informada."""
    path: str = _browser_status_path()
    db: dict[str, dict[str, str]] = {}
    if os.path.exists(path):
        loaded = _resilient_load_json(path)
        if isinstance(loaded, dict):
            db = loaded
    db[key] = mapping
    _atomic_write_json(path, db)
