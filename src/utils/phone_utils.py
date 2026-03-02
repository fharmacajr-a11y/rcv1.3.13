# -*- coding: utf-8 -*-
"""Utilitários para formatação e normalização de números de telefone/WhatsApp.

Funções:
- normalize_br_whatsapp(): Retorna dict com e164, display, ddd, local (para wa.me)
- format_phone_br(): Formata telefone no padrão +55 DD XXXXX-XXXX
- only_phone_digits(): Remove tudo que não é dígito
- is_valid_br_phone(): Valida telefone brasileiro
"""

from __future__ import annotations

import logging
import re

from src.core.string_utils import only_digits

log = logging.getLogger(__name__)


def only_phone_digits(value: str | None) -> str:
    """Remove tudo que não é dígito de um telefone.

    Args:
        value: String com telefone (pode conter +, espaços, pontos, etc.)

    Returns:
        String apenas com dígitos
    """
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def format_phone_br(raw: str | None) -> str:
    """Formata telefone brasileiro no padrão +55 DD XXXXX-XXXX ou +55 DD XXXX-XXXX.

    Args:
        raw: Telefone bruto (qualquer formato)

    Returns:
        Telefone formatado (ex: "+55 11 98765-4321") ou string vazia se inválido

    Examples:
        >>> format_phone_br("11987654321")
        '+55 11 98765-4321'
        >>> format_phone_br("5511987654321")
        '+55 11 98765-4321'
        >>> format_phone_br("(11) 3456-7890")
        '+55 11 3456-7890'
        >>> format_phone_br("1198765")
        ''  # Muito curto, inválido
    """
    if not raw:
        return ""

    digits = only_phone_digits(raw)
    if not digits:
        return ""

    # Remover prefixo 55 se presente (vamos readicionar formatado)
    if digits.startswith("55") and len(digits) > 11:
        digits = digits[2:]

    # Validar comprimento mínimo: DDD (2) + número (8 ou 9) = 10 ou 11 dígitos
    if len(digits) < 10:
        log.debug(f"[phone_utils] Telefone muito curto para formatar: {raw} ({len(digits)} dígitos)")
        return ""

    if len(digits) > 11:
        log.debug(f"[phone_utils] Telefone muito longo para formatar: {raw} ({len(digits)} dígitos)")
        return ""

    # Extrair DDD e número
    ddd = digits[:2]
    numero = digits[2:]

    # Formatar número com hífen
    if len(numero) == 9:
        # Celular: 9XXXX-XXXX
        numero_fmt = f"{numero[:5]}-{numero[5:]}"
    elif len(numero) == 8:
        # Fixo: XXXX-XXXX
        numero_fmt = f"{numero[:4]}-{numero[4:]}"
    else:
        # Fallback: sem hífen
        numero_fmt = numero

    return f"+55 {ddd} {numero_fmt}"


def is_valid_br_phone(raw: str | None) -> bool:
    """Verifica se é um telefone brasileiro válido (DDD + 8 ou 9 dígitos).

    Args:
        raw: Telefone bruto

    Returns:
        True se válido, False caso contrário
    """
    if not raw:
        return False

    digits = only_phone_digits(raw)

    # Remover 55 se presente
    if digits.startswith("55") and len(digits) > 11:
        digits = digits[2:]

    # DDD (2) + número (8 ou 9)
    return len(digits) in (10, 11)


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
        # Valida DDD: deve ter 2 dígitos e não pode começar com '0'
        if len(ddd) != 2 or ddd[0] == "0":
            log.debug("[phone_utils] DDD inválido: %s", ddd)
            return {"e164": "", "display": "", "ddd": "", "local": ""}
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
