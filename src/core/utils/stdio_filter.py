# -*- coding: utf-8 -*-
"""Context manager para suprimir linhas específicas de stdout/stderr.

Útil para filtrar warnings/mensagens indesejadas de bibliotecas externas
sem esconder todos os outputs.
"""

from __future__ import annotations

import io
import re
import sys
from contextlib import contextmanager
from typing import Generator


@contextmanager
def suppress_stdio_lines(patterns: list[str]) -> Generator[None, None, None]:
    """Context manager que captura stdout/stderr e filtra linhas por regex.

    Args:
        patterns: Lista de regex patterns. Linhas que matcharem qualquer pattern
                  serão suprimidas (não reemitidas).

    Yields:
        None

    Example:
        >>> patterns = [r"^Storage endpoint URL should have a trailing slash\\.\\s*$"]
        >>> with suppress_stdio_lines(patterns):
        ...     create_client(...)  # Warning será filtrado
    """
    # Salvar streams originais
    old_out = sys.stdout
    old_err = sys.stderr

    # Criar buffers para captura
    buf_out = io.StringIO()
    buf_err = io.StringIO()

    # Redirecionar streams
    sys.stdout = buf_out
    sys.stderr = buf_err

    try:
        yield
    finally:
        # Restaurar streams originais
        sys.stdout = old_out
        sys.stderr = old_err

        # Função para replay com filtro
        def replay(text: str, stream: io.TextIOBase) -> None:
            """Reemite texto linha por linha, filtrando patterns."""
            for line in text.splitlines(keepends=True):
                # Verificar se linha matcha algum pattern
                if any(re.search(pattern, line) for pattern in patterns):
                    continue  # Suprimir esta linha
                stream.write(line)

        # Reemitir outputs filtrados
        replay(buf_out.getvalue(), old_out)
        replay(buf_err.getvalue(), old_err)
