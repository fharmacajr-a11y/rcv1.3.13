"""Helpers puros para lógica de UI do PDF Viewer.

Este módulo contém funções puras extraídas de main_window.py para facilitar
testes e reduzir acoplamento com Tkinter.
"""

from __future__ import annotations

import mimetypes


def is_pdf_or_image(source: str | None) -> tuple[bool, bool]:
    """Retorna flags indicando se o arquivo é PDF ou imagem.

    Args:
        source: Caminho ou nome do arquivo (pode ser None)

    Returns:
        Tupla (is_pdf, is_image) com flags booleanas

    Examples:
        >>> is_pdf_or_image("doc.pdf")
        (True, False)
        >>> is_pdf_or_image("photo.jpg")
        (False, True)
        >>> is_pdf_or_image(None)
        (False, False)
    """
    mime, _ = mimetypes.guess_type(source or "")
    is_pdf = bool(mime == "application/pdf")
    if not is_pdf and source:
        is_pdf = source.lower().endswith(".pdf")
    is_image = bool(mime and mime.startswith("image/"))
    return is_pdf, is_image


def format_page_label(
    current_page: int,
    total_pages: int,
    zoom_percent: int,
    *,
    page_prefix: str = "Página",
    suffix: str = "",
) -> tuple[str, str]:
    """Formata labels de página e zoom para exibição.

    Args:
        current_page: Índice da página atual (0-based)
        total_pages: Total de páginas no documento
        zoom_percent: Percentual de zoom (ex: 100 para 100%)
        page_prefix: Prefixo para o label de página
        suffix: Sufixo adicional para o label de página (ex: "• OCR: OK")

    Returns:
        Tupla (page_label, zoom_label) com os textos formatados

    Examples:
        >>> format_page_label(0, 5, 100)
        ('Página 1/5', '100%')
        >>> format_page_label(4, 10, 150, suffix="• OCR: OK")
        ('Página 5/10  • OCR: OK', '150%')
    """
    total = max(1, total_pages)
    clamped = max(0, min(current_page, total - 1))
    page_label = f"{page_prefix} {clamped + 1}/{total}"
    if suffix:
        page_label = f"{page_label}  {suffix}"
    zoom_label = f"{zoom_percent}%"
    return page_label, zoom_label


def find_first_visible_page(
    canvas_y: float,
    page_tops: list[int],
    page_heights: list[int],
) -> int:
    """Encontra o índice da primeira página visível no canvas.

    Args:
        canvas_y: Coordenada Y do topo do viewport do canvas
        page_tops: Lista com coordenadas Y do topo de cada página
        page_heights: Lista com alturas de cada página (em pixels)

    Returns:
        Índice (0-based) da primeira página visível

    Examples:
        >>> find_first_visible_page(0, [16, 1116, 2216], [1100, 1100, 1100])
        0
        >>> find_first_visible_page(1200, [16, 1116, 2216], [1100, 1100, 1100])
        1
        >>> find_first_visible_page(9999, [16, 1116, 2216], [1100, 1100, 1100])
        2
    """
    if not page_tops:
        return 0

    for idx, top in enumerate(page_tops):
        height = page_heights[idx] if idx < len(page_heights) else 0
        if canvas_y < top + height:
            return idx

    return len(page_tops) - 1


def calculate_button_states(
    *,
    is_pdf: bool,
    is_image: bool,
) -> tuple[bool, bool]:
    """Calcula estados (enabled/disabled) dos botões de download.

    Args:
        is_pdf: Se o arquivo atual é um PDF
        is_image: Se o arquivo atual é uma imagem

    Returns:
        Tupla (pdf_enabled, image_enabled) com flags booleanas

    Examples:
        >>> calculate_button_states(is_pdf=True, is_image=False)
        (True, False)
        >>> calculate_button_states(is_pdf=False, is_image=True)
        (False, True)
        >>> calculate_button_states(is_pdf=False, is_image=False)
        (False, False)
    """
    return is_pdf, is_image


def detect_file_type(source: str | None) -> tuple[bool, bool]:
    """Alias para is_pdf_or_image (compatibilidade).

    Args:
        source: Caminho ou nome do arquivo

    Returns:
        Tupla (is_pdf, is_image)
    """
    return is_pdf_or_image(source)


# ======== FASE 02: Zoom calculations ========


def calculate_zoom_step(
    current_zoom: float,
    wheel_steps: int | float,
    *,
    min_zoom: float = 0.2,
    max_zoom: float = 6.0,
    step: float = 0.1,
) -> float:
    """Calcula novo zoom após aplicar steps de scroll/wheel.

    Args:
        current_zoom: Zoom atual (ex: 1.0 para 100%)
        wheel_steps: Quantidade de steps (positivo = zoom in, negativo = zoom out)
        min_zoom: Limite mínimo de zoom (padrão: 0.2 = 20%)
        max_zoom: Limite máximo de zoom (padrão: 6.0 = 600%)
        step: Incremento por step (padrão: 0.1 = 10%)

    Returns:
        Novo valor de zoom clamped entre min_zoom e max_zoom

    Examples:
        >>> calculate_zoom_step(1.0, 1)  # zoom in
        1.1
        >>> calculate_zoom_step(1.0, -2)  # zoom out
        0.8
        >>> calculate_zoom_step(5.9, 5)  # não ultrapassa max
        6.0
        >>> calculate_zoom_step(0.3, -5)  # não fica abaixo de min
        0.2
    """
    new_zoom = current_zoom + (wheel_steps * step)
    return max(min_zoom, min(max_zoom, round(new_zoom, 2)))


