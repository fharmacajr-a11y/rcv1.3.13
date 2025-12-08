"""Fase PDF – testes headless do PdfPreviewController."""

from __future__ import annotations

import pytest

from src.modules.pdf_preview.controller import (
    PageRenderData,
    PdfButtonStates,
    PdfPreviewController,
)
from src.modules.pdf_preview.raster_service import RasterResult


class DummyRaster:
    """Raster fake para evitar dependência de PyMuPDF nos testes."""

    def __init__(self, page_count: int = 4) -> None:
        self.page_count = page_count
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def get_page_sizes(self) -> list[tuple[int, int]]:
        return [(800, 600) for _ in range(self.page_count)]

    def get_text_buffer(self) -> list[str]:
        return [f"Texto da página {idx + 1}" for idx in range(self.page_count)]

    def get_page_pixmap(self, page_index: int, zoom: float) -> RasterResult:
        return RasterResult(
            page_index=page_index,
            zoom=zoom,
            pixmap={"index": page_index, "zoom": zoom},
            width=int(800 * zoom),
            height=int(600 * zoom),
        )


@pytest.fixture
def controller() -> PdfPreviewController:
    return PdfPreviewController(raster_service=DummyRaster(page_count=5))


def test_controller_initializes_state_from_raster(controller: PdfPreviewController) -> None:
    assert controller.state.page_count == 5
    assert controller.page_sizes == [(800, 600)] * 5
    assert len(controller.text_buffer) == 5


def test_navigation_respects_bounds(controller: PdfPreviewController) -> None:
    controller.go_to_page(2)
    assert controller.state.current_page == 2
    controller.next_page()
    assert controller.state.current_page == 3
    controller.next_page()
    controller.next_page()
    assert controller.state.current_page == 4  # última página
    controller.next_page()
    assert controller.state.current_page == 4
    controller.first_page()
    assert controller.state.current_page == 0
    controller.prev_page()
    assert controller.state.current_page == 0


def test_zoom_delta_is_clamped(controller: PdfPreviewController) -> None:
    controller.set_zoom(1.0)
    new_zoom = controller.apply_zoom_delta(+3)  # +0.3
    assert new_zoom == pytest.approx(1.3)
    new_zoom = controller.apply_zoom_delta(-20)  # tenta ir abaixo do mínimo
    assert new_zoom == controller.MIN_ZOOM
    controller.set_zoom(controller.MAX_ZOOM - 0.05)
    controller.zoom_in()
    assert controller.state.zoom == controller.MAX_ZOOM


def test_button_states_change_with_navigation(controller: PdfPreviewController) -> None:
    controller.go_to_page(0)
    states = controller.get_button_states()
    assert states == PdfButtonStates(
        can_go_first=False,
        can_go_prev=False,
        can_go_next=True,
        can_go_last=True,
        can_zoom_in=True,
        can_zoom_out=True,
    )
    controller.go_to_page(controller.state.page_count - 1)
    states = controller.get_button_states()
    assert states.can_go_next is False
    assert states.can_go_last is False
    assert states.can_go_prev is True


def test_text_state_is_tracked(controller: PdfPreviewController) -> None:
    assert controller.state.show_text is False
    controller.toggle_text()
    assert controller.state.show_text is True
    controller.set_show_text(False)
    render_state = controller.get_render_state()
    assert render_state.show_text is False


def test_get_page_pixmap_returns_render_data(controller: PdfPreviewController) -> None:
    render = controller.get_page_pixmap(page_index=1, zoom=1.5)
    assert isinstance(render, PageRenderData)
    assert render.page_index == 1
    assert render.zoom == pytest.approx(1.5)
    assert isinstance(render.pixmap, dict)


def test_controller_close_delegates_to_raster() -> None:
    raster = DummyRaster()
    ctrl = PdfPreviewController(raster_service=raster)
    ctrl.close()
    assert raster.closed is True
