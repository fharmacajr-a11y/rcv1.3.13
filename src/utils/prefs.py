# -*- coding: utf-8 -*-
"""Utilitários para persistência de preferências do usuário."""

import json
import logging
import os
from typing import Any, Dict

try:
    from filelock import FileLock  # type: ignore[import-untyped]

    HAS_FILELOCK = True
except ImportError:
    FileLock = Any  # type: ignore[misc,assignment]
    HAS_FILELOCK = False

log = logging.getLogger(__name__)

APP_FOLDER_NAME = "RegularizeConsultoria"
PREFS_FILENAME = "columns_visibility.json"
BROWSER_STATE_FILENAME = "browser_state.json"
BROWSER_STATUS_FILENAME = "browser_status.json"


def _get_base_dir() -> str:
    """Retorna diretório base para armazenar preferências."""
    # Windows
    appdata = os.getenv("APPDATA")
    if appdata and os.path.isdir(appdata):
        path = os.path.join(appdata, APP_FOLDER_NAME)
        os.makedirs(path, exist_ok=True)
        return path
    # Unix-like
    home = os.path.expanduser("~")
    path = os.path.join(home, f".{APP_FOLDER_NAME.lower()}")
    os.makedirs(path, exist_ok=True)
    return path


def _prefs_path() -> str:
    """Retorna caminho completo do arquivo de preferências."""
    return os.path.join(_get_base_dir(), PREFS_FILENAME)


def load_columns_visibility(user_key: str) -> Dict[str, bool]:
    """
    Lê visibilidade das colunas para o user_key (ex.: email).
    Retorna {} se não existir.
    """
    path = _prefs_path()
    if not os.path.exists(path):
        return {}

    lock_path = path + ".lock" if HAS_FILELOCK else None
    lock = FileLock(lock_path, timeout=5) if HAS_FILELOCK and lock_path else None  # type: ignore[misc]

    try:
        if lock:
            with lock:
                return _load_prefs_unlocked(path, user_key)
        else:
            return _load_prefs_unlocked(path, user_key)
    except Exception as e:
        log.exception("Erro ao ler preferências para %s: %s", user_key, e)
        return {}


def _load_prefs_unlocked(path: str, user_key: str) -> Dict[str, bool]:
    """Lê preferências sem lock (internal)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(user_key, {})
    except Exception:
        return {}


def save_columns_visibility(user_key: str, mapping: Dict[str, bool]) -> None:
    """
    Salva visibilidade das colunas para o user_key (ex.: email).
    Preserva outras chaves (outros usuários).
    """
    path = _prefs_path()
    lock_path = path + ".lock" if HAS_FILELOCK else None
    lock = FileLock(lock_path, timeout=5) if HAS_FILELOCK and lock_path else None  # type: ignore[misc]

    try:
        if lock:
            with lock:
                _save_prefs_unlocked(path, user_key, mapping)
        else:
            _save_prefs_unlocked(path, user_key, mapping)
    except Exception as e:
        log.exception("Erro ao salvar preferências para %s: %s", user_key, e)


def _save_prefs_unlocked(path: str, user_key: str, mapping: Dict[str, bool]) -> None:
    """Salva preferências sem lock (internal)."""
    db: Dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f) or {}
        except Exception:
            db = {}
    db[user_key] = mapping
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# --- Browser state helpers ---


def _browser_state_path() -> str:
    base = _get_base_dir()
    return os.path.join(base, BROWSER_STATE_FILENAME)


def _browser_status_path() -> str:
    base = _get_base_dir()
    return os.path.join(base, BROWSER_STATUS_FILENAME)


def load_last_prefix(key: str) -> str:
    """Retorna o último prefixo salvo para a chave informada ou string vazia."""
    path = _browser_state_path()
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        value = data.get(key, "")
        return str(value or "")
    except Exception:
        return ""


def save_last_prefix(key: str, prefix: str) -> None:
    """Salva o último prefixo visitado para a chave informada."""
    path = _browser_state_path()
    db: Dict[str, str] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f) or {}
        except Exception:
            db = {}
    db[key] = prefix
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def load_browser_status_map(key: str) -> Dict[str, str]:
    """Carrega o mapa de status do browser associado à chave fornecida."""
    path = _browser_status_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        raw = data.get(key, {})
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    except Exception:
        pass
    return {}


def save_browser_status_map(key: str, mapping: Dict[str, str]) -> None:
    """Persiste o mapa de status do browser para a chave informada."""
    path = _browser_status_path()
    db: Dict[str, Dict[str, str]] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f) or {}
        except Exception:
            db = {}
    db[key] = mapping
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
