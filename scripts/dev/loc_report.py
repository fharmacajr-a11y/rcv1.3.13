# scripts/dev/loc_report.py
from __future__ import annotations
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache"}
EXTS = {".py", ".md"}


def skip_dir(p: pathlib.Path) -> bool:
    return any(s in SKIP_DIRS for s in p.parts)


def count_lines(p: pathlib.Path) -> int:
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def main() -> int:
    rows = []
    for path, _, files in os.walk(ROOT):
        d = pathlib.Path(path)
        if skip_dir(d):
            continue
        for fn in files:
            p = d / fn
            if p.suffix.lower() in EXTS:
                rows.append(
                    (str(p.relative_to(ROOT)).replace("\\", "/"), count_lines(p))
                )
    rows.sort(key=lambda x: x[1], reverse=True)

    out = ROOT / "docs" / "LOC-REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write("# LOC Report\n\n| Arquivo | Linhas |\n|---|---:|\n")
        for rel, n in rows:
            f.write(f"| {rel} | {n} |\n")

    top = rows[:15]
    app = next((r for r in rows if r[0].endswith("app_gui.py")), None)

    print("== Top 15 por linhas ==")
    for rel, n in top:
        print(f"{n:>6}  {rel}")
    if app:
        print("\napp_gui.py:", app[1], "linhas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
