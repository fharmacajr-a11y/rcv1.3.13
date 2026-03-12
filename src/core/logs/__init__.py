"""Módulo de logging e auditoria do sistema.

Fornece funcionalidades de logging consistente e auditoria de ações.
Não cria arquivos/diretórios no import - apenas define funções.
"""

from . import configure, filters
from .logger import configure_file_logging, get_logger

__all__ = [
    "configure",
    "filters",
    "get_logger",
    "configure_file_logging",
]
