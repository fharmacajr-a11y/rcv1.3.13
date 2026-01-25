# -*- coding: utf-8 -*-
"""Filtros de logging para redacao de informacoes sensiveis."""

from __future__ import annotations

import logging
import re
from typing import Any, Mapping

# Padrao para detectar informacoes sensiveis em logs
SENSITIVE_PATTERN: re.Pattern[str] = re.compile(
    r"(apikey|authorization|token|password|secret|api_key|access_key|private_key)=([^\s&]+)",
    re.IGNORECASE,
)


class RedactSensitiveData(logging.Filter):
    """
    Filtro de logging que redacta informacoes sensiveis.

    Remove valores de credenciais, tokens, senhas e outros dados sensiveis
    dos logs, substituindo-os por '***' para evitar vazamento de informacoes.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filtra e redacta mensagens de log contendo dados sensiveis.

        Mantem o mesmo comportamento do filtro base, sempre permitindo
        a continuacao do fluxo de logging.
        """
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", record.msg)

        if hasattr(record, "args") and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self._redact_value(arg) for arg in record.args)

        return True

    def _redact_value(self, value: Any) -> Any:
        """Redacta um valor se for string ou dicionario com chaves sensiveis."""
        if isinstance(value, str):
            return SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", value)
        if isinstance(value, dict):
            return self._redact_dict(value)
        return value

    def _redact_dict(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """Redacta valores sensiveis em dicionarios."""
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(key, str) and any(
                sensitive in key.lower()
                for sensitive in [
                    "password",
                    "token",
                    "secret",
                    "key",
                    "apikey",
                    "authorization",
                ]
            ):
                redacted[key] = "***"
            else:
                redacted[key] = self._redact_value(value)
        return redacted


# Alias para compatibilidade com a documentacao
Redact = RedactSensitiveData
