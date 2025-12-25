# -*- coding: utf-8 -*-
"""
SEC-006: Utilitários para sanitização de logs e prevenção de vazamento de dados sensíveis.

Este módulo fornece funções para mascarar informações sensíveis em logs,
prevenindo a exposição de senhas, tokens, CPFs, etc.
"""

from __future__ import annotations

import re
from typing import Any


def sanitize_for_log(value: Any, mask_char: str = "*") -> str:
    """
    Sanitiza um valor para log, mascarando informações sensíveis.

    SEC-006: Previne vazamento de dados sensíveis em logs.

    Args:
        value: Valor a ser sanitizado
        mask_char: Caractere usado para mascaramento

    Returns:
        String segura para logging
    """
    if value is None:
        return "None"

    text = str(value)

    # Mascara padrões sensíveis comuns
    text = _mask_passwords(text, mask_char)
    text = _mask_tokens(text, mask_char)
    text = _mask_cpf_cnpj(text, mask_char)
    text = _mask_credit_cards(text, mask_char)
    text = _mask_email_passwords(text, mask_char)

    return text


def _mask_passwords(text: str, mask_char: str) -> str:
    """Mascara campos que parecem senhas."""
    patterns = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', "password"),
        (r'senha["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', "senha"),
        (r'pwd["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', "pwd"),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', "secret"),
    ]

    for pattern, field_name in patterns:
        text = re.sub(pattern, f"{field_name}={mask_char * 8}", text, flags=re.IGNORECASE)

    return text


def _mask_tokens(text: str, mask_char: str) -> str:
    """Mascara tokens e chaves de API."""
    patterns = [
        (r"Bearer\s+([A-Za-z0-9_\-\.]+)", "Bearer"),
        (r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]+)', "token"),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]+)', "api_key"),
        (r'RC_CLIENT_SECRET_KEY["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-=]+)', "RC_CLIENT_SECRET_KEY"),
    ]

    for pattern, field_name in patterns:

        def replacer(match):
            token = match.group(1)
            # Mostra apenas primeiros 4 e últimos 4 caracteres
            if len(token) > 12:
                masked = token[:4] + mask_char * 8 + token[-4:]
            else:
                masked = mask_char * 8
            return f"{field_name}={masked}"

        text = re.sub(pattern, replacer, text, flags=re.IGNORECASE)

    return text


def _mask_cpf_cnpj(text: str, mask_char: str) -> str:
    """Mascara CPF e CNPJ."""
    # CPF: 123.456.789-01 ou 12345678901
    text = re.sub(
        r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", f"{mask_char * 3}.{mask_char * 3}.{mask_char * 3}-{mask_char * 2}", text
    )

    # CNPJ: 12.345.678/0001-90 ou 12345678000190
    text = re.sub(
        r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b",
        f"{mask_char * 2}.{mask_char * 3}.{mask_char * 3}/{mask_char * 4}-{mask_char * 2}",
        text,
    )

    return text


def _mask_credit_cards(text: str, mask_char: str) -> str:
    """Mascara números de cartão de crédito."""
    # Padrão: 4 grupos de 4 dígitos
    text = re.sub(
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        f"{mask_char * 4}-{mask_char * 4}-{mask_char * 4}-{mask_char * 4}",
        text,
    )

    return text


def _mask_email_passwords(text: str, mask_char: str) -> str:
    """Mascara senhas em contextos de email."""
    patterns = [
        r"(password|senha|pwd)\s*=\s*([^\s&]+)",
        r'"(password|senha|pwd)"\s*:\s*"([^"]+)"',
    ]

    for pattern in patterns:
        text = re.sub(pattern, lambda m: f"{m.group(1)}={mask_char * 8}", text, flags=re.IGNORECASE)

    return text


def sanitize_dict_for_log(data: dict[str, Any], sensitive_keys: set[str] | None = None) -> dict[str, Any]:
    """
    Sanitiza um dicionário para log, mascarando chaves sensíveis.

    SEC-006: Versão específica para dicionários.

    Args:
        data: Dicionário a sanitizar
        sensitive_keys: Conjunto de chaves sensíveis (além das padrão)

    Returns:
        Dicionário com valores sensíveis mascarados
    """
    default_sensitive = {
        "password",
        "senha",
        "pwd",
        "secret",
        "token",
        "api_key",
        "access_token",
        "refresh_token",
        "authorization",
        "bearer",
        "cpf",
        "cnpj",
        "credit_card",
        "card_number",
    }

    if sensitive_keys:
        default_sensitive.update(sensitive_keys)

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Verifica se a chave é sensível
        if any(sens in key_lower for sens in default_sensitive):
            if isinstance(value, str) and value:
                # Mascara mantendo primeiros e últimos caracteres
                if len(value) > 8:
                    result[key] = value[:2] + "***" + value[-2:]
                else:
                    result[key] = "***"
            else:
                result[key] = "***"
        elif isinstance(value, dict):
            # Recursivo para dicts aninhados
            result[key] = sanitize_dict_for_log(value, sensitive_keys)
        else:
            result[key] = value

    return result


__all__ = [
    "sanitize_for_log",
    "sanitize_dict_for_log",
]
