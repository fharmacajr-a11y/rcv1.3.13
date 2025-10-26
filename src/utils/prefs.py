# -*- coding: utf-8 -*-
"""Utilitários para persistência de preferências do usuário."""

import json
import os
from typing import Any, Dict

APP_FOLDER_NAME = "RegularizeConsultoria"
PREFS_FILENAME = "columns_visibility.json"


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
