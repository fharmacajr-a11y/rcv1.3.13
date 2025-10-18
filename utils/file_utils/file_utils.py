from __future__ import annotations
from config.paths import CLOUD_ONLY

# utils/file_utils.py

from pathlib import Path
import os
import re
import shutil
from typing import Optional, Any, Iterable, Mapping, Union
from datetime import datetime

# Classificador de documentos (mantém como já estava no projeto)
from core import classify_document

# Carregador da configuração (SUBPASTAS / EXTRAS_VISIBLE)


# =============================================================================
# Utilidades básicas de arquivo
# =============================================================================
def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    if not CLOUD_ONLY:
        p.mkdir(parents=True, exist_ok=True)
    return p


def safe_copy(src: str | Path, dst: str | Path) -> None:
    src, dst = Path(src), Path(dst)
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)


def open_folder(p: str | Path) -> None:
    """Abre pasta no explorador de arquivos (bloqueado em modo Cloud-Only)."""
    from utils.helpers import check_cloud_only_block

    if check_cloud_only_block("Abrir pasta"):
        return
    os.startfile(str(Path(p)))


# =============================================================================
# Leitura de PDF (vários backends + OCR fallback)
# =============================================================================
# Backend unificado: pypdf (recomendado) com fallback para PyPDF2 (deprecated)
# Referência: PyPDF2 está deprecated, pypdf é o sucessor oficial
# https://pypi.org/project/pypdf/
pdfmod: Any
try:
    import pypdf as pdfmod  # Prioridade: pypdf (recomendado)
except Exception:
    try:
        import PyPDF2 as pdfmod  # type: ignore[no-redef]  # Fallback: PyPDF2 (deprecated)
    except Exception:
        pdfmod = None


def _read_pdf_text_pypdf(p: Path) -> Optional[str]:
    if pdfmod is None:
        return None
    try:
        reader = pdfmod.PdfReader(str(p))  # type: ignore[attr-defined]
        parts: list[str] = []
        for page in getattr(reader, "pages", []):
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


def _read_pdf_text_pdfminer(p: Path) -> Optional[str]:
    try:
        from pdfminer.high_level import extract_text

        res = (extract_text(str(p)) or "").strip()
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
            for i, page in enumerate(doc):
                if i >= max_pages:
                    break
                # tenta texto nativo primeiro
                t = page.get_text() or ""
                if t.strip():
                    texts.append(t)
                    continue
                # fallback OCR
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
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None

    for fn in (_read_pdf_text_pypdf, _read_pdf_text_pdfminer, _read_pdf_text_pymupdf):
        txt = fn(p)
        if txt:
            return txt

    return _ocr_pdf_with_pymupdf(p)


# =============================================================================
# Busca robusta de Cartão CNPJ (pelo CONTEÚDO)
# =============================================================================
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
    """
    Procura o PDF de Cartão CNPJ dentro da pasta pelo CONTEÚDO.
    1) Varre todos os PDFs <= max_mb MB.
    2) Para cada PDF, extrai texto e verifica se parece um Cartão CNPJ.
    3) Retorna o primeiro que bater pelo conteúdo.
    """
    base = Path(base)
    if not base.exists():
        return None

    limit = max(1, max_mb) * 1024 * 1024
    try:
        pdfs = [
            p for p in base.rglob("*.pdf") if p.is_file() and p.stat().st_size <= limit
        ]
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


# =============================================================================
# Listagem + classificação integrada
# =============================================================================
def list_and_classify_pdfs(base: str | Path) -> list[dict]:
    """
    Lista todos os PDFs de uma pasta e retorna metadados classificados.
    Cada item é um dict com:
      {"path": "...", "type": "...", "meta": {...}}
    """
    docs: list[dict] = []
    base = Path(base)
    for p in base.rglob("*.pdf"):
        if not p.is_file():
            continue
        info = classify_document(str(p))
        docs.append({"path": str(p), **info})
    return docs


# =============================================================================
# Subpastas – suporte a ÁRVORE (strings com "/" e/ou objetos {name, children})
# =============================================================================
SubSpec = Union[str, Mapping[str, object]]
SubSpecList = Iterable[SubSpec]


def _split_pathlike(s: str) -> list[str]:
    """Quebra 'ANVISA/ALTERACAO_DE_PORTE' em ['ANVISA','ALTERACAO_DE_PORTE']."""
    return [seg for seg in s.replace("\\", "/").split("/") if seg.strip()]


def _spec_name(spec: SubSpec) -> str:
    if isinstance(spec, str):
        return spec
    return str(spec.get("name") or spec.get("folder") or spec.get("dir") or "")


def _spec_children(spec: SubSpec) -> list[SubSpec]:
    if isinstance(spec, str):
        return []
    kids = spec.get("children") or spec.get("sub") or spec.get("dirs") or []
    return list(kids) if isinstance(kids, (list, tuple)) else []


