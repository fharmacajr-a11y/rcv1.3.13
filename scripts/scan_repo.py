# -*- coding: utf-8 -*-
"""
Gera ajuda/SCAN_REPORT.json com:
- contagem de dirs/arquivos
- tamanho por pasta de 1º nível
- top extensões (tamanho e contagem)
- LOC de .py
- imports detectados (aprox.)
- resumo do spec (datas/hiddenimports)
Ignora: .venv, dist, build/__pycache__, ajuda
"""
import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ajuda" / "SCAN_REPORT.json"
SKIP_DIRS = {
    ".venv",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".git",
    "ajuda",
}


def is_skipped(p: Path) -> bool:
    parts = set(p.parts)
    return bool(parts & SKIP_DIRS)


total_files = 0
total_dirs = 0
ext_stats = {}  # {".py": {"count":N,"bytes":M}}
top_dirs = {}  # {"core": {"count":N,"bytes":M}, ...}
py_loc = 0
imports = set()

for dirpath, dirnames, filenames in os.walk(ROOT):
    d = Path(dirpath)
    # prune pastas ignoradas
    dirnames[:] = [n for n in dirnames if not is_skipped(d / n)]
    if is_skipped(d):
        continue

    total_dirs += 1
    # pasta de 1º nível
    rel = d.relative_to(ROOT)
    first = rel.parts[0] if rel.parts else ""
    if first:
        top_dirs.setdefault(first, {"count": 0, "bytes": 0})

    for fn in filenames:
        p = d / fn
        if is_skipped(p):
            continue
        try:
            size = p.stat().st_size
        except Exception:
            size = 0
        total_files += 1
        if first:
            td = top_dirs[first]
            td["count"] += 1
            td["bytes"] += size

        ext = p.suffix.lower()
        st = ext_stats.setdefault(ext or "<noext>", {"count": 0, "bytes": 0})
        st["count"] += 1
        st["bytes"] += size

        if ext == ".py":
            # LOC simples
            try:
                with p.open("r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                py_loc += txt.count("\n") + 1
                # imports (aprox.)
                for m in re.finditer(
                    r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_\.]*)", txt, re.M
                ):
                    name = m.group(1).split(".")[0]
                    if name not in {"__future__"}:
                        imports.add(name)
            except Exception:
                pass

# spec summary (se existir)
spec_summary = {"exists": False, "datas": False, "hiddenimports": False}
spec = ROOT / "build" / "rc_gestor.spec"
if spec.exists():
    spec_summary["exists"] = True
    try:
        txt = spec.read_text(encoding="utf-8", errors="ignore")
        spec_summary["datas"] = "datas=" in txt
        spec_summary["hiddenimports"] = "hiddenimports" in txt
    except Exception:
        pass

report = {
    "root": str(ROOT),
    "stats": {
        "dirs": total_dirs,
        "files": total_files,
        "py_loc": py_loc,
    },
    "top_dirs": sorted(
        [{"name": k, **v} for k, v in top_dirs.items()],
        key=lambda x: (-x["bytes"], x["name"]),
    ),
    "extensions": sorted(
        [{"ext": k, **v} for k, v in ext_stats.items()],
        key=lambda x: (-x["bytes"], x["ext"]),
    )[:25],
    "imports_detected": sorted(imports),
    "spec_summary": spec_summary,
}

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OK -> {OUT}")
