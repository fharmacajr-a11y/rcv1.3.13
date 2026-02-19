# -*- coding: utf-8 -*-
"""
Helpers e utilitários da Main Window.

Funções auxiliares que podem ser usadas independentemente da classe App.
"""

import logging
import os
import sys
from typing import Callable

log = logging.getLogger(__name__)


def resource_path(relative_path: str) -> str:
    """
    Resolve caminho de recurso (arquivo bundled pelo PyInstaller).

    Tenta usar a versão oficial de src.utils.resource_path primeiro,
    com fallback para implementação local.

    Args:
        relative_path: Caminho relativo ao recurso

    Returns:
        Caminho absoluto ao recurso
    """
    try:
        from src.utils.resource_path import resource_path as _rp

        return _rp(relative_path)
    except Exception:
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base_path, relative_path)


def sha256_file(path: str) -> str:
    """
    Calcula SHA256 de um arquivo.

    Tenta usar a versão oficial de src.utils.hash_utils primeiro,
    com fallback para implementação local.

    Args:
        path: Caminho ao arquivo

    Returns:
        Hash SHA256 em hexadecimal

    Raises:
        FileNotFoundError: Se o arquivo não existir
    """
    try:
        from src.utils.hash_utils import sha256_file as _sha

        return _sha(path)
    except Exception:
        import hashlib

        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


def create_verbose_logger(fn: Callable) -> Callable:
    """
    Cria um decorator para logging verbose de chamadas de métodos.

    Usado apenas quando RC_VERBOSE=1 está definido.

    Args:
        fn: Função a ser decorada

    Returns:
        Função decorada com logging
    """
    import functools

    log_verb = logging.getLogger("ui.actions")
    is_verbose = (os.getenv("RC_VERBOSE") or "").strip().lower() in {"1", "true", "yes", "on"}

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if is_verbose:
            log_verb.info("CALL %s", fn.__name__)
        try:
            return fn(self, *args, **kwargs)
        except Exception:
            log_verb.exception("ERROR in %s", fn.__name__)
            raise

    return wrapper if is_verbose else fn
