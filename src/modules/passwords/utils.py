# -*- coding: utf-8 -*-
"""Utilitários do módulo passwords — wrapper de compatibilidade.

Delega format_cnpj para a implementação canônica em src.utils.formatters.
"""

from __future__ import annotations

from src.utils.formatters import format_cnpj  # noqa: F401

__all__ = ["format_cnpj"]
