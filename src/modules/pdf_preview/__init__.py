"""Módulo PDF Preview - view e serviços."""

from __future__ import annotations

from .view import PdfPreviewFrame, open_pdf_viewer
from . import service

__all__ = ["PdfPreviewFrame", "open_pdf_viewer", "service"]
