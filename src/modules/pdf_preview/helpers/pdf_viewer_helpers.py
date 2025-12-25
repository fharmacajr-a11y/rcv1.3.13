# -*- coding: utf-8 -*-
"""
PDF Viewer Helpers - Funções puras sem Tkinter.

Extraído de views/main_window.py para reduzir complexidade e melhorar testabilidade.
"""

from __future__ import annotations

from typing import List, Tuple

__all__ = [
    "calculate_page_tops",
    "update_button_states_from_doc",
    "validate_zoom_value",
]

# Type aliases para clareza
ZoomValue = float
PageIndex = int
PixelCoord = int
PageSize = Tuple[int, int]  # (width, height)

GAP = 16  # espaço entre páginas (constante global)


def calculate_page_tops(
    page_sizes: List[PageSize],
    zoom: ZoomValue,
    *,
    gap: int = GAP,
) -> List[PixelCoord]:
    """Calcula posições Y (tops) de cada página no canvas.

    Args:
        page_sizes: Lista de (width, height) em escala 1.0
        zoom: Fator de zoom atual
        gap: Espaçamento entre páginas

    Returns:
        Lista de coordenadas Y onde cada página começa

    Examples:
        >>> calculate_page_tops([(800, 1100), (800, 1100)], zoom=1.0, gap=16)
        [16, 1132]
    """
    tops = []
    y = gap
    for w, h in page_sizes:
        tops.append(y)
        h_scaled = int(h * zoom)
        y += h_scaled + gap
    return tops


def update_button_states_from_doc(
    is_pdf: bool,
    is_image: bool,
) -> Tuple[bool, bool]:
    """Calcula estados dos botões de download baseado no tipo de documento.

    Args:
        is_pdf: Se o documento é PDF
        is_image: Se o documento é imagem

    Returns:
        (pdf_button_enabled, image_button_enabled)

    Examples:
        >>> update_button_states_from_doc(True, False)
        (True, False)

        >>> update_button_states_from_doc(False, True)
        (False, True)
    """
    # PDF: habilita download de PDF
    # Imagem: habilita download de imagem
    return (is_pdf, is_image)


def validate_zoom_value(
    zoom: ZoomValue,
    *,
    min_zoom: ZoomValue = 0.1,
    max_zoom: ZoomValue = 5.0,
) -> ZoomValue:
    """Valida e clipa valor de zoom dentro de limites.

    Args:
        zoom: Valor de zoom solicitado
        min_zoom: Zoom mínimo permitido
        max_zoom: Zoom máximo permitido

    Returns:
        Valor de zoom válido (clamped)

    Examples:
        >>> validate_zoom_value(1.5)
        1.5

        >>> validate_zoom_value(10.0)
        5.0

        >>> validate_zoom_value(0.01)
        0.1
    """
    return max(min_zoom, min(zoom, max_zoom))
