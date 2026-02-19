from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from .raster_service import PdfRasterService, RasterResult


@dataclass
class PageRenderData:
    page_index: int
    zoom: float
    pixmap: Any  # fitz.Pixmap
    width: int
    height: int


@dataclass
class PdfPreviewState:
    current_page: int = 0
    page_count: int = 0
    zoom: float = 1.0
    fit_mode: str = "width"
    show_text: bool = False


@dataclass(frozen=True)
class PdfRenderState:
    page_index: int
    page_count: int
    zoom: float
    show_text: bool


@dataclass(frozen=True)
class PdfButtonStates:
    can_go_first: bool
    can_go_prev: bool
    can_go_next: bool
    can_go_last: bool
    can_zoom_in: bool
    can_zoom_out: bool


class PdfPreviewController:
    """
    Controller de estado do preview de PDF.

    Mantém página/zoom/fit e cache de pixmaps, abrindo o documento
    via PyMuPDF quando disponível.
    """

    MIN_ZOOM = 0.2
    MAX_ZOOM = 6.0
    ZOOM_STEP = 0.1

    def __init__(
        self,
        *,
        pdf_bytes: Optional[bytes] = None,
        pdf_path: Optional[str] = None,
        raster_service: Optional[PdfRasterService] = None,
    ) -> None:
        self._raster = raster_service or PdfRasterService(pdf_bytes=pdf_bytes, pdf_path=pdf_path)
        page_count = self._raster.page_count if self._raster is not None else 0
        self.state = PdfPreviewState(page_count=page_count)
        self._page_sizes: List[Tuple[int, int]] = self._compute_page_sizes()
        self._text_buffer: List[str] = self._compute_text_buffer()

    def close(self) -> None:
        if self._raster is not None:
            self._raster.close()

    # --- Estado de navegação -------------------------------------------------
    def go_to_page(self, index: int) -> None:
        if self.state.page_count <= 0:
            return
        self.state.current_page = max(0, min(index, self.state.page_count - 1))

    def next_page(self) -> None:
        self.go_to_page(self.state.current_page + 1)

    def prev_page(self) -> None:
        self.go_to_page(self.state.current_page - 1)

    def first_page(self) -> None:
        self.go_to_page(0)

    def last_page(self) -> None:
        self.go_to_page(self.state.page_count - 1)

    # --- Zoom ----------------------------------------------------------------
    def _clamp_zoom(self, zoom: float) -> float:
        if zoom != zoom:  # NaN check
            zoom = self.state.zoom
        return max(self.MIN_ZOOM, min(self.MAX_ZOOM, round(zoom, 2)))

    def set_zoom(self, zoom: float, *, fit_mode: Optional[str] = None) -> None:
        if zoom <= 0:
            zoom = self.MIN_ZOOM
        self.state.zoom = self._clamp_zoom(zoom)
        if fit_mode is not None:
            self.state.fit_mode = fit_mode

    def zoom_in(self, step: float = ZOOM_STEP) -> None:
        self.set_zoom(self.state.zoom + step, fit_mode="custom")

    def zoom_out(self, step: float = ZOOM_STEP) -> None:
        self.set_zoom(self.state.zoom - step, fit_mode="custom")

    def apply_zoom_delta(self, wheel_steps: float, *, step: float = ZOOM_STEP) -> float:
        """
        Ajusta o zoom aplicando um delta (positivo/negativo) e retorna o novo valor.
        """
        delta = wheel_steps * step
        target = self.state.zoom + delta
        self.set_zoom(target, fit_mode="custom")
        return self.state.zoom

    def set_fit_width(self) -> None:
        self.state.fit_mode = "width"

    def set_zoom_100(self) -> None:
        self.set_zoom(1.0, fit_mode="100%")

    def toggle_text(self) -> None:
        self.state.show_text = not self.state.show_text

    def set_show_text(self, value: bool) -> bool:
        """Define o estado de exibição de texto e retorna o valor efetivo."""
        self.state.show_text = bool(value)
        return self.state.show_text

    # --- Render --------------------------------------------------------------
    def get_page_pixmap(
        self, page_index: Optional[int] = None, *, zoom: Optional[float] = None
    ) -> Optional[PageRenderData]:
        if self._raster is None:
            return None
        if page_index is None:
            page_index = self.state.current_page
        if zoom is not None:
            self.state.zoom = zoom
        result: Optional[RasterResult] = self._raster.get_page_pixmap(page_index, self.state.zoom)
        if result is None:
            return None
        return PageRenderData(
            page_index=page_index,
            zoom=result.zoom,
            pixmap=result.pixmap,
            width=result.width,
            height=result.height,
        )

    # --- Helpers -------------------------------------------------------------
    @property
    def page_sizes(self) -> List[Tuple[int, int]]:
        return list(self._page_sizes)

    @property
    def text_buffer(self) -> List[str]:
        return list(self._text_buffer)

    def get_page_label(self, prefix: str = "Página") -> str:
        total = max(1, self.state.page_count)
        current = max(0, min(self.state.current_page, total - 1))
        return f"{prefix} {current + 1}/{total}"

    def get_zoom_label(self) -> str:
        return f"{int(round(self.state.zoom * 100))}%"

    def _compute_page_sizes(self) -> List[Tuple[int, int]]:
        if self._raster is None:
            return [(800, 1100)]
        return self._raster.get_page_sizes()

    def _compute_text_buffer(self) -> List[str]:
        if self._raster is None:
            return ["Texto indisponível (PyMuPDF não detectado)."]
        return self._raster.get_text_buffer()

    def get_render_state(self) -> PdfRenderState:
        total = max(0, self.state.page_count)
        current = max(0, min(self.state.current_page, max(total - 1, 0)))
        return PdfRenderState(
            page_index=current,
            page_count=total,
            zoom=self.state.zoom,
            show_text=self.state.show_text,
        )

    def get_button_states(self) -> PdfButtonStates:
        total = max(0, self.state.page_count)
        current = max(0, min(self.state.current_page, max(total - 1, 0)))
        has_pages = total > 0
        can_prev = has_pages and current > 0
        can_next = has_pages and current < (total - 1)
        return PdfButtonStates(
            can_go_first=can_prev,
            can_go_prev=can_prev,
            can_go_next=can_next,
            can_go_last=can_next,
            can_zoom_in=self.state.zoom < self.MAX_ZOOM,
            can_zoom_out=self.state.zoom > self.MIN_ZOOM,
        )
