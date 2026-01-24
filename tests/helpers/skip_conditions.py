# -*- coding: utf-8 -*-
"""
Skip conditions reutilizáveis para testes.

Este módulo centraliza decorators de skip comuns para evitar duplicação
e facilitar manutenção quando bugs upstream forem corrigidos.
"""

import sys

import pytest

# ============================================================================
# Python 3.13 + Tkinter/ttkbootstrap em Windows
# ============================================================================

SKIP_PY313_TKINTER = pytest.mark.skipif(
    sys.version_info >= (3, 13) and sys.platform == "win32",
    reason=(
        "Tkinter/ttkbootstrap + pytest em Python 3.13 no Windows pode causar "
        "'Windows fatal exception: access violation' (bug do runtime CPython, "
        "ver issues #125179 e #118973)"
    ),
)
# Skip testes que usam Tkinter/ttkbootstrap em Python 3.13+ no Windows.
# Bug conhecido do CPython que causa access violation ao criar widgets
# Tkinter/ttkbootstrap dentro de testes pytest no Windows.
# Referências:
# - https://github.com/python/cpython/issues/125179
# - https://github.com/python/cpython/issues/118973
# Quando corrigir:
# - Remover este decorator quando o bug for corrigido no CPython 3.13.x ou 3.14+
# - Verificar se o bug persiste antes de remover

# ============================================================================
# Platform-specific skips
# ============================================================================

SKIP_NOT_LINUX = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux-only test",
)
# Skip testes que só funcionam em Linux.

SKIP_NOT_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-only test",
)
# Skip testes que só funcionam em Windows.

# ============================================================================
# Versão Python
# ============================================================================

SKIP_PY312_PLUS = pytest.mark.skipif(
    sys.version_info >= (3, 12),
    reason="Test incompatível com Python 3.12+",
)
# Skip testes incompatíveis com Python 3.12+.
