"""
WarningsPack-01 — Analisador de Warnings do Pyright
Lê pyright.json e agrupa warnings por regra e arquivo para guiar as correções.
"""

import json
from collections import defaultdict
from pathlib import Path


def load_pyright_json(filepath: Path) -> dict:
    """Carrega o JSON do Pyright com encoding UTF-8."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def extract_warnings(data: dict) -> list[dict]:
    """Extrai apenas os diagnósticos com severity == 'warning'."""
    diagnostics = data.get("generalDiagnostics", [])
    return [d for d in diagnostics if d.get("severity") == "warning"]


def group_by_rule(warnings: list[dict]) -> dict[str, list[dict]]:
    """Agrupa warnings por regra (rule)."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for w in warnings:
        rule = w.get("rule", "unknown")
        grouped[rule].append(w)
    return dict(grouped)


def group_by_file(warnings: list[dict]) -> dict[str, list[dict]]:
    """Agrupa warnings por arquivo (file)."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for w in warnings:
        file_path = w.get("file", "unknown")
        # Normaliza para path relativo (simplifica a exibição)
        file_path = file_path.replace("c:\\Users\\Pichau\\Desktop\\v1.1.45\\", "")
        grouped[file_path].append(w)
    return dict(grouped)


def print_top_rules(grouped_rules: dict[str, list[dict]], top_n: int = 15) -> None:
    """Imprime as top N regras com mais warnings."""
    print("=" * 60)
    print("=== TOP WARNING RULES ===")
    print("=" * 60)
    sorted_rules = sorted(grouped_rules.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (rule, items) in enumerate(sorted_rules[:top_n], start=1):
        print(f"{i}) {rule} - {len(items)}")
    print()


def print_top_files(grouped_files: dict[str, list[dict]], top_n: int = 15) -> None:
    """Imprime os top N arquivos com mais warnings."""
    print("=" * 60)
    print("=== TOP WARNING FILES ===")
    print("=" * 60)
    sorted_files = sorted(grouped_files.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (file, items) in enumerate(sorted_files[:top_n], start=1):
        print(f"{i}) {file} - {len(items)}")
    print()


def print_sample_by_rule(grouped_rules: dict[str, list[dict]], sample_per_rule: int = 3) -> None:
    """Imprime samples de warnings por regra."""
    print("=" * 60)
    print("=== SAMPLE BY RULE (first N per rule) ===")
    print("=" * 60)

    sorted_rules = sorted(grouped_rules.items(), key=lambda x: len(x[1]), reverse=True)
    for rule, items in sorted_rules[:10]:  # Top 10 regras
        print(f"\n{rule}: ({len(items)} total)")
        for w in items[:sample_per_rule]:
            file_path = w.get("file", "?").replace("c:\\Users\\Pichau\\Desktop\\v1.1.45\\", "")
            line = w.get("range", {}).get("start", {}).get("line", 0) + 1  # line é 0-indexed
            msg = w.get("message", "")
            # Remove caracteres especiais que podem causar problemas no Windows
            msg_safe = msg.encode("ascii", errors="replace").decode("ascii")
            print(f"  - {file_path}:{line} - \"{msg_safe}\"")
    print()


def main() -> None:
    """Main entry point."""
    pyright_json_path = Path(__file__).parent / "pyright.json"

    if not pyright_json_path.exists():
        print(f"[X] Arquivo nao encontrado: {pyright_json_path}")
        return

    print(f"[*] Carregando {pyright_json_path}...")
    data = load_pyright_json(pyright_json_path)

    warnings = extract_warnings(data)
    print(f"[OK] Total de warnings encontrados: {len(warnings)}\n")

    # Agrupamentos
    grouped_rules = group_by_rule(warnings)
    grouped_files = group_by_file(warnings)

    # Relatórios
    print_top_rules(grouped_rules, top_n=15)
    print_top_files(grouped_files, top_n=15)
    print_sample_by_rule(grouped_rules, sample_per_rule=3)

    print("=" * 60)
    print("[OK] Analise concluida!")
    print("=" * 60)


if __name__ == "__main__":
    main()
