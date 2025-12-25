# -*- coding: utf-8 -*-
"""
PDF Zoom Controller - Lógica de zoom sem dependências de Tkinter.

Extraído de views/main_window.py para:
- Reduzir complexidade da view
- Tornar lógica de zoom testável independentemente da UI
- Centralizar cálculos de zoom (PDF e imagem)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Protocol, Tuple

if TYPE_CHECKING:
    from src.modules.pdf_preview.controller import PdfPreviewController

logger = logging.getLogger(__name__)

__all__ = ["PdfZoomController"]

# Type aliases
ZoomValue = float
CanvasWidth = int


class PdfControllerLike(Protocol):
    """Protocol para dependências do PdfZoomController."""

    def set_zoom(self, zoom: ZoomValue, fit_mode: bool = False) -> None:
        """Define zoom no controller principal."""
        ...

    def get_page_size(self, page_index: int) -> Tuple[int, int] | None:
        """Retorna (width, height) da página em escala 1.0."""
        ...

    def get_canvas_width(self) -> CanvasWidth:
        """Retorna largura do canvas."""
        ...


class PdfZoomController:
    """Controller headless para gerenciar zoom de PDF/imagem."""

    def __init__(
        self,
        *,
        min_zoom: ZoomValue = 0.1,
        max_zoom: ZoomValue = 6.0,
        zoom_step: ZoomValue = 0.1,
    ) -> None:
        """Inicializa controller de zoom.

        Args:
            min_zoom: Zoom mínimo permitido
            max_zoom: Zoom máximo permitido
            zoom_step: Incremento por step de zoom
        """
        self._min_zoom: ZoomValue = min_zoom
        self._max_zoom: ZoomValue = max_zoom
        self._zoom_step: ZoomValue = zoom_step

        # Estado interno
        self._current_zoom: ZoomValue = 1.0
        self._fit_mode: bool = False

        # Para imagens
        self._img_zoom: ZoomValue = 1.0

    @property
    def current_zoom(self) -> ZoomValue:
        """Zoom atual para PDF."""
        return self._current_zoom

    @property
    def img_zoom(self) -> ZoomValue:
        """Zoom atual para imagem."""
        return self._img_zoom

    @property
    def is_fit_mode(self) -> bool:
        """Se está em modo fit-to-width."""
        return self._fit_mode

    def calculate_zoom_by_delta(
        self,
        current: ZoomValue,
        wheel_steps: int | float,
        *,
        is_image: bool = False,
    ) -> ZoomValue:
        """Calcula novo zoom baseado em delta de wheel steps.

        Args:
            current: Zoom atual
            wheel_steps: Número de steps do wheel (positivo = zoom in)
            is_image: Se True, usa limites de zoom de imagem (0.1-5.0)

        Returns:
            Novo valor de zoom (clamped)

        Examples:
            >>> ctrl = PdfZoomController()
            >>> ctrl.calculate_zoom_by_delta(1.0, 2)
            1.2

            >>> ctrl.calculate_zoom_by_delta(0.5, -3)
            0.2
        """
        if is_image:
            min_z, max_z = 0.1, 5.0
        else:
            min_z, max_z = self._min_zoom, self._max_zoom

        new_zoom = current + wheel_steps * self._zoom_step
        return max(min_z, min(max_z, round(new_zoom, 2)))

    def calculate_fit_to_width_zoom(
        self,
        canvas_width: CanvasWidth,
        page_or_image_width: int,
        *,
        gap: int = 16,
        is_image: bool = False,
    ) -> ZoomValue:
        """Calcula zoom para fit-to-width.

        Args:
            canvas_width: Largura do canvas
            page_or_image_width: Largura da página/imagem em escala 1.0
            gap: Padding lateral
            is_image: Se True, usa limites de imagem

        Returns:
            Zoom adequado para fit-to-width

        Examples:
            >>> ctrl = PdfZoomController()
            >>> ctrl.calculate_fit_to_width_zoom(1000, 800, gap=16)
            1.23
        """
        if is_image:
            min_z, max_z = 0.1, 5.0
        else:
            min_z, max_z = self._min_zoom, self._max_zoom

        available_width = max(1, canvas_width - 2 * gap)
        target = available_width / max(1, page_or_image_width)
        return max(min_z, min(max_z, round(target, 2)))

    def apply_zoom_to_pdf(
        self,
        wheel_steps: int | float,
        pdf_controller: Optional[PdfPreviewController],
    ) -> ZoomValue:
        """Aplica zoom a um PDF via PdfPreviewController.

        Args:
            wheel_steps: Delta de zoom
            pdf_controller: Controller do PDF (pode ser None)

        Returns:
            Novo zoom calculado
        """
        if pdf_controller is not None:
            new_zoom = pdf_controller.apply_zoom_delta(wheel_steps)
            self._current_zoom = new_zoom
            self._fit_mode = False
            return new_zoom

        # Fallback sem controller
        new_zoom = self.calculate_zoom_by_delta(self._current_zoom, wheel_steps)
        self._current_zoom = new_zoom
        self._fit_mode = False
        return new_zoom

    def apply_zoom_to_image(
        self,
        wheel_steps: int | float,
    ) -> ZoomValue:
        """Aplica zoom a uma imagem.

        Args:
            wheel_steps: Delta de zoom

        Returns:
            Novo zoom de imagem
        """
        new_zoom = self.calculate_zoom_by_delta(
            self._img_zoom,
            wheel_steps,
            is_image=True,
        )
        self._img_zoom = new_zoom
        return new_zoom

    def set_exact_zoom(
        self,
        zoom: ZoomValue,
        *,
        fit_mode: bool = False,
        pdf_controller: Optional[PdfPreviewController] = None,
    ) -> ZoomValue:
        """Define zoom exato.

        Args:
            zoom: Valor de zoom desejado
            fit_mode: Se é modo fit-to-width
            pdf_controller: Controller do PDF (opcional)

        Returns:
            Zoom efetivamente aplicado (pode ser clipado)
        """
        self._fit_mode = fit_mode

        if pdf_controller is not None:
            mode_str = "width" if fit_mode else "custom"
            pdf_controller.set_zoom(float(zoom), fit_mode=mode_str)
            self._current_zoom = pdf_controller.state.zoom
            return self._current_zoom

        # Fallback
        clamped = max(self._min_zoom, min(self._max_zoom, float(zoom)))
        self._current_zoom = clamped
        return clamped

    def toggle_fit_100(
        self,
        canvas_width: CanvasWidth,
        page_width: int,
        *,
        pdf_controller: Optional[PdfPreviewController] = None,
    ) -> Tuple[ZoomValue, bool]:
        """Alterna entre zoom 100% e fit-to-width.

        Args:
            canvas_width: Largura do canvas
            page_width: Largura da página
            pdf_controller: Controller do PDF

        Returns:
            (novo_zoom, agora_em_fit_mode)
        """
        if self._fit_mode:
            # Estava em fit → volta para 100%
            new_zoom = self.set_exact_zoom(1.0, fit_mode=False, pdf_controller=pdf_controller)
            return (new_zoom, False)
        else:
            # Estava em custom → vai para fit
            fit_zoom = self.calculate_fit_to_width_zoom(canvas_width, page_width)
            new_zoom = self.set_exact_zoom(fit_zoom, fit_mode=True, pdf_controller=pdf_controller)
            return (new_zoom, True)
