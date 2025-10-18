# -*- coding: utf-8 -*-
"""
Stub de compatibilidade - infrastructure/ → infra/

DEPRECATED: Este módulo é um stub de compatibilidade.
A pasta infrastructure/ será removida no futuro.
Use 'from infra import ...' ao invés de 'from infrastructure import ...'

Este stub mantém compatibilidade temporária com código legado.
"""
from __future__ import annotations

import warnings

# Reexport tudo de infra para manter compatibilidade
from infra import *  # noqa: F401, F403

warnings.warn(
    "O módulo 'infrastructure' está deprecated. Use 'infra' ao invés disso.",
    DeprecationWarning,
    stacklevel=2,
)
