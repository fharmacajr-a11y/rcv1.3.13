# utils/subpastas_config.py
from __future__ import annotations

from pathlib import Path
from typing import Tuple, List, Any
import yaml


def _flatten(node: Any, prefix: str = "") -> List[str]:
    """Achata listas/dicts do YAML para caminhos 'PAI/ FILHO / ...'."""
    items: List[str] = []

    def join(a: str, b: str) -> str:
        if not a:
            return b
        return f"{a}/{b}"

    if isinstance(node, list):
        for it in node:
            if isinstance(it, str):
                items.append(join(prefix, it))
            elif isinstance(it, dict):
                for k, v in it.items():
                    base = join(prefix, str(k))
                    if not v:
                        items.append(base)
                    else:
                        items.extend(_flatten(v, base))
    elif isinstance(node, dict):
        for k, v in node.items():
            base = join(prefix, str(k))
            if not v:
                items.append(base)
            else:
                items.extend(_flatten(v, base))

    return items


def _norm(p: str) -> str:
    return "/".join([seg for seg in str(p).replace("\\", "/").split("/") if seg])


def load_subpastas_config(
    explicit_path: str | Path | None = None,
) -> Tuple[List[str], List[str]]:
    """
    Lê subpastas.yml, achata e retorna (subpastas, extras_visiveis).
    Procura em:
      - caminho explícito (se fornecido)
      - <raiz do projeto>/subpastas.yml
      - <raiz do projeto>/config/subpastas.yml
    """
    cfg = {}
    candidates: List[Path] = []

    if explicit_path:
        candidates = [Path(explicit_path)]
    else:
        here = Path(__file__).resolve()
        root = here.parents[1]  # .../utils -> raiz do projeto
        candidates = [root / "subpastas.yml", root / "config" / "subpastas.yml"]

    for cand in candidates:
        try:
            if cand.exists():
                with cand.open("r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                break
        except Exception:
            pass

    sub_spec = cfg.get("SUBPASTAS") or []
    extras_spec = cfg.get("EXTRAS_VISIBLE") or []

    sub_list = [_norm(p) for p in _flatten(sub_spec)]
    extras_list = [_norm(p) for p in _flatten(extras_spec)]

    # remove vazios + duplicados mantendo ordem
    seen = set()
    sub_list = [p for p in sub_list if p and not (p in seen or seen.add(p))]
    seen = set()
    extras_list = [p for p in extras_list if p and not (p in seen or seen.add(p))]

    return sub_list, extras_list


MANDATORY_SUBPASTAS = ("SIFAP", "ANVISA", "FARMACIA_POPULAR", "AUDITORIA")


def get_mandatory_subpastas():
    return tuple(MANDATORY_SUBPASTAS)


def join_prefix(base: str, *parts: str) -> str:
    b = base.rstrip("/")
    mid = "/".join(p.strip("/") for p in parts if p)
    combined = f"{b}/{mid}".strip("/") if mid else b.strip("/")
    return (combined + "/") if combined else ""
