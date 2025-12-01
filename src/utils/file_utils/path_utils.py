from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Iterable, Mapping

from src.config.paths import CLOUD_ONLY

log = logging.getLogger(__name__)

SubSpec = str | Mapping[str, object]
SubSpecList = Iterable[SubSpec]

__all__ = [
    "ensure_dir",
    "safe_copy",
    "open_folder",
    "ensure_subtree",
    "ensure_subpastas",
]


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
    from src.utils.helpers import check_cloud_only_block

    if check_cloud_only_block("Abrir pasta"):
        return
    if not p:
        return
    try:
        os.startfile(str(Path(p)))  # nosec B606 - caminho local controlado pela aplicação
    except OSError as exc:
        log.warning("Falha ao abrir caminho %s: %s", p, exc)


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
        if isinstance(item, str):
            parts: list[str] = _split_pathlike(item)
            if not parts:
                continue
            p: Path = base
            for seg in parts:
                p = p / seg
                if not CLOUD_ONLY:
                    p.mkdir(parents=True, exist_ok=True)
            continue

        name: str = _spec_name(item)
        if not name:
            continue
        p: Path = base / name
        if not CLOUD_ONLY:
            p.mkdir(parents=True, exist_ok=True)
        children = _spec_children(item)
        if children:
            ensure_subtree(p, children)


def ensure_subpastas(base: str, nomes: Iterable[str] | None = None, *, subpastas: Iterable[str] | None = None) -> bool:
    """
    Garante a criação das subpastas em 'base'.

    Args:
        base: Diretório base
        nomes: Lista de nomes de subpastas (novo parâmetro padrão)
        subpastas: Alias para 'nomes' (mantido para compatibilidade)
    """
    # Compat: se vier 'subpastas' e 'nomes' não vier, usa 'subpastas'
    if subpastas is not None and nomes is None:
        nomes = subpastas

    if not CLOUD_ONLY:
        os.makedirs(base, exist_ok=True)

    final: list[str] = []

    if nomes is not None:
        final = [str(n).replace("\\", "/").strip("/") for n in nomes if str(n).strip()]
    else:
        try:
            from src.utils.subpastas_config import load_subpastas_config

            ret = load_subpastas_config()

            subs: list[str] = []
            extras: list[str] = []

            if isinstance(ret, tuple):
                if len(ret) == 2:
                    subs, extras = ret
                elif len(ret) == 3:
                    _top_level, all_paths, extras = ret  # pyright: ignore[reportGeneralTypeIssues]
                    subs = all_paths
            final = [*subs, *extras]
        except Exception:
            log.debug("Falha ao carregar subpastas_config; usando vazio", exc_info=True)
            final = []

    if not final:
        for n in ("DOCS", "ANEXOS"):
            try:
                if not CLOUD_ONLY:
                    os.makedirs(os.path.join(base, n), exist_ok=True)
            except Exception:
                log.debug("Falha ao criar subpasta padrão %s em %s", n, base, exc_info=True)
        return True

    for rel in final:
        rel = str(rel).replace("\\", "/").strip("/")
        if not rel:
            continue
        try:
            if not CLOUD_ONLY:
                os.makedirs(os.path.join(base, rel), exist_ok=True)
        except Exception:
            log.debug("Falha ao criar subpasta %s em %s", rel, base, exc_info=True)

    return True
