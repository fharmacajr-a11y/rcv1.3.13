# -*- coding: utf-8 -*-
"""Utilitários para formatação e normalização de números de telefone/WhatsApp."""

from __future__ import annotations

from src.core.string_utils import only_digits


def normalize_br_whatsapp(raw: str | None) -> dict:
    """
    Recebe qualquer entrada (com/sem +55, espaços, parênteses, etc.)
    e retorna:
      - e164: "55DDXXXXXXXXX" (sem '+', para usar em wa.me)
      - display: "(DD) 9XXXX-XXXX" ou "(DD) XXXX-XXXX"
      - ddd: "DD"
      - local: número local sem DDD

    Regras:
      - Se vier com '55' no começo, remove.
      - Se local tiver 9 dígitos e começar com '9' => celular.
      - Se local tiver 8 dígitos => fixo.
      - Se sobrar algo fora do padrão, devolve o que der e não quebra.
    """
    digits = only_digits(raw)

    # remove possível '+' inicial já removido pelo only_digits
    # normaliza país
    if digits.startswith("55"):
        digits = digits[2:]

    # tenta extrair DDD (2) + local (8 ou 9+8)
    ddd = ""
    local = ""

    if len(digits) >= 10:
        ddd = digits[:2]
        local = digits[2:]
    else:
        # faltou dígito, trata como tudo local
        local = digits

    # Corrige casos com 11+ dígitos (ex.: 9 + 8)
    # Mantém até 9 para celular, ou 8 para fixo.
    if len(local) >= 9:
        local = local[:9]
    elif len(local) >= 8:
        local = local[:8]

    # Monta display
    display = ""
    if ddd and len(local) in (8, 9):
        if len(local) == 9:
            # celular: 9XXXX-XXXX
            display = f"({ddd}) {local[0]}{local[1:5]}-{local[5:]}"
        else:
            # fixo: XXXX-XXXX
            display = f"({ddd}) {local[:4]}-{local[4:]}"
    elif ddd:
        display = f"({ddd}) {local}"
    else:
        display = local

    # e164 para wa.me -> 55 + ddd + local
    e164 = ""
    if ddd and local:
        e164 = f"55{ddd}{local}"
    elif local:
        # sem DDD, evita quebrar link – não monta e164
        e164 = ""

    return {"e164": e164, "display": display, "ddd": ddd, "local": local}
