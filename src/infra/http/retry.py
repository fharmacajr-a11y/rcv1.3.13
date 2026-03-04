"""Módulo legado — retry agora centralizado em ``src.infra.retry_policy``.

Mantém re-export de ``retry_call`` para compatibilidade com imports existentes.
"""

from __future__ import annotations

from src.infra.retry_policy import retry_call  # noqa: F401 – re-export

__all__ = ["retry_call"]
