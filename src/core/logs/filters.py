# -*- coding: utf-8 -*-
"""Filtros de logging para redacao de informacoes sensiveis e anti-spam."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Mapping

# Padrao para detectar informacoes sensiveis em logs
SENSITIVE_PATTERN: re.Pattern[str] = re.compile(
    r"(apikey|authorization|token|password|secret|api_key|access_key|private_key)=([^\s&]+)",
    re.IGNORECASE,
)

# Padrão para paths do Windows (C:\Users\...) - mais abrangente
WINDOWS_PATH_PATTERN: re.Pattern[str] = re.compile(
    r"[A-Z]:[\\][^\s,)\"'<>|?*]+",
    re.IGNORECASE,
)

# Padrão para UUIDs (formato: 8-4-4-4-12) - captura em qualquer contexto
UUID_PATTERN: re.Pattern[str] = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# Padrão para emails
EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
)

# Cache para anti-spam (msg_key -> last_timestamp)
_SPAM_CACHE: dict[str, float] = {}
_SPAM_THROTTLE_SECONDS = 60.0  # Mínimo 60s entre logs repetitivos


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
            # Redatar credenciais
            record.msg = SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", record.msg)
            # Redatar paths do Windows
            record.msg = WINDOWS_PATH_PATTERN.sub(self._redact_path, record.msg)
            # Redatar UUIDs (mostrar apenas 8 primeiros chars)
            record.msg = UUID_PATTERN.sub(self._redact_uuid, record.msg)
            # Redatar emails
            record.msg = EMAIL_PATTERN.sub(self._redact_email, record.msg)

        if hasattr(record, "args") and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self._redact_value(arg) for arg in record.args)

        return True

    def _redact_path(self, match: re.Match[str]) -> str:
        """Reduz path do Windows para apenas basename ou relativo."""
        full_path = match.group(0)
        try:
            path = Path(full_path)
            # Se for arquivo comum (rc.ico, .env), mostrar apenas nome
            if path.suffix:
                return f"<path>/{path.name}"
            # Se for diretório, mostrar apenas último componente
            return f"<path>/{path.name}/"
        except Exception:
            return "<path>/..."

    def _redact_uuid(self, match: re.Match[str]) -> str:
        """Reduz UUID para prefixo de 8 chars."""
        uuid_str = match.group(0)
        return f"{uuid_str[:8]}..."

    def _redact_email(self, match: re.Match[str]) -> str:
        """Mascara email (a***@d***.com)."""
        email = match.group(0)
        try:
            user, domain = email.split("@")
            user_masked = user[0] + "***" if len(user) > 1 else "***"
            domain_parts = domain.split(".")
            if len(domain_parts) >= 2:
                domain_masked = domain_parts[0][0] + "***" + "." + ".".join(domain_parts[1:])
            else:
                domain_masked = "***"
            return f"{user_masked}@{domain_masked}"
        except Exception:
            return "***@***.***"

    def _redact_value(self, value: Any) -> Any:
        """Redacta um valor se for string ou dicionario com chaves sensiveis."""
        if isinstance(value, str):
            # Aplicar todas as redações
            value = SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", value)
            value = WINDOWS_PATH_PATTERN.sub(self._redact_path, value)
            value = UUID_PATTERN.sub(self._redact_uuid, value)
            value = EMAIL_PATTERN.sub(self._redact_email, value)
            return value
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


class AntiSpamFilter(logging.Filter):
    """Filtro anti-spam para mensagens repetitivas.

    Throttle: permite log apenas 1x a cada 60s para mensagens com mesmo padrão.
    Útil para: health checks, connectivity confirmed, polling, etc.
    """

    # Padrões de mensagens que devem ter throttle
    SPAM_PATTERNS = [
        r"Health check:",
        r"Internet connectivity confirmed",
        r"Background health check:",
        r"Cliente Supabase reutilizado",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Aplica throttle em mensagens repetitivas."""
        # Permitir sempre WARNING/ERROR/CRITICAL
        if record.levelno >= logging.WARNING:
            return True

        try:
            msg = str(record.getMessage())
        except (TypeError, Exception) as e:
            # Se falhar ao formatar mensagem (ex: placeholders vs args mismatch),
            # usar mensagem raw e limpar args para evitar crash
            msg = str(record.msg)
            record.args = ()
            # Log do problema em dev_mode apenas para debug
            import os

            if os.environ.get("RC_DEBUG_TK_EXCEPTIONS") == "1":
                print(f"[LogFilter] Erro de formatação: {e} | msg={record.msg} | args={record.args}")

        # Verificar se mensagem corresponde a algum padrão de spam
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE):
                # Criar chave única para throttle
                cache_key = f"{record.name}:{pattern}"
                now = time.time()
                last_logged = _SPAM_CACHE.get(cache_key, 0.0)

                # Se passou tempo suficiente, permitir log
                if (now - last_logged) >= _SPAM_THROTTLE_SECONDS:
                    _SPAM_CACHE[cache_key] = now
                    return True

                # Caso contrário, bloquear (spam)
                return False

        # Mensagens não-spam passam normalmente
        return True


class ConsoleImportantFilter(logging.Filter):
    """Filtro para console que permite apenas loggers importantes em INFO.

    Permite sempre WARNING/ERROR/CRITICAL.
    Para INFO, aplica allowlist de loggers importantes.
    DEBUG sempre é bloqueado (use RC_LOG_LEVEL=DEBUG para ver tudo).
    """

    # Loggers importantes que devem aparecer no console em INFO
    IMPORTANT_LOGGERS = {
        "startup",
        "app_gui",
        "app_gui.layout",
        "src.ui.theme_manager",
        "src.ui.splash",
        "src.ui.shutdown",
        "src.modules.main_window.controllers.screen_registry",
        "src.modules.clientes.ui.view",
        "src.core.tk_exception_handler",
        "src.modules.main_window.views.main_window_services",
        "src.infra.supabase.db_client",  # Apenas criação/health checker
        "src.infra.supabase.auth_client",
        "src.infra.repositories.anvisa_requests_repository",
        "src.modules.hub.recent_activity_store",
    }

    # Prefixos de loggers que devem ser bloqueados em INFO
    BLOCKED_PREFIXES = (
        "src.ui.ttk_treeview_",
        "infra.supabase.storage",
        "src.modules.clientes.ui.views.client_files_dialog",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        """Filtra logs para console.

        Returns:
            True se o log deve ser exibido, False caso contrário
        """
        # Permitir sempre WARNING/ERROR/CRITICAL
        if record.levelno >= logging.WARNING:
            return True

        # DEBUG nunca aparece no console (mesmo que level seja DEBUG)
        # Use arquivo de log ou RC_LOG_LEVEL=DEBUG para ver
        if record.levelno < logging.INFO:
            return False

        # Para INFO, aplicar allowlist
        logger_name = record.name

        # Bloquear prefixos específicos
        for prefix in self.BLOCKED_PREFIXES:
            if logger_name.startswith(prefix):
                return False

        # Permitir apenas loggers importantes
        return logger_name in self.IMPORTANT_LOGGERS
