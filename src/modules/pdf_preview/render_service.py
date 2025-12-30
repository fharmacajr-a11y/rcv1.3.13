# -*- coding: utf-8 -*-
"""PDF Render Service - headless rendering logic for PDF preview.

This service handles page rendering and caching without any UI dependencies.
Extracted from main_window.py for better separation of concerns and testability.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Any

from src.modules.pdf_preview.utils import LRUCache, pixmap_to_photoimage

if TYPE_CHECKING:
    from src.modules.pdf_preview.controller import PdfPreviewController

logger = logging.getLogger(__name__)


class PdfRenderService:
    """Headless PDF page rendering service with caching.

    This service handles:
    - Page rendering via PdfPreviewController
    - LRU caching of rendered PhotoImages
    - Fallback blank images when rendering fails

    The service does NOT manage UI elements - that remains in the View.
    """

    def __init__(
        self,
        *,
        cache: LRUCache | None = None,
        cache_round: int = 2,
        min_px: int = 200,
    ) -> None:
        """Initialize the render service.

        Args:
            cache: LRU cache instance (creates new if None)
            cache_round: Decimal places for zoom rounding in cache key
            min_px: Minimum pixel size for fallback images
        """
        self._cache = cache if cache is not None else LRUCache(12)
        self._cache_round = cache_round
        self._min_px = min_px

    def clear_cache(self) -> None:
        """Clear all cached rendered images."""
        self._cache.clear()

    def get_page_photoimage(
        self,
        *,
        page_index: int,
        zoom: float,
        page_sizes: list[tuple[int, int]],
        pdf_controller: PdfPreviewController | None,
    ) -> tk.PhotoImage:
        """Get rendered page as PhotoImage, using cache when available.

        Args:
            page_index: Zero-based page index
            zoom: Current zoom level
            page_sizes: List of (width, height) tuples for each page at zoom=1.0
            pdf_controller: Controller for pixmap rendering (can be None)

        Returns:
            PhotoImage of the rendered page (or blank fallback)
        """
        key = (page_index, round(float(zoom), self._cache_round))
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        img = self._render_page_to_photoimage(
            page_index=page_index,
            zoom=float(zoom),
            page_sizes=page_sizes,
            pdf_controller=pdf_controller,
        )
        self._cache.put(key, img)
        return img

    def _render_page_to_photoimage(
        self,
        *,
        page_index: int,
        zoom: float,
        page_sizes: list[tuple[int, int]],
        pdf_controller: PdfPreviewController | None,
    ) -> tk.PhotoImage:
        """Render a PDF page to PhotoImage.

        Args:
            page_index: Zero-based page index
            zoom: Current zoom level
            page_sizes: List of (width, height) tuples for each page at zoom=1.0
            pdf_controller: Controller for pixmap rendering

        Returns:
            PhotoImage of the rendered page (or blank fallback)
        """
        # Get page size at zoom 1.0
        if page_index < 0 or page_index >= len(page_sizes):
            return tk.PhotoImage(width=self._min_px, height=self._min_px)

        w1, h1 = page_sizes[page_index]

        # Get pixmap from controller
        pix: Any = None
        if pdf_controller is not None:
            try:
                render = pdf_controller.get_page_pixmap(page_index=page_index, zoom=zoom)
                pix = render.pixmap if render is not None else None
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to get pixmap for page %d: %s", page_index, exc)
                pix = None

        # Fallback: blank image if no pixmap
        if pix is None:
            return tk.PhotoImage(
                width=max(self._min_px, int(w1 * zoom)),
                height=max(self._min_px, int(h1 * zoom)),
            )

        # Convert pixmap to PhotoImage
        photo = pixmap_to_photoimage(pix)
        if photo is None:
            # Final fallback: minimal blank image
            return tk.PhotoImage(width=self._min_px, height=self._min_px)

        return photo
