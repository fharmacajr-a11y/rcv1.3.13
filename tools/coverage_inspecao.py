from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


COV_JSON = Path("reports/coverage.json")
OUT_MD = Path("reports/inspecao/coverage_inspecao.md")
OUT_TXT = Path("reports/inspecao/coverage_inspecao.txt")


@dataclass(frozen=True)
class FileCov:
    path: str
    num_statements: int
    missing_lines: int
    excluded_lines: int
    percent_covered: float

    @property
    def covered_statements(self) -> int:
        # Fórmula padrão de statements (aproxima o que o coverage usa em totals).
        return max(self.num_statements - self.missing_lines, 0)


def _norm(p: str) -> str:
    # Normaliza para comparar Windows/Linux
    return p.replace("\\", "/").lstrip("./").lower()


def load_files() -> list[FileCov]:
    data = json.loads(COV_JSON.read_text(encoding="utf-8"))
    files = data.get("files", {}) or {}
    out: list[FileCov] = []

    for path, payload in files.items():
        summ = (payload or {}).get("summary", {}) or {}
        num = int(summ.get("num_statements", 0) or 0)
        missing = int(summ.get("missing_lines", 0) or 0)
        excluded = int(summ.get("excluded_lines", 0) or 0)
        pct = float(summ.get("percent_covered", 0.0) or 0.0)
        out.append(
            FileCov(
                path=str(path), num_statements=num, missing_lines=missing, excluded_lines=excluded, percent_covered=pct
            )
        )

    return out


def group_weighted(files: Iterable[FileCov], key_fn):
    agg = defaultdict(lambda: {"files": 0, "stmts": 0, "miss": 0})
    for f in files:
        k = key_fn(f)
        agg[k]["files"] += 1
        agg[k]["stmts"] += f.num_statements
        agg[k]["miss"] += f.missing_lines

    rows = []
    for k, v in agg.items():
        stmts = v["stmts"]
        miss = v["miss"]
        covered = max(stmts - miss, 0)
        pct = (covered / stmts * 100.0) if stmts else 100.0
        rows.append((k, v["files"], stmts, miss, pct))
    rows.sort(key=lambda r: (r[4], r[3]), reverse=False)  # menor % primeiro, depois mais miss
    return rows


def top_opportunities(files: list[FileCov], *, exclude_prefixes: tuple[str, ...], min_statements: int, limit: int):
    kept = []
    for f in files:
        p = _norm(f.path)
        if any(p.startswith(_norm(x)) for x in exclude_prefixes):
            continue
        if "tests/" in p:
            continue
        if f.num_statements < min_statements:
            continue
        kept.append((f.missing_lines, f.num_statements, f.percent_covered, f.path))
    kept.sort(key=lambda t: (t[0], t[1]), reverse=True)  # mais miss e mais tamanho primeiro
    return kept[:limit]


def scan_py_files(roots: list[str]) -> set[str]:
    all_py: set[str] = set()
    for r in roots:
        base = Path(r)
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            # ignore venv/pytest cache
            s = p.as_posix().lower()
            if "/.venv/" in s or "/venv/" in s or "/__pycache__/" in s:
                continue
            if "/tests/" in s:
                continue
            all_py.add(s.lstrip("./"))
    return all_py


def main() -> None:
    if not COV_JSON.exists():
        raise SystemExit(
            f"ERRO: {COV_JSON} não encontrado. Não rode coverage de novo; gere o arquivo uma vez e re-use."
        )

    files = load_files()
    files_norm = {_norm(f.path) for f in files}

    total_stmts = sum(f.num_statements for f in files)
    total_miss = sum(f.missing_lines for f in files)
    total_cov = (max(total_stmts - total_miss, 0) / total_stmts * 100.0) if total_stmts else 100.0

    # Agrupamento por raiz (src/infra/adapters/data/security/...)
    def root_key(f: FileCov) -> str:
        p = _norm(f.path)
        return p.split("/", 1)[0] if "/" in p else p

    root_rows = group_weighted(files, root_key)

    # Subgrupos do src (src/core, src/utils, src/modules, src/ui, etc)
    def src_key(f: FileCov) -> str:
        p = _norm(f.path)
        parts = p.split("/")
        if len(parts) >= 2 and parts[0] == "src":
            return "/".join(parts[:2])
        return root_key(f)

    src_rows = [r for r in group_weighted(files, src_key) if r[0].startswith("src/")]

    # Oportunidades (não-GUI vs GUI)
    non_gui = top_opportunities(files, exclude_prefixes=("src/ui/",), min_statements=25, limit=30)
    gui_only = top_opportunities(files, exclude_prefixes=(), min_statements=25, limit=30)
    gui_only = [t for t in gui_only if _norm(t[3]).startswith("src/ui/")][:30]

    # Arquivos .py no repo que não aparecem no coverage.json
    roots = ["src", "infra", "adapters", "data", "security"]
    scanned = scan_py_files(roots)
    not_in_cov = sorted(p for p in scanned if p not in files_norm)

    lines = []
    lines.append(f"Cobertura total (statements): {total_cov:.2f}%")
    lines.append(f"Statements: {total_stmts - total_miss}/{total_stmts}")
    lines.append("")
    lines.append("== Resumo por raiz (weighted por statements) ==")
    lines.append("Pasta | Arquivos | Statements | Miss | Cobertura")
    lines.append("---|---:|---:|---:|---:")
    for k, nfiles, stmts, miss, pct in root_rows:
        lines.append(f"{k} | {nfiles} | {stmts} | {miss} | {pct:.1f}%")

    lines.append("")
    lines.append("== Sub-resumo do src (por 1º subpacote) ==")
    lines.append("Pasta | Arquivos | Statements | Miss | Cobertura")
    lines.append("---|---:|---:|---:|---:")
    for k, nfiles, stmts, miss, pct in src_rows:
        lines.append(f"{k} | {nfiles} | {stmts} | {miss} | {pct:.1f}%")

    lines.append("")
    lines.append("== TOP 30 oportunidades (NÃO-GUI, exclui src/ui, min 25 stmts; ordenado por miss) ==")
    lines.append("Miss | Stmts | % | Arquivo")
    lines.append("---:|---:|---:|---")
    for miss, stmts, pct, path in non_gui:
        lines.append(f"{miss} | {stmts} | {pct:.1f}% | {path}")

    lines.append("")
    lines.append("== TOP 30 oportunidades (GUI, só src/ui, min 25 stmts; ordenado por miss) ==")
    lines.append("Miss | Stmts | % | Arquivo")
    lines.append("---:|---:|---:|---")
    for miss, stmts, pct, path in gui_only:
        lines.append(f"{miss} | {stmts} | {pct:.1f}% | {path}")

    lines.append("")
    lines.append(
        "== Arquivos .py existentes que NÃO aparecem no coverage.json (possível: nunca importados/executados) =="
    )
    for p in not_in_cov[:200]:
        lines.append(f"- {p}")
    if len(not_in_cov) > 200:
        lines.append(f"... +{len(not_in_cov) - 200} arquivos (ver lista completa no .txt)")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(not_in_cov) + "\n", encoding="utf-8")

    print(f"[OK] Gerado: {OUT_MD}")
    print(f"[OK] Lista completos não-no-coverage: {OUT_TXT}")


if __name__ == "__main__":
    main()
