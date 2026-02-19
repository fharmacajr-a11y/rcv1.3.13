"""Service fino para o módulo de visualização de PDFs.

Este arquivo expõe uma API estável para operações de leitura
em PDFs reutilizando os utilitários legados.
"""

from __future__ import annotations

from src.utils.pdf_reader import read_pdf_text

__all__ = ["read_pdf_text"]
