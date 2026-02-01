# -*- coding: utf-8 -*-
"""Filtros de stream para suprimir linhas específicas em tempo real.

Útil para filtrar warnings de bibliotecas externas sem capturar/replay.
"""

from __future__ import annotations

import re
import sys
from typing import Any, TextIO


class LineFilterStream:
    """Stream wrapper que filtra linhas baseado em patterns regex.

    Escreve linha por linha no stream original, descartando aquelas que
    matcham patterns fornecidos. Preserva tracebacks e outros outputs.
    """

    def __init__(self, original_stream: TextIO, drop_patterns: list[str]) -> None:
        """Inicializa o filtro de stream.

        Args:
            original_stream: Stream original (sys.stdout ou sys.stderr)
            drop_patterns: Lista de regex patterns para descartar linhas
        """
        self._original = original_stream
        self._patterns = [re.compile(p) for p in drop_patterns]
        self._buffer = ""

    def write(self, text: str) -> int:
        """Escreve texto no stream, filtrando linhas que matcham patterns.

        Args:
            text: Texto a escrever

        Returns:
            Número de caracteres escritos (do texto original)
        """
        # Adicionar ao buffer
        self._buffer += text

        # Processar linhas completas
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line += "\n"

            # Verificar se deve descartar
            if any(pattern.search(line) for pattern in self._patterns):
                continue  # Descartar esta linha

            # Escrever no stream original
            self._original.write(line)

        return len(text)

    def flush(self) -> None:
        """Flush do buffer e stream original."""
        # Escrever qualquer coisa no buffer (linha incompleta)
        if self._buffer:
            # Não filtrar linhas incompletas (pode quebrar tracebacks)
            self._original.write(self._buffer)
            self._buffer = ""

        self._original.flush()

    def __getattr__(self, name: str) -> Any:
        """Proxy outros atributos para o stream original."""
        return getattr(self._original, name)


def install_line_filters(
    drop_patterns: list[str],
    streams: tuple[str, ...] = ("stdout", "stderr"),
) -> None:
    """Instala filtros de linha em sys.stdout/stderr.

    Args:
        drop_patterns: Lista de regex patterns para descartar linhas
        streams: Tuple com nomes dos streams ("stdout", "stderr")

    Example:
        >>> install_line_filters(
        ...     drop_patterns=[r"Storage endpoint URL should have a trailing slash"],
        ...     streams=("stdout", "stderr")
        ... )
    """
    if "stdout" in streams and not isinstance(sys.stdout, LineFilterStream):
        sys.stdout = LineFilterStream(sys.stdout, drop_patterns)  # type: ignore[assignment]

    if "stderr" in streams and not isinstance(sys.stderr, LineFilterStream):
        sys.stderr = LineFilterStream(sys.stderr, drop_patterns)  # type: ignore[assignment]
