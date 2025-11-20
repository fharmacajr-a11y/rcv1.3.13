# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config.paths import CLOUD_ONLY
from src.core import classify_document

__all__ = [
    "read_pdf_text",
    "find_cartao_cnpj_pdf",
    "list_and_classify_pdfs",
    "write_marker",
    "read_marker_id",
    "migrate_legacy_marker",
    "get_marker_updated_at",
    "format_datetime",
]

try:
    from pypdf import PdfReader

    pdfmod = True
except ImportError:
    pdfmod = False


def _read_pdf_text_pypdf(p: Path) -> Optional[str]:
    """Extrai texto de PDF usando pypdf."""
    if not pdfmod:
        return None
    try:
        reader = PdfReader(str(p))
        parts: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                parts.append(t)
        res = "\n".join(parts).strip()
        return res or None
    except Exception:
        return None


def _read_pdf_text_pymupdf(p: Path) -> Optional[str]:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return None
    try:
        parts: list[str] = []
        with fitz.open(str(p)) as doc:
            for page in doc:
                t = page.get_text() or ""
                if t.strip():
                    parts.append(t)
        res = "\n".join(parts).strip()
        return res or None
    except Exception:
        return None


def _ocr_pdf_with_pymupdf(p: Path, max_pages: int = 5, dpi: int = 200) -> Optional[str]:
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except Exception:
        return None

    try:
        texts: list[str] = []
        with fitz.open(str(p)) as doc:
            for i, page in enumerate(doc):  # pyright: ignore[reportArgumentType]
                if i >= max_pages:
                    break
                t = page.get_text() or ""
                if t.strip():
                    texts.append(t)
                    continue
                pm = page.get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                t = pytesseract.image_to_string(img, lang="por+eng")
                if t and t.strip():
                    texts.append(t)
        res = "\n".join(texts).strip()
        return res or None
    except Exception:
        return None


def read_pdf_text(path: str | Path) -> Optional[str]:
    """
    Extrai texto de PDF usando estratégia de fallback em cascata.
    
    Ordem de tentativa (otimizada pós-Sprint P1):
    1. PyMuPDF (fitz) - Mais robusto, rápido e completo
    2. pypdf - Fallback para PDFs simples
    3. OCR com PyMuPDF + Tesseract - Para PDFs escaneados
    
    Nota de Segurança (Sprint P1-SEG/DEP):
    - pdfminer-six REMOVIDO (CVE GHSA-f83h-ghpp-7wcc, CVSS 7.8 HIGH)
    - Eliminação completa do vetor de ataque de desserialização pickle
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None

    # Ordem otimizada: PyMuPDF (primário) → pypdf (fallback) → OCR
    for fn in (_read_pdf_text_pymupdf, _read_pdf_text_pypdf):
        txt = fn(p)
        if txt:
            return txt

    # Último recurso: OCR para PDFs escaneados
    return _ocr_pdf_with_pymupdf(p)


_CNPJ_RX = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", re.IGNORECASE)

_CARTAO_KWS = [
    "cadastro nacional da pessoa jurídica",
    "comprovante de inscrição",
    "situação cadastral",
    "cartão cnpj",
    "cartao cnpj",
    "nome empresarial",
]


def _looks_like_cartao_cnpj(text: str) -> bool:
    if not text:
        return False
    t_low = text.lower()
    has_cnpj = bool(_CNPJ_RX.search(text))
    has_kw = any(kw in t_low for kw in _CARTAO_KWS)
    return has_cnpj and has_kw


def find_cartao_cnpj_pdf(base: str | Path, max_mb: int = 10) -> Optional[Path]:
    base = Path(base)
    if not base.exists():
        return None

    limit = max(1, max_mb) * 1024 * 1024
    try:
        pdfs = [p for p in base.rglob("*.pdf") if p.is_file() and p.stat().st_size <= limit]
    except Exception:
        pdfs = []
    if not pdfs:
        return None

    for p in pdfs:
        try:
            text = read_pdf_text(p)
        except Exception:
            text = None
        if text and _looks_like_cartao_cnpj(text):
            return p

    return None


def list_and_classify_pdfs(base: str | Path) -> list[dict]:
    docs: list[dict] = []
    base = Path(base)
    for p in base.rglob("*.pdf"):
        if not p.is_file():
            continue
        info = classify_document(str(p))
        docs.append({"path": str(p), **info})
    return docs


MARKER_NAME = ".rc_client_id"


def write_marker(pasta: str, cliente_id: int) -> str:
    if not CLOUD_ONLY:
        os.makedirs(pasta, exist_ok=True)
    marker = os.path.join(pasta, MARKER_NAME)
    with open(marker, "w", encoding="utf-8") as f:
        f.write(str(cliente_id).strip() + "\n")
    os.utime(marker, None)
    return marker


def read_marker_id(pasta: str) -> str | None:
    marker_new = os.path.join(pasta, MARKER_NAME)
    if os.path.exists(marker_new):
        try:
            with open(marker_new, "r", encoding="utf-8") as f:
                val = f.read().strip()
            return val or None
        except Exception:
            pass

    try:
        for fname in os.listdir(pasta):
            if fname.startswith("cliente_") and fname.endswith(".marker"):
                with open(os.path.join(pasta, fname), "r", encoding="utf-8") as f:
                    txt = f.read().strip()
                if txt.startswith("ID="):
                    return txt.split("=", 1)[1].strip() or None
    except FileNotFoundError:
        return None

    return None


def migrate_legacy_marker(pasta: str) -> str | None:
    client_id = read_marker_id(pasta)
    if not client_id:
        return None
    marker_new = os.path.join(pasta, MARKER_NAME)
    if not os.path.exists(marker_new):
        with open(marker_new, "w", encoding="utf-8") as f:
            f.write(client_id + "\n")
    for fname in os.listdir(pasta):
        if fname.startswith("cliente_") and fname.endswith(".marker"):
            try:
                os.remove(os.path.join(pasta, fname))
            except OSError:
                pass
    os.utime(marker_new, None)
    return marker_new


def get_marker_updated_at(pasta: str) -> datetime | None:
    marker = os.path.join(pasta, MARKER_NAME)
    if not os.path.exists(marker):
        return None
    return datetime.fromtimestamp(os.path.getmtime(marker))


def format_datetime(dt_obj) -> str:
    if not dt_obj:
        return ""
    if isinstance(dt_obj, str):
        try:
            dt_obj = datetime.fromisoformat(dt_obj)
        except Exception:
            return dt_obj
    return dt_obj.strftime("%d/%m/%Y - %H:%M:%S")
