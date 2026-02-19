# -*- coding: utf-8 -*-
"""
PDF Render Controller - Lógica de renderização sem Tkinter direto.

Extraído de views/main_window.py para separar lógica de renderização
da UI e permitir testabilidade.
"""

from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.modules.pdf_preview.controller import PdfPreviewController, PageRenderData
    from src.modules.pdf_preview.utils import LRUCache

logger = logging.getLogger(__name__)

__all__ = ["PdfRenderController", "PageLayout"]

GAP = 16

# Type aliases
ZoomValue = float
PageIndex = int
PixelCoord = int
PageSize = Tuple[int, int]  # (width, height)


@dataclass(frozen=True)
class PageLayout:
    """Resultado de calculate_page_layout."""

    page_tops: List[PixelCoord]
    total_width: int
    total_height: int


class PdfRenderController:
    """Controller para gerenciar renderização de páginas PDF."""

    def __init__(
        self,
        *,
        gap: int = GAP,
    ) -> None:
        """Inicializa controller de render.

        Args:
            gap: Espaçamento entre páginas
        """
        self._gap: int = gap

    def calculate_page_layout(
        self,
        page_sizes: List[PageSize],
        zoom: ZoomValue,
    ) -> PageLayout:
        """Calcula layout das páginas (tops, total width/height).

        Args:
            page_sizes: Lista de (width, height) em escala 1.0
            zoom: Fator de zoom

        Returns:
            PageLayout com page_tops, total_width, total_height

        Examples:
            >>> ctrl = PdfRenderController()
            >>> layout = ctrl.calculate_page_layout([(800, 1100), (800, 1100)], 1.0)
            >>> layout.page_tops
            [16, 1132]
            >>> layout.total_width, layout.total_height
            (832, 2248)
        """
        page_tops = []
        y = self._gap
        max_width = 0

        for w1, h1 in page_sizes:
            w = int(w1 * zoom)
            h = int(h1 * zoom)
            page_tops.append(y)
            y += h + self._gap
            max_width = max(max_width, w + 2 * self._gap)

        total_height = y
        return PageLayout(
            page_tops=page_tops,
            total_width=max_width,
            total_height=total_height,
        )

    def find_visible_page_indices(
        self,
        page_tops: List[PixelCoord],
        page_sizes: List[PageSize],
        zoom: ZoomValue,
        canvas_y0: int,
        canvas_height: int,
        *,
        margin: int = 32,
    ) -> List[PageIndex]:
        """Encontra índices de páginas visíveis no canvas.

        Args:
            page_tops: Lista de coordenadas Y de cada página
            page_sizes: Lista de (width, height) em escala 1.0
            zoom: Fator de zoom
            canvas_y0: Coordenada Y superior do canvas (via canvasy)
            canvas_height: Altura visível do canvas
            margin: Margem extra para pré-render

        Returns:
            Lista de índices de páginas visíveis

        Examples:
            >>> ctrl = PdfRenderController()
            >>> ctrl.find_visible_page_indices(
            ...     [16, 1132],
            ...     [(800, 1100), (800, 1100)],
            ...     1.0,
            ...     0,
            ...     800,
            ... )
            [0]
        """
        visible = []
        y1 = canvas_y0 + canvas_height

        for i, top in enumerate(page_tops):
            h = int(page_sizes[i][1] * zoom)
            bottom = top + h

            # Verifica se página está na área visível (com margem)
            if bottom < canvas_y0 - margin:
                continue
            if top > y1 + margin:
                continue

            visible.append(i)

        return visible

    def render_page_to_photoimage(
        self,
        page_index: int,
        zoom: float,
        page_sizes: List[Tuple[int, int]],
        pdf_controller: Optional[PdfPreviewController],
        *,
        use_fallback_on_error: bool = True,
    ) -> Optional[tk.PhotoImage]:
        """Renderiza uma página para PhotoImage.

        Args:
            page_index: Índice da página (0-based)
            zoom: Fator de zoom
            page_sizes: Lista de (width, height) em escala 1.0
            pdf_controller: Controller do PDF (pode ser None)
            use_fallback_on_error: Se True, retorna imagem vazia em caso de erro

        Returns:
            PhotoImage ou None
        """
        if page_index >= len(page_sizes):
            if use_fallback_on_error:
                return tk.PhotoImage(width=200, height=200)
            return None

        w1, h1 = page_sizes[page_index]

        # Obtém pixmap do controller
        if pdf_controller is not None:
            try:
                render: Optional[PageRenderData] = pdf_controller.get_page_pixmap(
                    page_index=page_index,
                    zoom=zoom,
                )
                pix = render.pixmap if render is not None else None
            except Exception as exc:
                logger.debug("Erro ao obter pixmap da página %d: %s", page_index, exc)
                pix = None
        else:
            pix = None

        # Fallback: imagem vazia se não houver pixmap
        if pix is None:
            if use_fallback_on_error:
                w = max(200, int(w1 * zoom))
                h = max(200, int(h1 * zoom))
                return tk.PhotoImage(width=w, height=h)
            return None

        # Converte pixmap para PhotoImage
        try:
            from src.modules.pdf_preview.utils import pixmap_to_photoimage

            photo = pixmap_to_photoimage(pix)
            if photo is not None:
                return photo
        except Exception as exc:
            logger.debug("Erro ao converter pixmap para PhotoImage: %s", exc)

        # Último fallback
        if use_fallback_on_error:
            return tk.PhotoImage(width=200, height=200)
        return None

    def update_canvas_items(
        self,
        canvas: Any,  # tk.Canvas
        items: List[int],
        page_tops: List[int],
        img_refs: Dict[int, tk.PhotoImage],
        cache: LRUCache,
        page_sizes: List[Tuple[int, int]],
        zoom: float,
        pdf_controller: Optional[PdfPreviewController],
        visible_indices: List[int],
    ) -> None:
        """Atualiza itens do canvas para páginas visíveis.

        Args:
            canvas: Canvas do Tkinter
            items: Lista de item IDs do canvas (por página)
            page_tops: Lista de coordenadas Y
            img_refs: Dicionário para manter referências vivas
            cache: LRU cache de imagens
            page_sizes: Lista de (width, height)
            zoom: Fator de zoom
            pdf_controller: Controller do PDF
            visible_indices: Índices de páginas visíveis
        """
        for i in visible_indices:
            if i >= len(items):
                continue

            # Verifica cache
            key = (i, round(zoom, 2))
            img = cache.get(key)

            if img is None:
                # Renderiza e cacheia
                img = self.render_page_to_photoimage(
                    i,
                    zoom,
                    page_sizes,
                    pdf_controller,
                )
                if img is not None:
                    cache.put(key, img)

            if img is not None:
                item_id = items[i]
                try:
                    canvas.itemconfig(item_id, image=img)
                    img_refs[item_id] = img  # manter referência viva
                except Exception as exc:
                    logger.debug("Erro ao atualizar item %d do canvas: %s", item_id, exc)
