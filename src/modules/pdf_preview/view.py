"""View principal do módulo de visualização de PDFs.

Este módulo encapsula a UI legada de preview de PDFs
(`src.ui.pdf_preview_native`) e reexporta os entrypoints usados
pelo restante da aplicação.

Qualquer ajuste visual futuro do preview deve ser feito aqui,
mantendo a interface estável para o restante do app.
"""

from __future__ import annotations

from typing import Any

from src.ui.pdf_preview_native import PdfViewerWin, open_pdf_viewer as _open_pdf_viewer

__all__ = ["PdfPreviewFrame", "open_pdf_viewer"]


class PdfPreviewFrame(PdfViewerWin):
    """Alias tipado para a janela principal de preview de PDF."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


def open_pdf_viewer(*args: Any, **kwargs: Any):
    """Wrapper fino para o helper legado `open_pdf_viewer`."""
    return _open_pdf_viewer(*args, **kwargs)