def calculate_zoom_fit_width(
    canvas_width: int,
    page_width: int,
    *,
    min_zoom: float = 0.2,
    max_zoom: float = 6.0,
    gap: int = 16,
) -> float:
    """Calcula zoom necessário para página caber na largura do canvas.

    Args:
        canvas_width: Largura do canvas em pixels
        page_width: Largura da página base (em zoom 1.0)
        min_zoom: Limite mínimo de zoom
        max_zoom: Limite máximo de zoom
        gap: Espaçamento lateral total (padrão: 16px)

    Returns:
        Zoom calculado clamped entre min/max

    Examples:
        >>> calculate_zoom_fit_width(800, 600)
        1.31
        >>> calculate_zoom_fit_width(400, 1000)
        0.38
        >>> calculate_zoom_fit_width(100, 800, gap=20)
        0.2
    """
    effective_width = max(1, canvas_width - gap)
    if page_width <= 0:
        return min_zoom
    raw_zoom = effective_width / page_width
    return max(min_zoom, min(max_zoom, round(raw_zoom, 2)))


def calculate_zoom_anchor(
    event_x: float,
    event_y: float,
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    """Calcula fração de ancoragem (fx, fy) para zoom centrado no cursor.

    Args:
        event_x: Coordenada X do cursor no canvas
        event_y: Coordenada Y do cursor no canvas
        bbox: Bounding box do canvas (x0, y0, x1, y1)

    Returns:
        Tupla (fx, fy) com frações 0.0-1.0 da posição relativa

    Examples:
        >>> calculate_zoom_anchor(400, 300, (0, 0, 800, 600))
        (0.5, 0.5)
        >>> calculate_zoom_anchor(0, 0, (0, 0, 800, 600))
        (0.0, 0.0)
        >>> calculate_zoom_anchor(800, 600, (0, 0, 800, 600))
        (1.0, 1.0)
        >>> calculate_zoom_anchor(100, 200, (100, 100, 100, 100))  # bbox degenerado
        (0.0, 0.0)
    """
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0

    fx = 0.0 if width == 0 else (event_x - x0) / width
    fy = 0.0 if height == 0 else (event_y - y0) / height

    # Clamp para evitar valores fora de [0, 1]
    fx = max(0.0, min(1.0, fx))
    fy = max(0.0, min(1.0, fy))

    return fx, fy


def should_apply_zoom_change(
    old_zoom: float,
    new_zoom: float,
    *,
    threshold: float = 1e-9,
) -> bool:
    """Determina se mudança de zoom é significativa o suficiente para aplicar.

    Args:
        old_zoom: Zoom atual
        new_zoom: Novo zoom calculado
        threshold: Limiar de diferença mínima (padrão: 1e-9)

    Returns:
        True se diferença for maior que threshold

    Examples:
        >>> should_apply_zoom_change(1.0, 1.1)
        True
        >>> should_apply_zoom_change(1.0, 1.0000000001)
        False
        >>> should_apply_zoom_change(0.5, 0.6, threshold=0.05)
        True
    """
    return abs(new_zoom - old_zoom) >= threshold


# ======== FASE 03: Page navigation logic ========


def clamp_page_index(
    index: int,
    total_pages: int,
) -> int:
    """Garante que índice de página fique dentro do range válido [0, total_pages-1].

    Args:
        index: Índice de página (0-based)
        total_pages: Total de páginas no documento

    Returns:
        Índice clamped entre 0 e total_pages-1 (ou 0 se total_pages <= 0)

    Examples:
        >>> clamp_page_index(5, 10)
        5
        >>> clamp_page_index(-3, 10)
        0
        >>> clamp_page_index(15, 10)
        9
        >>> clamp_page_index(5, 0)
        0
    """
    if total_pages <= 0:
        return 0
    return max(0, min(index, total_pages - 1))


def get_next_page_index(
    current_index: int,
    total_pages: int,
) -> int:
    """Retorna índice da próxima página (ou permanece se já estiver na última).

    Args:
        current_index: Índice da página atual (0-based)
        total_pages: Total de páginas no documento

    Returns:
        Índice da próxima página (clamped no range válido)

    Examples:
        >>> get_next_page_index(3, 10)
        4
        >>> get_next_page_index(9, 10)
        9
        >>> get_next_page_index(0, 0)
        0
    """
    if total_pages <= 0:
        return 0
    next_index = current_index + 1
    return clamp_page_index(next_index, total_pages)


def get_prev_page_index(
    current_index: int,
    total_pages: int,
) -> int:
    """Retorna índice da página anterior (ou permanece se já estiver na primeira).

    Args:
        current_index: Índice da página atual (0-based)
        total_pages: Total de páginas no documento

    Returns:
        Índice da página anterior (clamped no range válido)

    Examples:
        >>> get_prev_page_index(5, 10)
        4
        >>> get_prev_page_index(0, 10)
        0
        >>> get_prev_page_index(3, 0)
        0
    """
    if total_pages <= 0:
        return 0
    prev_index = current_index - 1
    return clamp_page_index(prev_index, total_pages)


def get_first_page_index(
    total_pages: int,
) -> int:
    """Retorna índice da primeira página (sempre 0).

    Args:
        total_pages: Total de páginas no documento

    Returns:
        0 (primeira página em índice 0-based)

    Examples:
        >>> get_first_page_index(10)
        0
        >>> get_first_page_index(1)
        0
        >>> get_first_page_index(0)
        0
    """
    return 0


def get_last_page_index(
    total_pages: int,
) -> int:
    """Retorna índice da última página.

    Args:
        total_pages: Total de páginas no documento

    Returns:
        Índice da última página (total_pages - 1, ou 0 se total_pages <= 0)

    Examples:
        >>> get_last_page_index(10)
        9
        >>> get_last_page_index(1)
        0
        >>> get_last_page_index(0)
        0
    """
    if total_pages <= 0:
        return 0
    return total_pages - 1
