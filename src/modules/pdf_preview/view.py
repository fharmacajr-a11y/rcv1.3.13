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

__all__ = ["PdfPreviewFrame", "open_pdf_viewer", "open_pdf_viewer_from_download_result"]


class PdfPreviewFrame(PdfViewerWin):
    """Alias tipado para a janela principal de preview de PDF."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


def open_pdf_viewer(*args: Any, **kwargs: Any):
    """Wrapper fino para o helper legado `open_pdf_viewer`."""
    return _open_pdf_viewer(*args, **kwargs)


def open_pdf_viewer_from_download_result(master: Any, download_result: dict[str, Any]):
    """Abre o PDF viewer interno a partir do resultado de download_and_open_file(mode='internal').

    Args:
        master: Widget pai (Tkinter)
        download_result: Resultado de download_and_open_file() com mode='internal'

    Returns:
        PdfViewerWin instance ou None se resultado inválido

    Example:
        result = download_and_open_file("path/to/file.pdf", mode="internal")
        if result["ok"] and result.get("mode") == "internal":
            open_pdf_viewer_from_download_result(root, result)
    """
    if not download_result.get("ok"):
        return None

    if download_result.get("mode") != "internal":
        return None

    temp_path = download_result.get("temp_path")
    display_name = download_result.get("display_name")

    if not temp_path:
        return None

    return open_pdf_viewer(
        master,
        pdf_path=temp_path,
        display_name=display_name,
    )
