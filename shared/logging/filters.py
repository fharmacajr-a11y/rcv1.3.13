# -*- coding: utf-8 -*-
"""Filtros de logging para redação de informações sensíveis."""
from __future__ import annotations

import logging
import re
from typing import Any

# Padrão para detectar informações sensíveis em logs
SENSITIVE_PATTERN = re.compile(
    r"(apikey|authorization|token|password|secret|api_key|access_key|private_key)=([^\s&]+)",
    re.IGNORECASE
)


class RedactSensitiveData(logging.Filter):
    """
    Filtro de logging que redacta informações sensíveis.
    
    Remove valores de credenciais, tokens, senhas e outros dados sensíveis
    dos logs, substituindo-os por '***' para evitar vazamento de informações.
    
    Baseado em práticas recomendadas pela OWASP Secrets Management Cheat Sheet.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filtra e redacta mensagens de log contendo dados sensíveis.
        
        Args:
            record: Registro de log a ser processado
            
        Returns:
            True para permitir que o log continue (sempre retorna True)
        """
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_PATTERN.sub(
                lambda m: f"{m.group(1)}=***",
                record.msg
            )
        
        # Também redacta argumentos do log se existirem
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self._redact_value(arg) for arg in record.args
                )
        
        return True
    
    def _redact_value(self, value: Any) -> Any:
        """Redacta um valor se for string sensível."""
        if isinstance(value, str):
            return SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", value)
        elif isinstance(value, dict):
            return self._redact_dict(value)
        return value
    
    def _redact_dict(self, data: dict) -> dict:
        """Redacta valores sensíveis em dicionários."""
        redacted = {}
        for key, value in data.items():
            if isinstance(key, str) and any(
                sensitive in key.lower() 
                for sensitive in ['password', 'token', 'secret', 'key', 'apikey', 'authorization']
            ):
                redacted[key] = '***'
            else:
                redacted[key] = self._redact_value(value)
        return redacted


# Alias para compatibilidade com a documentação
Redact = RedactSensitiveData

