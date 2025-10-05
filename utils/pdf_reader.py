# utils/pdf_reader.py
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)
log = logger

def _flatten_rawdict(raw) -> str:
    try:
        blocks = raw.get("blocks", []) if isinstance(raw, dict) else []
        parts = []
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    t = span.get("text", "")
                    if isinstance(t, str):
                        parts.append(t)
        return "\n".join(parts)
    except Exception as e:
        logger.warning(f"Falha ao converter rawdict: {e}")
        try:
            return str(raw)
        except Exception:
            return ""

def read_pdf_text(path: str, max_pages: int = 3) -> str:
    """Lê até max_pages do PDF (default=3) com fallback para 'rawdict' quando necessário."""
    try:
        with fitz.open(path) as doc:
            # PyMuPDF: doc.needs_pass -> True se cifrado e sem senha
            if getattr(doc, "needs_pass", False):
                logger.warning(f"PDF criptografado sem senha: {path}")
                return ""

            total_pages = getattr(doc, "page_count", 0)
            if total_pages <= 0:
                return ""

            limit = total_pages if (max_pages is None or max_pages <= 0) else min(max_pages, total_pages)
            texts = []
            for i in range(limit):
                try:
                    page = doc.load_page(i)
                    txt = page.get_text("text") or ""
                    if not txt.strip():
                        raw = page.get_text("rawdict")
                        txt = _flatten_rawdict(raw)
                    if not isinstance(txt, str):
                        txt = str(txt)
                    texts.append(txt)
                except Exception as e:
                    logger.warning(f"Falha ao ler página {i} em {path}: {e}")
                    continue
            return "\n".join(texts)
    except Exception as e:
        logger.warning(f"PDF inválido ou erro ao abrir: {path} ({e})")
        return ""
