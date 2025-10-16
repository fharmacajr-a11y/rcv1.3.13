import fitz  # PyMuPDF
import logging

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
    """Lê até max_pages do PDF, com fallback para PDFs problemáticos."""
    try:
        doc = fitz.open(path)
    except Exception as e:
        logger.warning(f"PDF inválido ou criptografado: {path} ({e})")
        return ""

    texts = []
    try:
        total = min(max_pages, getattr(doc, "page_count", 0))
        for i in range(total):
            try:
                page = doc.load_page(i)
                txt = page.get_text("text")
                if not txt:
                    raw = page.get_text("rawdict")
                    txt = _flatten_rawdict(raw)
                if not isinstance(txt, str):
                    txt = str(txt)
                texts.append(txt)
            except Exception as e:
                logger.warning(f"Falha ao ler página {i} em {path}: {e}")
                continue
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return "\n".join(texts)
