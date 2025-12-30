# -*- coding: utf-8 -*-
"""Unit tests for PdfRenderService.

Tests the headless PDF rendering service without requiring actual Tk root.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, sentinel

from src.modules.pdf_preview.render_service import PdfRenderService
from src.modules.pdf_preview.utils import LRUCache


class TestPdfRenderServiceCaching:
    """Tests for caching behavior."""

    def test_returns_blank_photo_when_pixmap_none_and_caches(self) -> None:
        """Test that blank PhotoImage is returned and cached when pixmap is None."""
        # Setup
        cache = LRUCache(12)
        service = PdfRenderService(cache=cache)
        page_sizes = [(800, 600)]

        # Mock controller that returns None pixmap
        mock_controller = MagicMock()
        mock_controller.get_page_pixmap.return_value = MagicMock(pixmap=None)

        # Patch tk.PhotoImage
        with patch("src.modules.pdf_preview.render_service.tk.PhotoImage") as mock_photo:
            mock_photo.return_value = sentinel.blank_photo

            # First call
            result1 = service.get_page_photoimage(
                page_index=0,
                zoom=1.0,
                page_sizes=page_sizes,
                pdf_controller=mock_controller,
            )

            # Second call (should use cache)
            result2 = service.get_page_photoimage(
                page_index=0,
                zoom=1.0,
                page_sizes=page_sizes,
                pdf_controller=mock_controller,
            )

        # Assertions
        assert result1 is sentinel.blank_photo
        assert result2 is sentinel.blank_photo
        # PhotoImage called only once (second call uses cache)
        assert mock_photo.call_count == 1
        # Controller called only once (second call uses cache)
        assert mock_controller.get_page_pixmap.call_count == 1

    def test_uses_pixmap_to_photoimage_when_available(self) -> None:
        """Test that pixmap_to_photoimage is used when pixmap is available."""
        # Setup
        cache = LRUCache(12)
        service = PdfRenderService(cache=cache)
        page_sizes = [(800, 600)]

        # Mock controller that returns valid pixmap
        mock_pixmap = MagicMock()
        mock_render_data = MagicMock(pixmap=mock_pixmap)
        mock_controller = MagicMock()
        mock_controller.get_page_pixmap.return_value = mock_render_data

        # Patch pixmap_to_photoimage
        with patch("src.modules.pdf_preview.render_service.pixmap_to_photoimage") as mock_convert:
            mock_convert.return_value = sentinel.converted_photo

            result = service.get_page_photoimage(
                page_index=0,
                zoom=1.0,
                page_sizes=page_sizes,
                pdf_controller=mock_controller,
            )

        # Assertions
        assert result is sentinel.converted_photo
        mock_convert.assert_called_once_with(mock_pixmap)

    def test_fallback_to_200x200_when_pixmap_convert_returns_none(self) -> None:
        """Test fallback to 200x200 blank image when pixmap conversion fails."""
        # Setup
        cache = LRUCache(12)
        service = PdfRenderService(cache=cache, min_px=200)
        page_sizes = [(800, 600)]

        # Mock controller that returns valid pixmap
        mock_pixmap = MagicMock()
        mock_render_data = MagicMock(pixmap=mock_pixmap)
        mock_controller = MagicMock()
        mock_controller.get_page_pixmap.return_value = mock_render_data

        # Patch pixmap_to_photoimage to return None (conversion failure)
        with (
            patch("src.modules.pdf_preview.render_service.pixmap_to_photoimage") as mock_convert,
            patch("src.modules.pdf_preview.render_service.tk.PhotoImage") as mock_photo,
        ):
            mock_convert.return_value = None
            mock_photo.return_value = sentinel.fallback_photo

            result = service.get_page_photoimage(
                page_index=0,
                zoom=1.0,
                page_sizes=page_sizes,
                pdf_controller=mock_controller,
            )

        # Assertions
        assert result is sentinel.fallback_photo
        # Should be called with min_px dimensions
        mock_photo.assert_called_once_with(width=200, height=200)


class TestPdfRenderServiceClearCache:
    """Tests for cache clearing."""

    def test_clear_cache_removes_all_entries(self) -> None:
        """Test that clear_cache removes all cached entries."""
        cache = LRUCache(12)
        service = PdfRenderService(cache=cache)

        # Add something to cache directly
        cache.put(("test", 1.0), "value")
        assert cache.get(("test", 1.0)) == "value"

        # Clear via service
        service.clear_cache()

        # Verify cache is empty
        assert cache.get(("test", 1.0)) is None


class TestPdfRenderServiceEdgeCases:
    """Tests for edge cases."""

    def test_handles_none_controller(self) -> None:
        """Test that None controller results in blank image."""
        cache = LRUCache(12)
        service = PdfRenderService(cache=cache)
        page_sizes = [(800, 600)]

        with patch("src.modules.pdf_preview.render_service.tk.PhotoImage") as mock_photo:
            mock_photo.return_value = sentinel.blank_photo

            result = service.get_page_photoimage(
                page_index=0,
                zoom=1.0,
                page_sizes=page_sizes,
                pdf_controller=None,
            )

        assert result is sentinel.blank_photo

    def test_handles_invalid_page_index(self) -> None:
        """Test that invalid page index results in blank image."""
        cache = LRUCache(12)
        service = PdfRenderService(cache=cache, min_px=200)
        page_sizes = [(800, 600)]  # Only page 0 exists

        with patch("src.modules.pdf_preview.render_service.tk.PhotoImage") as mock_photo:
            mock_photo.return_value = sentinel.blank_photo

            # Request page index out of range
            result = service.get_page_photoimage(
                page_index=5,
                zoom=1.0,
                page_sizes=page_sizes,
                pdf_controller=None,
            )

        assert result is sentinel.blank_photo
        mock_photo.assert_called_once_with(width=200, height=200)
