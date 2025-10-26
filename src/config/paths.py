# config/paths.py
"""
Caminhos centrais do app RC.

- Em modo cloud-only (RC_NO_LOCAL_FS=1), **nada** é criado na pasta do app.
  Os paths são redirecionados para uma área temporária do sistema (apenas se
  algum módulo insistir em fazer .parent.mkdir() ou abrir SQLite).
- Em modo local (RC_NO_LOCAL_FS != 1), as pastas db/ e clientes_docs/
  são criadas (se necessário) dentro do diretório base do app (ou RC_APP_DATA).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from src.config.environment import cloud_only_default

# --- Diretório base do app ---
# config/paths.py fica em <BASE>/config/paths.py → BASE é o pai de config.
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Permite sobrescrever a raiz de dados local (modo não-cloud) via ambiente
APP_DATA: Path = Path(os.getenv("RC_APP_DATA") or BASE_DIR)

# Flag de operação somente nuvem
CLOUD_ONLY: bool = cloud_only_default()

# --- Definições de diretórios/arquivos ---
if CLOUD_ONLY:
    # Em cloud-only, nunca use a pasta do app:
    # Redireciona para uma base "inofensiva" no diretório temporário.
    TMP_BASE = Path(tempfile.gettempdir()) / "rc_void"

    DB_DIR: Path = TMP_BASE / "db"
    DB_PATH: Path = (
        DB_DIR / "disabled.db"
    )  # não deve ser usado no cloud, mas mantemos o path

    USERS_DB_PATH: Path = TMP_BASE / "users" / "disabled_users.db"
    DOCS_DIR: Path = TMP_BASE / "docs"

    # Observação: não criamos diretórios aqui. Se outro módulo chamar
    # .parent.mkdir(...), a criação acontecerá apenas dentro do /tmp,
    # não na pasta do aplicativo.
else:
    # Operação local: mantém comportamento antigo com criação de pastas.
    DB_DIR: Path = APP_DATA / "db"
    DB_DIR.mkdir(parents=True, exist_ok=True)

    DB_PATH: Path = DB_DIR / "clientes.db"
    USERS_DB_PATH: Path = DB_DIR / "users.db"

    DOCS_DIR: Path = APP_DATA / "clientes_docs"
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Exposição explícita dos símbolos principais
__all__ = [
    "BASE_DIR",
    "APP_DATA",
    "CLOUD_ONLY",
    "DB_DIR",
    "DB_PATH",
    "USERS_DB_PATH",
    "DOCS_DIR",
]
