"""Módulo de logging e auditoria do sistema.

Fornece funcionalidades de logging consistente e auditoria de ações.
Não cria arquivos/diretórios no import - apenas define funções.
"""

from .audit import log_client_action
from .logger import configure_file_logging, get_logger

__all__ = ["log_client_action", "get_logger", "configure_file_logging"]