def ensure_subtree(base: str | Path, spec: SubSpecList) -> None:
    """
    Cria recursivamente a árvore em 'base'.
    Exemplos de spec aceitos:
      - ["DOCS", "ANEXOS"]
      - ["ANVISA/ALTERACAO_DE_PORTE", "ANVISA/RESPONSAVEL_TECNICO"]
      - [{"name":"ANVISA","children":["ALTERACAO_DE_PORTE",
                                     {"name":"RESPONSAVEL_LEGAL","children":["PROTOCOLOS","DOCS"]}]}]
    """
    base = Path(base)
    if not CLOUD_ONLY:
        base.mkdir(parents=True, exist_ok=True)

    for item in spec or []:
        # Caso string: pode ter barras (cria caminho completo)
        if isinstance(item, str):
            parts = _split_pathlike(item)
            if not parts:
                continue
            p = base
            for seg in parts:
                p = p / seg
                if not CLOUD_ONLY:
                    p.mkdir(parents=True, exist_ok=True)
            continue

        # Caso dict: cria <base>/<name> e desce nos children
        name = _spec_name(item)
        if not name:
            continue
        p = base / name
        if not CLOUD_ONLY:
            p.mkdir(parents=True, exist_ok=True)
        children = _spec_children(item)
        if children:
            ensure_subtree(p, children)


from typing import Iterable


def ensure_subpastas(base: str, nomes: Iterable[str] | None = None) -> bool:
    """
    Garante a criação das subpastas em 'base'.
    - Se 'nomes' vier, usa essa lista (pode conter caminhos com '/').
    - Caso contrário, carrega do YAML (utils.subpastas_config.load_subpastas_config),
      aceitando tanto o retorno novo (subpastas, extras) quanto o antigo
      (top_level, all_paths, extras).
    """
    if not CLOUD_ONLY:
        os.makedirs(base, exist_ok=True)

    final: list[str] = []

    if nomes is not None:
        # normaliza lista recebida
        final = [str(n).replace("\\", "/").strip("/") for n in nomes if str(n).strip()]
    else:
        # carrega do YAML, aceitando 2 ou 3 valores de retorno
        try:
            from utils.subpastas_config import load_subpastas_config

            ret = load_subpastas_config()

            subs: list[str] = []
            extras: list[str] = []

            if isinstance(ret, tuple):
                if len(ret) == 2:
                    subs, extras = ret
                elif len(ret) == 3:
                    # compat com versões antigas
                    _top_level, all_paths, extras = ret
                    subs = all_paths
            final = [*subs, *extras]
        except Exception:
            final = []

    # Fallback mínimo se nada veio do YAML
    if not final:
        for n in ("DOCS", "ANEXOS"):
            try:
                if not CLOUD_ONLY:
                    os.makedirs(os.path.join(base, n), exist_ok=True)
            except Exception:
                pass
        return True

    # Cria cada caminho (suporta subníveis: "PAI/ FILHO / ...")
    for rel in final:
        rel = str(rel).replace("\\", "/").strip("/")
        if not rel:
            continue
        try:
            if not CLOUD_ONLY:
                os.makedirs(os.path.join(base, rel), exist_ok=True)
        except Exception:
            pass

    return True


# =============================================================================
# Marcador de pasta do cliente (.rc_client_id)
# =============================================================================
MARKER_NAME = ".rc_client_id"  # padrão único do app


def write_marker(pasta: str, cliente_id: int) -> str:
    """Cria/atualiza o marcador `.rc_client_id` com o ID (conteúdo cru)."""
    if not CLOUD_ONLY:
        os.makedirs(pasta, exist_ok=True)
    marker = os.path.join(pasta, MARKER_NAME)
    with open(marker, "w", encoding="utf-8") as f:
        f.write(str(cliente_id).strip() + "\n")
    # mtime = agora, serve como "UPDATED"
    os.utime(marker, None)
    return marker


def read_marker_id(pasta: str) -> str | None:
    """Lê o ID do cliente da pasta. Aceita formato novo e legado."""
    # Formato novo
    marker_new = os.path.join(pasta, MARKER_NAME)
    if os.path.exists(marker_new):
        try:
            with open(marker_new, "r", encoding="utf-8") as f:
                val = f.read().strip()
            return val or None
        except Exception:
            pass

    # Formato legado: cliente_{id}.marker com conteúdo "ID=..."
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
    """Se existir marcador legado, converte para o formato novo e remove os antigos."""
    client_id = read_marker_id(pasta)
    if not client_id:
        return None
    marker_new = os.path.join(pasta, MARKER_NAME)
    if not os.path.exists(marker_new):
        with open(marker_new, "w", encoding="utf-8") as f:
            f.write(client_id + "\n")
    # tentar remover marcadores antigos
    for fname in os.listdir(pasta):
        if fname.startswith("cliente_") and fname.endswith(".marker"):
            try:
                os.remove(os.path.join(pasta, fname))
            except OSError:
                pass
    os.utime(marker_new, None)
    return marker_new


def get_marker_updated_at(pasta: str) -> datetime | None:
    """Retorna o mtime do marcador como datetime (para exibir 'Atualizado em')."""
    marker = os.path.join(pasta, MARKER_NAME)
    if not os.path.exists(marker):
        return None
    return datetime.fromtimestamp(os.path.getmtime(marker))


def format_datetime(dt_obj) -> str:
    """Formata datas no padrão usado no app."""
    if not dt_obj:
        return ""
    if isinstance(dt_obj, str):
        try:
            dt_obj = datetime.fromisoformat(dt_obj)
        except Exception:
            return dt_obj
    return dt_obj.strftime("%d/%m/%Y - %H:%M:%S")


__all__ = [
    # utils
    "ensure_dir",
    "safe_copy",
    "open_folder",
    # pdf
    "read_pdf_text",
    "find_cartao_cnpj_pdf",
    "list_and_classify_pdfs",
    # subpastas
    "ensure_subtree",
    "ensure_subpastas",
    # marcador
    "write_marker",
    "read_marker_id",
    "migrate_legacy_marker",
    "get_marker_updated_at",
    "format_datetime",
]
