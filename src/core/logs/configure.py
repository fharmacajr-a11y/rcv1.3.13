from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.config.environment import env_str
from src.core.logs.filters import RedactSensitiveData, ConsoleImportantFilter, AntiSpamFilter

_configured = False


class StorageWarningFilter(logging.Filter):
    """Filtro para suprimir warning específico do storage sobre trailing slash."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Bloqueia apenas a warning do trailing slash do storage."""
        if record.levelno == logging.WARNING:
            msg = str(record.getMessage())
            if "Storage endpoint URL should have a trailing slash" in msg:
                return False
        return True


def configure_logging(level: Optional[str] = None) -> None:
    global _configured
    if _configured:
        return

    level_name = (level or env_str("LOG_LEVEL") or env_str("RC_LOG_LEVEL") or "INFO").upper()
    lvl = getattr(logging, level_name, logging.INFO)

    # Capturar warnings do Python (warnings module) e logar
    logging.captureWarnings(True)

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root sempre DEBUG, filtros controlam saída

    # Limpar handlers existentes (evitar duplicação)
    root_logger.handlers.clear()

    # 1. CONSOLE HANDLER (INFO minimalista)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(lvl)  # Respeita RC_LOG_LEVEL para console
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # Filtros do console
    console_handler.addFilter(RedactSensitiveData())
    console_handler.addFilter(AntiSpamFilter())
    console_handler.addFilter(ConsoleImportantFilter())
    console_handler.addFilter(StorageWarningFilter())

    root_logger.addHandler(console_handler)

    # 2. FILE HANDLER (DEBUG completo com rotação)
    # Apenas se não for ambiente de teste
    if not (os.getenv("RC_TESTING") == "1" or os.getenv("PYTEST_CURRENT_TEST")):
        try:
            log_dir = Path("artifacts/local/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "rcgestor.log"

            # RotatingFileHandler: 10MB max, 5 backups
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)  # Arquivo sempre DEBUG
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)-40s | %(filename)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)

            # Redactor também no arquivo (não consoleim portant filter)
            file_handler.addFilter(RedactSensitiveData())

            root_logger.addHandler(file_handler)
        except Exception as exc:
            # Se falhar, continuar sem file handler (não bloquear app)
            root_logger.debug("Falha ao configurar file handler: %s", exc)

    # Configurar logger py.warnings (captado por captureWarnings)
    warnings_logger = logging.getLogger("py.warnings")
    warnings_logger.setLevel(logging.WARNING)  # Apenas WARNING+

    # Configurar nível DEBUG para loggers ruidosos
    # Eles só aparecerão no arquivo de log, não no console
    logging.getLogger("src.ui.ttk_treeview_manager").setLevel(logging.DEBUG)
    logging.getLogger("src.ui.ttk_treeview_theme").setLevel(logging.DEBUG)
    logging.getLogger("src.utils.network").setLevel(logging.DEBUG)
    logging.getLogger("infra.supabase.storage").setLevel(logging.DEBUG)
    logging.getLogger("src.modules.clientes.ui.views.client_files_dialog").setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True
