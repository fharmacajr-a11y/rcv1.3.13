# -*- coding: utf-8 -*-
"""Utilitários compartilhados do módulo Senhas."""

from __future__ import annotations


def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ '05788603000113' -> '05.788.603/0001-13'.

    Wrapper para compatibilidade. Delega para src.utils.formatters.format_cnpj.

    Args:
        cnpj: String contendo CNPJ (com ou sem pontuação)

    Returns:
        CNPJ formatado com pontuação padrão, ou o valor original se não tiver 14 dígitos
    """
    from src.utils.formatters import format_cnpj as _format_cnpj_canonical

    return _format_cnpj_canonical(cnpj)
