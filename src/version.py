# -*- coding: utf-8 -*-
"""
Gerenciamento de versão do RC-Gestor.
"""

import os

__version__ = "v1.1.0"


def get_version() -> str:
    """
    Retorna a versão do aplicativo.

    Pode ser sobrescrita via variável de ambiente RC_APP_VERSION.

    Returns:
        str: Versão do aplicativo no formato "v1.1.0"
    """
    try:
        return os.getenv("RC_APP_VERSION", __version__)
    except Exception:
        return __version__
