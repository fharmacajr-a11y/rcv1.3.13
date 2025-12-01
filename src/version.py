# -*- coding: utf-8 -*-
"""Gerenciamento de versão do RC-Gestor."""

import os

# Fonte única de verdade da versão do aplicativo.
__version__ = "v1.3.28"
APP_VERSION = __version__


def get_version() -> str:
    """
    Retorna a versão do aplicativo.

    Pode ser sobrescrita via variável de ambiente RC_APP_VERSION.

    Returns:
        str: Versão do aplicativo no formato "v1.3.28"
    """
    try:
        return os.getenv("RC_APP_VERSION", __version__)
    except Exception:
        return __version__
