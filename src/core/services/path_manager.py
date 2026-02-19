# core/services/path_manager.py
from __future__ import annotations

import os
import shutil
import logging
from dataclasses import dataclass
from typing import Optional, Iterable, Tuple

try:
    # seu resolver já existente (sólido)
    from core.services.path_resolver import resolve_unique_path
except Exception:  # fallback muito defensivo (não deve ocorrer)

    def resolve_unique_path(pk: int, prefer: Optional[str] = None):
        return None, None  # type: ignore[misc]


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PathResolution:
    """Resultado consolidado da resolução de caminhos para um cliente."""

    pk: int
    active_path: Optional[str]
    trash_path: Optional[str]
    location: Optional[str]  # 'active' | 'trash' | None
    has_conflict: bool  # true quando há pastas nas duas localizações
    marker_id: Optional[str] = None
    slug: Optional[str] = None


# -------------------------- resolução --------------------------


def resolve_paths(pk: int) -> PathResolution:
    """
    Resolve caminhos do cliente tanto em 'active' quanto em 'trash' e detecta conflito.
    Usa seu path_resolver como fonte da verdade.
    """
    try:
        act_path, act_loc = resolve_unique_path(pk, prefer="active")
    except Exception:
        act_path, act_loc = None, None

    try:
        tr_path, tr_loc = resolve_unique_path(pk, prefer="trash")
    except Exception:
        tr_path, tr_loc = None, None

    location = act_loc or tr_loc
    has_conflict = bool(act_path and tr_path and os.path.abspath(act_path) != os.path.abspath(tr_path))

    # Tenta ler marker do que estiver disponível
    marker = read_marker_id(act_path) if act_path else (read_marker_id(tr_path) if tr_path else None)

    # slug = nome da pasta (heurística útil para UI/log)
    slug = None
    for p in (act_path, tr_path):
        if p:
            slug = os.path.basename(os.path.normpath(p))
            break

    return PathResolution(
        pk=pk,
        active_path=act_path,
        trash_path=tr_path,
        location=location,
        has_conflict=has_conflict,
        marker_id=marker,
        slug=slug,
    )


# -------------------------- pré-checagens para mover/restaurar --------------------------


def preflight_move_to_trash(pk: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Verifica se há uma pasta ativa para mover.
    Retorna (src, motivo_erro). Se src for None, motivo_erro explica.
    """
    r = resolve_paths(pk)
    if r.active_path and os.path.isdir(r.active_path):
        return r.active_path, None
    return None, "Pasta ativa não encontrada para este cliente."


def preflight_restore_from_trash(pk: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Verifica se há uma pasta na lixeira para restaurar.
    Retorna (src, motivo_erro). Se src for None, motivo_erro explica.
    """
    r = resolve_paths(pk)
    if r.trash_path and os.path.isdir(r.trash_path):
        return r.trash_path, None
    return None, "Pasta na Lixeira não encontrada para este cliente."


# -------------------------- helpers seguros de FS --------------------------


def ensure_dir(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        log.exception("ensure_dir: falha ao criar '%s'", path)
        return False


def safe_move_dir(src: str, dst: str, overwrite: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Move diretório com segurança.
    - Se destino existe e overwrite=False, aborta com mensagem.
    - Cria diretório pai do destino se necessário.
    """
    try:
        if not os.path.isdir(src):
            return False, f"Origem não é um diretório: {src}"
        parent = os.path.dirname(os.path.normpath(dst))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        if os.path.exists(dst):
            if not overwrite:
                return False, f"Destino já existe: {dst}"
        shutil.move(src, dst)
        return True, None
    except Exception as e:
        log.exception("safe_move_dir: falha ao mover '%s' -> '%s'", src, dst)
        return False, str(e)


def ensure_subfolders(base_dir: str, names: Iterable[str]) -> Tuple[list[str], list[Tuple[str, str]]]:
    """
    Garante subpastas em base_dir.
    Retorna: (criadas, falhas[(nome, motivo)]).
    """
    created, failures = [], []
    for name in names or []:
        p = os.path.join(base_dir, name)
        try:
            os.makedirs(p, exist_ok=True)
            created.append(name)
        except Exception as e:
            failures.append((name, str(e)))
            log.exception("ensure_subfolders: falha ao criar '%s'", p)
    return created, failures


# -------------------------- markers --------------------------

# Conjunto de nomes prováveis para marker; cobrimos várias variações.
_MARKER_CANDIDATES = (
    ".cliente_id",
    ".marker_id",
    ".id",
    "CLIENTE_ID",
    "MARKER.ID",
    "CLIENTE.ID",
    ".marker",
)


def read_marker_id(path: Optional[str]) -> Optional[str]:
    """
    Lê o marker do cliente (se existir). Suporta múltiplos nomes de arquivo.
    Retorna o conteúdo stripado ou None.
    """
    if not path:
        return None
    try:
        for fname in _MARKER_CANDIDATES:
            fpath = os.path.join(path, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    return (f.read() or "").strip()
    except Exception:
        log.exception("read_marker_id: falha ao ler marker em '%s'", path)
    return None


def write_marker_id(path: str, marker_value: str, filename: str = ".cliente_id") -> bool:
    """
    Escreve (ou sobrescreve) o marker do cliente no diretório informado.
    Por padrão, usa '.cliente_id' — parâmetro ajustável se você já padronizou outro nome.
    """
    try:
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
        fpath = os.path.join(path, filename)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(str(marker_value).strip())
        return True
    except Exception:
        log.exception("write_marker_id: falha ao escrever marker em '%s'", path)
        return False


# -------------------------- utilidades diversas --------------------------


def slug_from_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        return os.path.basename(os.path.normpath(path))
    except Exception:
        return None
