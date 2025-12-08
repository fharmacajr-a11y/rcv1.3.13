"""Módulo PDF Preview - view e serviços."""

from __future__ import annotations

from .view import PdfPreviewFrame, open_pdf_viewer, open_pdf_viewer_from_download_result
from . import service

__all__ = ["PdfPreviewFrame", "open_pdf_viewer", "open_pdf_viewer_from_download_result", "service"]
