# -*- coding: utf-8 -*-
"""
Stub de compatibilidade - infrastructure/scripts/ → scripts/

DEPRECATED: Este módulo é um stub de compatibilidade.
O módulo infrastructure/scripts/ foi movido para scripts/.
Use 'from scripts import ...' ao invés de 'from infrastructure.scripts import ...'

Este stub mantém compatibilidade temporária com código legado.
"""
from __future__ import annotations

import warnings

# Reexport healthcheck de scripts para manter compatibilidade
try:
    from scripts.healthcheck import *  # noqa: F401, F403
except ImportError:
    pass

warnings.warn(
    "O módulo 'infrastructure.scripts' está deprecated. Use 'scripts' ao invés disso.",
    DeprecationWarning,
    stacklevel=2,
)
