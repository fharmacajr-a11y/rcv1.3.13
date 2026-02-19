from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - ambiente sem PyMuPDF
    fitz = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class RasterResult:
    page_index: int
    zoom: float
    pixmap: Any  # fitz.Pixmap
    width: int
    height: int


class PdfRasterService:
    """
    Serviço responsável por abrir documentos PDF e rasterizar páginas.

    - abre o documento via PyMuPDF (path ou bytes);
    - expõe page_count;
    - rasteriza páginas com cache simples de Pixmaps.
    """

    def __init__(self, *, pdf_bytes: Optional[bytes] = None, pdf_path: Optional[str] = None) -> None:
        self._pdf_bytes = pdf_bytes
        self._pdf_path = pdf_path
        self._doc = self._open_document()
        self._cache: Dict[Tuple[int, float], RasterResult] = {}

    # --- Recursos -----------------------------------------------------------
    def _open_document(self):
        if fitz is None:
            return None
        try:
            if self._pdf_bytes is not None:
                return fitz.open(stream=self._pdf_bytes, filetype="pdf")
            if self._pdf_path is not None:
                return fitz.open(self._pdf_path)
        except Exception:
            return None
        return None

    def close(self) -> None:
        try:
            if self._doc is not None:
                self._doc.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar documento PDF: %s", exc)

    # --- Atributos auxiliares -----------------------------------------------
    @property
    def page_count(self) -> int:
        if self._doc is None:
            return 1
        try:
            return int(self._doc.page_count)
        except Exception:
            return 1

    def get_page_sizes(self) -> List[Tuple[int, int]]:
        if self._doc is None:
            return [(800, 1100)]
        sizes: List[Tuple[int, int]] = []
        try:
            for p in self._doc:
                sizes.append((int(p.rect.width), int(p.rect.height)))
        except Exception:
            sizes = [(800, 1100)]
        return sizes or [(800, 1100)]

    def get_text_buffer(self) -> List[str]:
        if self._doc is None:
            return ["Texto indisponível (PyMuPDF não detectado)."]
        try:
            buf = [p.get_text("text") for p in self._doc]
        except Exception:
            buf = []
        safe: List[str] = []
        for t in buf:
            if isinstance(t, (bytes, bytearray)):
                safe.append(t.decode("utf-8", "ignore"))
            elif t is None:
                safe.append("")
            else:
                safe.append(str(t))
        return safe or ["Texto indisponível."]

    # --- Raster -------------------------------------------------------------
    def get_page_pixmap(self, page_index: int, zoom: float) -> Optional[RasterResult]:
        if self._doc is None or fitz is None:
            return None

        key = (page_index, zoom)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        try:
            page = self._doc.load_page(page_index)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
        except Exception:
            return None

        result = RasterResult(
            page_index=page_index,
            zoom=zoom,
            pixmap=pix,
            width=pix.width,
            height=pix.height,
        )
        self._cache[key] = result
        return result
