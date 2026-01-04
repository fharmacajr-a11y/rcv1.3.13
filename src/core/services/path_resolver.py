# core/services/path_resolver.py
"""
Resolução de caminhos de clientes no sistema de arquivos.

Fornece funções para localizar pastas de clientes usando:
- Marcadores de ID (.rcid)
- Slugs gerados a partir de dados do cliente (fallback)

Suporta busca em pastas ativas (DOCS_DIR) e lixeira (TRASH_DIR).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Literal, Optional, Tuple

from src.core.app_utils import safe_base_from_fields
from src.config.paths import DOCS_DIR
from src.core.db_manager import get_cliente_by_id
from src.utils.file_utils import read_marker_id
from src.utils.paths import PathLikeStr, ensure_str_path

if TYPE_CHECKING:
    import sqlite3

TRASH_DIR = os.path.join(DOCS_DIR, "_LIXEIRA")


def _limited_walk(base: str, max_depth: int = 2) -> Iterator[Tuple[str, list[str], list[str]]]:
    """
    Walk limitado por profundidade.

    Args:
        base: Diretório raiz para percorrer
        max_depth: Profundidade máxima de recursão (padrão: 2)

    Yields:
        Tuplas (root, dirs, files) como os.walk, mas limitado por profundidade
    """
    base_sep = base.count(os.sep)
    for root, dirs, files in os.walk(base):
        if root.count(os.sep) - base_sep >= max_depth:
            dirs[:] = []
        yield root, dirs, files


@dataclass
class ResolveResult:
    """Resultado da resolução de caminho de cliente."""

    pk: int
    active: Optional[str] = None  # Caminho na pasta ativa
    trash: Optional[str] = None  # Caminho na lixeira
    slug: Optional[str] = None  # Slug gerado a partir dos dados do cliente


def _candidate_by_slug(pk: int) -> Optional[str]:
    """
    Gera slug candidato a partir dos dados do cliente no banco.

    Args:
        pk: ID do cliente

    Returns:
        Slug gerado (numero_cnpj_razao) ou None se cliente não encontrado
    """
    try:
        cliente = get_cliente_by_id(pk)
        row = (cliente.numero, cliente.cnpj, cliente.razao_social) if cliente else None
    except Exception:
        row = None

    if not row:
        return None

    numero, cnpj, razao = row
    slug = safe_base_from_fields(cnpj or "", numero or "", razao or "", pk)
    return slug


def _find_by_marker(root: PathLikeStr, pk: int, *, skip_names: set[str] | None = None) -> Optional[str]:
    """
    Busca pasta por marcador de ID (.rcid).

    Args:
        root: Diretório raiz onde procurar
        pk: ID do cliente a localizar
        skip_names: Nomes de pastas a ignorar (ex: {"_LIXEIRA"})

    Returns:
        Caminho da pasta encontrada ou None
    """
    # Normalize path-like to str (PEP 519)
    root_str = ensure_str_path(root)
    if not os.path.isdir(root_str):
        return None

    if skip_names is None:
        skip_names = set()

    for name in os.listdir(root_str):
        if name in skip_names:
            continue

        candidate_path = os.path.join(root_str, name)
        if not os.path.isdir(candidate_path):
            continue

        try:
            marker_id = read_marker_id(candidate_path)
        except Exception:
            marker_id = None

        if marker_id and str(marker_id) == str(pk):
            return candidate_path

    return None


def resolve_cliente_path(pk: int, *, prefer: Literal["active", "trash", "both"] = "both") -> ResolveResult:
    """
    Resolve o caminho real (pasta) de um cliente pelo PK.

    Estratégia de busca:
      1) Tenta localizar por marcador (.rcid) em pastas ativas e lixeira
      2) Fallback: tenta por slug (safe_base_from_fields) se marcador não existir

    Args:
        pk: ID do cliente
        prefer: Preferência de localização (não utilizado atualmente, reservado)

    Returns:
        ResolveResult com caminhos encontrados (ou None se não localizado)
    """
    res = ResolveResult(pk=pk)

    # 1) Busca por marcador (estratégia primária)
    active_path = _find_by_marker(DOCS_DIR, pk, skip_names={"_LIXEIRA"})
    trash_path = _find_by_marker(TRASH_DIR, pk)

    # 2) Fallback: busca por slug (para pastas migradas ou sem marcador)
    slug = _candidate_by_slug(pk)
    res.slug = slug

    if not active_path and slug:
        candidate = os.path.join(DOCS_DIR, slug)
        if os.path.isdir(candidate):
            active_path = candidate

    if not trash_path and slug:
        candidate = os.path.join(TRASH_DIR, slug)
        if os.path.isdir(candidate):
            trash_path = candidate

    res.active = active_path
    res.trash = trash_path
    return res


def resolve_unique_path(
    pk: int,
    *,
    prefer: Literal["active", "trash", "both"] = "both",
    conn: Optional[sqlite3.Connection] = None,  # noqa: ARG001 - Reservado para uso futuro
) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna um único caminho para o cliente.

    Args:
        pk: ID do cliente
        prefer: Preferência quando encontrado em múltiplos locais:
                - 'active': prioriza pasta ativa
                - 'trash': prioriza lixeira
                - 'both': prioriza ativa, fallback para trash
        conn: Conexão SQLite (reservado para uso futuro)

    Returns:
        Tupla (path, location) onde:
        - path: caminho da pasta ou None
        - location: 'active' | 'trash' | None
    """
    result = resolve_cliente_path(pk, prefer=prefer)

    if prefer == "active" and result.active:
        return result.active, "active"
    if prefer == "trash" and result.trash:
        return result.trash, "trash"

    # Modo 'both' ou fallback: prioriza active
    if result.active:
        return result.active, "active"
    if result.trash:
        return result.trash, "trash"

    return None, None
