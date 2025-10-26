from __future__ import annotations

from src.config.paths import CLOUD_ONLY

import os
import shutil
from pathlib import Path
from typing import Iterable, Mapping, Union

SubSpec = Union[str, Mapping[str, object]]
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
    os.startfile(str(Path(p)))


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
            parts = _split_pathlike(item)
            if not parts:
                continue
            p = base
            for seg in parts:
                p = p / seg
                if not CLOUD_ONLY:
                    p.mkdir(parents=True, exist_ok=True)
            continue

        name = _spec_name(item)
        if not name:
            continue
        p = base / name
        if not CLOUD_ONLY:
            p.mkdir(parents=True, exist_ok=True)
        children = _spec_children(item)
        if children:
            ensure_subtree(p, children)


def ensure_subpastas(base: str, nomes: Iterable[str] | None = None) -> bool:
    """
    Garante a criação das subpastas em 'base'.
    """
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
                    _top_level, all_paths, extras = ret
                    subs = all_paths
            final = [*subs, *extras]
        except Exception:
            final = []

    if not final:
        for n in ("DOCS", "ANEXOS"):
            try:
                if not CLOUD_ONLY:
                    os.makedirs(os.path.join(base, n), exist_ok=True)
            except Exception:
                pass
        return True

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
