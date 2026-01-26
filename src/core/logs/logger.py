"""Configuração de logging para o sistema.

Este módulo fornece helpers para logging consistente em toda a aplicação.
Logs gerados em runtime vão para artifacts/local/logs/ (ignorado no git).
"""

import logging
import os
from pathlib import Path
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado.

    Args:
        name: Nome do logger (geralmente __name__ do módulo).

    Returns:
        Logger configurado com NullHandler por padrão.
    """
    logger = logging.getLogger(name)

    # Se ainda não tem handlers, adiciona NullHandler
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    return logger


def configure_file_logging(
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
) -> None:
    """Configura logging para arquivo (chamado em runtime, não no import).

    Args:
        log_dir: Diretório para logs. Se None, usa artifacts/local/logs/.
        level: Nível de logging (default: INFO).
    """
    if log_dir is None:
        # Logs gerados vão para artifacts/local/logs/ (ignorado)
        log_dir = os.environ.get("RC_LOG_DIR", "artifacts/local/logs")

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configura root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path / "rcgestor.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
