#!/usr/bin/env python3
"""
Script de ranking de cobertura para identificar próximos alvos de testes.
Lê coverage.json e gera ranking de arquivos com:
- fora de tests/
- stmts entre 20 e 120
- ordenados por menor percent_covered, depois menor stmts
"""

import json
import sys
from pathlib import Path


def load_coverage(coverage_path: Path) -> dict:
    """Carrega o arquivo coverage.json"""
    # Tentar primeiro em reports/coverage.json
    if not coverage_path.exists():
        alternative_path = Path("reports/coverage.json")
        if alternative_path.exists():
            coverage_path = alternative_path
            print(f"📊 Analisando cobertura: {coverage_path}")
        else:
            print(f"❌ Arquivo não encontrado: {coverage_path}")
            print("   Rode: pytest -c pytest_cov.ini")
            sys.exit(1)

    try:
        with open(coverage_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON: {e}")
        sys.exit(1)


def analyze_files(coverage_data: dict) -> list[dict]:
    """
    Analisa os arquivos do coverage e retorna lista de candidatos.

    Critérios:
    - Não estão em tests/
    - Possuem entre 20 e 120 statements
    - Ordenados por menor cobertura, depois menor tamanho
    """
    files = coverage_data.get("files", {})
    candidates = []

    for filepath, stats in files.items():
        # Normalizar path para usar /
        filepath_normalized = filepath.replace("\\", "/")

        # Filtrar: não incluir tests/
        if "/tests/" in filepath_normalized or filepath_normalized.startswith("tests/"):
            continue

        # Pegar métricas
        num_statements = stats["summary"].get("num_statements", 0)
        covered_lines = stats["summary"].get("covered_lines", 0)

        # Filtrar por tamanho
        if not (20 <= num_statements <= 120):
            continue

        # Calcular percentual
        percent_covered = (covered_lines / num_statements * 100) if num_statements > 0 else 0

        candidates.append(
            {
                "file": filepath_normalized,
                "stmts": num_statements,
                "covered": covered_lines,
                "percent": percent_covered,
            }
        )

    # Ordenar: menor percent_covered primeiro, depois menor stmts
    candidates.sort(key=lambda x: (x["percent"], x["stmts"]))

    return candidates


def suggest_headless(candidates: list[dict]) -> list[dict]:
    """
    Sugere os 3 melhores candidatos "headless" (sem Tk, sem rede externa).

    Heurística:
    - Priorizar: helpers/, infra/ (exceto storage), security/, data/
    - Evitar: modules/ com UI, adapters/storage, arquivos com "window", "dialog", "view"
    """
    headless_keywords = ["helpers/", "infra/", "security/", "data/", "core/"]
    avoid_keywords = ["window", "dialog", "view", "screen", "ui", "storage", "widget"]

    headless = []
    for candidate in candidates:
        filepath = candidate["file"].lower()

        # Priorizar módulos headless
        has_headless = any(kw in filepath for kw in headless_keywords)
        has_avoid = any(kw in filepath for kw in avoid_keywords)

        if has_headless and not has_avoid:
            headless.append(candidate)

        if len(headless) >= 3:
            break

    return headless


def print_ranking(candidates: list[dict], top_n: int = 30):
    """Imprime ranking dos candidatos"""
    print(f"\n{'=' * 80}")
    print(f"TOP {top_n} ARQUIVOS PARA AUMENTAR COBERTURA")
    print(f"{'=' * 80}")
    print(f"{'#':<4} {'Arquivo':<55} {'Stmts':<7} {'Cov%':<7}")
    print(f"{'-' * 80}")

    for i, candidate in enumerate(candidates[:top_n], 1):
        print(f"{i:<4} {candidate['file']:<55} {candidate['stmts']:<7} {candidate['percent']:<7.1f}")

    print(f"{'-' * 80}\n")


def print_headless_suggestions(headless: list[dict]):
    """Imprime sugestões de testes headless"""
    if not headless:
        print("⚠️  Nenhum candidato headless identificado nos top 30.\n")
        return

    print(f"\n{'=' * 80}")
    print("🎯 TOP 3 SUGESTÕES HEADLESS (sem Tk, sem rede)")
    print(f"{'=' * 80}")

    for i, candidate in enumerate(headless, 1):
        print(f"\n{i}. {candidate['file']}")
        print(f"   Statements: {candidate['stmts']} | Cobertura: {candidate['percent']:.1f}%")

    print(f"\n{'=' * 80}\n")


def main():
    # Localizar coverage.json
    project_root = Path(__file__).parent.parent
    coverage_path = project_root / "coverage.json"

    print(f"📊 Analisando cobertura: {coverage_path}")

    # Carregar e analisar
    coverage_data = load_coverage(coverage_path)
    candidates = analyze_files(coverage_data)

    if not candidates:
        print("⚠️  Nenhum arquivo encontrado nos critérios (20-120 stmts, fora de tests/).")
        return

    # Imprimir ranking
    print_ranking(candidates, top_n=30)

    # Sugerir headless
    headless = suggest_headless(candidates)
    print_headless_suggestions(headless)

    # Resumo final
    print(f"✅ Total de candidatos analisados: {len(candidates)}")
    print(f"📁 Arquivo de cobertura: {coverage_path.relative_to(project_root)}")


if __name__ == "__main__":
    main()
