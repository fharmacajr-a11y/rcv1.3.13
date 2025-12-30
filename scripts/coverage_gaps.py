#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analisa reports/coverage.json e lista os 10 arquivos com pior cobertura.

Também gera um resumo por pasta raiz lógica (src, infra, adapters, data, security).

Uso:
    python scripts/coverage_gaps.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# Raiz do projeto (subindo de scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COVERAGE_JSON = PROJECT_ROOT / "reports" / "coverage.json"

# Pastas raízes de produto
ROOT_FOLDERS = {"src", "infra", "adapters", "data", "security"}


def load_coverage_data() -> dict:
    """Carrega dados do coverage.json."""
    if not COVERAGE_JSON.exists():
        print(f"[ERRO] Arquivo não encontrado: {COVERAGE_JSON}")
        print("Execute primeiro: python -m pytest -c pytest_cov.ini")
        sys.exit(1)

    with open(COVERAGE_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_root_folder(filepath: str) -> str:
    """Extrai a pasta raiz lógica do path."""
    parts = Path(filepath).parts
    for part in parts:
        if part in ROOT_FOLDERS:
            return part
    return "other"


def analyze_gaps(data: dict) -> tuple[list[tuple[str, float, int]], dict[str, dict]]:
    """
    Analisa gaps de cobertura.

    Returns:
        - Lista dos arquivos com menor cobertura: [(path, percent, statements), ...]
        - Resumo por pasta raiz: {pasta: {files: N, total_statements: N, covered: N, avg_percent: X}}
    """
    files_data: list[tuple[str, float, int]] = []
    folder_stats: dict[str, dict] = defaultdict(lambda: {"files": 0, "total_statements": 0, "covered_statements": 0})

    files_info = data.get("files", {})

    for filepath, info in files_info.items():
        summary = info.get("summary", {})
        num_statements = summary.get("num_statements", 0)
        covered_lines = summary.get("covered_lines", 0)
        percent = summary.get("percent_covered", 0.0)

        # Ignorar arquivos sem statements (ex: __init__.py vazio)
        if num_statements == 0:
            continue

        files_data.append((filepath, percent, num_statements))

        # Acumular por pasta raiz
        root = get_root_folder(filepath)
        folder_stats[root]["files"] += 1
        folder_stats[root]["total_statements"] += num_statements
        folder_stats[root]["covered_statements"] += covered_lines

    # Ordenar por menor cobertura (pior primeiro)
    files_data.sort(key=lambda x: x[1])

    # Calcular médias por pasta
    for root, stats in folder_stats.items():
        if stats["total_statements"] > 0:
            stats["avg_percent"] = (stats["covered_statements"] / stats["total_statements"]) * 100
        else:
            stats["avg_percent"] = 0.0

    return files_data, dict(folder_stats)


def main() -> None:
    """Executa análise de gaps."""
    data = load_coverage_data()

    # Extrair total global
    totals = data.get("totals", {})
    global_percent = totals.get("percent_covered", 0.0)
    global_statements = totals.get("num_statements", 0)
    global_covered = totals.get("covered_lines", 0)

    print("=" * 70)
    print("ANÁLISE DE COBERTURA - RC Gestor v1.4.79")
    print("=" * 70)
    print()

    print(">>> TOTAL GLOBAL:")
    print(f"    Cobertura: {global_percent:.2f}%")
    print(f"    Statements: {global_covered}/{global_statements}")
    print()

    files_data, folder_stats = analyze_gaps(data)

    print(">>> TOP 10 ARQUIVOS COM MENOR COBERTURA:")
    print("-" * 70)
    for i, (filepath, percent, statements) in enumerate(files_data[:10], 1):
        print(f"  {i:2d}. {percent:5.1f}% ({statements:4d} stmts) {filepath}")
    print()

    print(">>> RESUMO POR PASTA RAIZ:")
    print("-" * 70)
    print(f"  {'Pasta':<12} {'Arquivos':>10} {'Statements':>12} {'Cobertura':>12}")
    print(f"  {'-' * 12} {'-' * 10} {'-' * 12} {'-' * 12}")

    for root in sorted(folder_stats.keys()):
        stats = folder_stats[root]
        print(f"  {root:<12} {stats['files']:>10} {stats['total_statements']:>12} {stats['avg_percent']:>11.1f}%")

    print()
    print("=" * 70)
    print("Relatórios gerados:")
    print("  - htmlcov/index.html")
    print("  - reports/coverage.json")
    print("  - reports/coverage.xml")
    print("=" * 70)


if __name__ == "__main__":
    main()
