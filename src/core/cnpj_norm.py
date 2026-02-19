from __future__ import annotations

from src.core.text_normalization import strip_diacritics as _strip_diacritics


def normalize_cnpj(raw: object) -> str:
    """Normaliza CNPJ (numérico ou alfanumérico) para comparação/índice.

    - Remove máscara, pontuação e diacríticos
    - Mantém apenas caracteres A–Z e 0–9
    - Converte para uppercase
    """
    s = "" if raw is None else str(raw)
    s = _strip_diacritics(s).upper()
    out: list[str] = []
    for ch in s:
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            out.append(ch)
    return "".join(out)


def normalize_cnpj_digits(raw: object) -> str:
    """Normaliza CNPJ retornando apenas dígitos (0–9).

    - Remove máscara, pontuação, letras e diacríticos
    - Mantém apenas caracteres 0–9
    - Usado para validações que requerem apenas números
    """
    s = "" if raw is None else str(raw)
    out: list[str] = []
    for ch in s:
        if "0" <= ch <= "9":
            out.append(ch)
    return "".join(out)


def is_valid_cnpj(cnpj: object) -> bool:
    """Valida CNPJ verificando dígitos verificadores (DV).

    **Implementação canônica** de validação de CNPJ no projeto.
    Todas as outras funções de validação devem delegar para esta.

    Regras:
    - Normaliza usando normalize_cnpj_digits
    - Rejeita se não tiver exatamente 14 dígitos
    - Rejeita CNPJs com todos os dígitos iguais (00000000000000, 11111111111111, etc.)
    - Valida os dois dígitos verificadores conforme algoritmo oficial

    Args:
        cnpj: CNPJ como string, int, ou qualquer objeto convertível para string

    Returns:
        True se CNPJ é válido, False caso contrário

    Examples:
        >>> is_valid_cnpj("11.222.333/0001-65")
        True
        >>> is_valid_cnpj("11222333000165")
        True
        >>> is_valid_cnpj("00000000000000")
        False
        >>> is_valid_cnpj("123")
        False
        >>> is_valid_cnpj(None)
        False
    """
    digits = normalize_cnpj_digits(cnpj)

    # Deve ter exatamente 14 dígitos
    if len(digits) != 14:
        return False

    # Rejeita sequências com todos os dígitos iguais
    if digits == digits[0] * 14:
        return False

    # Calcula dígito verificador
    def _calc_dv(base: str) -> str:
        weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(digit) * weights[i] for i, digit in enumerate(base))
        remainder = total % 11
        dv = 0 if remainder < 2 else 11 - remainder
        return str(dv)

    # Valida primeiro dígito verificador
    dv1 = _calc_dv(digits[:12])
    # Valida segundo dígito verificador
    dv2 = _calc_dv(digits[:12] + dv1)

    return digits[-2:] == dv1 + dv2
