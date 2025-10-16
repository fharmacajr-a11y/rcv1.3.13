
# core/services/path_resolver.py
from __future__ import annotations
import os
from core.db_manager import get_cliente_by_id

from dataclasses import dataclass
from typing import Optional, Literal, Tuple

from config.paths import DB_PATH, DOCS_DIR
from app_utils import safe_base_from_fields
from utils.file_utils import read_marker_id

TRASH_DIR = os.path.join(DOCS_DIR, "_LIXEIRA")

def _limited_walk(base: str, max_depth: int = 2):
    base_sep = base.count(os.sep)
    for root, dirs, files in os.walk(base):
        if root.count(os.sep) - base_sep >= max_depth:
            dirs[:] = []
        yield root, dirs, files


@dataclass
class ResolveResult:
    pk: int
    active: Optional[str] = None
    trash: Optional[str] = None
    slug: Optional[str] = None

def _candidate_by_slug(pk: int) -> Optional[str]:
    try:
        c = get_cliente_by_id(pk)
        row = (c.numero, c.cnpj, c.razao_social) if c else None
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if not row:
        return None

    numero, cnpj, razao = row
    base = safe_base_from_fields(cnpj or "", numero or "", razao or "", pk)
    return base

def _find_by_marker(root: str, pk: int, *, skip_names: set[str] | None = None) -> Optional[str]:
    if not os.path.isdir(root):
        return None
    if skip_names is None:
        skip_names = set()
    for name in os.listdir(root):
        if name in skip_names:
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        try:
            mid = read_marker_id(path)
        except Exception:
            mid = None
        if mid and str(mid) == str(pk):
            return path
    return None

def resolve_cliente_path(pk: int, *, prefer: Literal["active", "trash", "both"] = "both") -> ResolveResult:
    """Resolve o caminho real (pasta) de um cliente pelo PK.
    Estratégia:
      1) Tenta pelo marcador (mais confiável) no ativos e na lixeira.
      2) Tenta pelo slug (safe_base_from_fields) em ativos e lixeira.
    Retorna ResolveResult com paths (ou None).
    """
    res = ResolveResult(pk=pk)

    # 1) Por marcador
    active = _find_by_marker(DOCS_DIR, pk, skip_names={"_LIXEIRA"})
    trash = _find_by_marker(TRASH_DIR, pk)

    # 2) Por slug (caso não tenha marcador ou foi migrado)
    slug = _candidate_by_slug(pk)
    res.slug = slug
    if not active and slug:
        cand = os.path.join(DOCS_DIR, slug)
        if os.path.isdir(cand):
            active = cand
    if not trash and slug:
        cand = os.path.join(TRASH_DIR, slug)
        if os.path.isdir(cand):
            trash = cand

    res.active = active
    res.trash = trash
    return res

def resolve_unique_path(pk: int, *, prefer: Literal["active", "trash", "both"] = "both", conn: Optional[sqlite3.Connection] = None) -> Tuple[Optional[str], Optional[str]]:
    """Convenience: retorna (path, location) onde location é 'active' ou 'trash'. Se ambos existirem,
    respeita 'prefer'. Em empates, prioriza 'active'.
    """
    r = resolve_cliente_path(pk, prefer=prefer)
    if prefer == "active" and r.active:
        return r.active, "active"
    if prefer == "trash" and r.trash:
        return r.trash, "trash"
    # both / fallback
    if r.active:
        return r.active, "active"
    if r.trash:
        return r.trash, "trash"
    return None, None