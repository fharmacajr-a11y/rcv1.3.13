# -*- coding: utf-8 -*-
"""Utilitários compartilhados do módulo Senhas."""

from __future__ import annotations


def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ '05788603000113' -> '05.788.603/0001-13'.

    Args:
        cnpj: String contendo CNPJ (com ou sem pontuação)

    Returns:
        CNPJ formatado com pontuação padrão, ou o valor original se não tiver 14 dígitos
    """
    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) != 14:
        return cnpj  # fallback, não quebra
    return f"{digits[0:2]}." f"{digits[2:5]}." f"{digits[5:8]}/" f"{digits[8:12]}-" f"{digits[12:14]}"
