#!/usr/bin/env python3
"""Relatório de uso de código legado do módulo Clientes.

Este script gera um inventário completo de referências a código legado
que deve ser eventualmente removido:
- clientes_v2 (substituído por clientes.ui)
- forms/_archived (código arquivado)

Uso:
    python tools/report_clientes_legacy_usage.py

Exit code:
    0: Sempre (é apenas relatório informativo)

Output:
    Contagem de ocorrências por padrão e arquivo
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

# Padrões de legado a buscar
LEGACY_PATTERNS = {
    "clientes_v2_module": r"modules\.clientes_v2|src/modules/clientes_v2|clientes_v2",
    "archived_forms_module": r"forms\._archived|forms/_archived",
}


class Match(NamedTuple):
    """Representa uma ocorrência encontrada."""

    file: Path
    line: int
    pattern_name: str
    matched_text: str


def scan_file(file_path: Path, pattern_name: str, regex: re.Pattern) -> list[Match]:
    """Escaneia arquivo buscando padrão específico.

    Args:
        file_path: Arquivo a escanear
        pattern_name: Nome do padrão (para reporting)
        regex: Regex compilado para buscar

    Returns:
        Lista de matches encontrados
    """
    matches: list[Match] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                # Extrair texto matchado
                match_obj = regex.search(line)
                if match_obj:
                    matched = match_obj.group(0)
                    matches.append(
                        Match(
                            file=file_path,
                            line=line_num,
                            pattern_name=pattern_name,
                            matched_text=matched,
                        )
                    )
    except Exception as e:
        print(f"⚠️  Erro ao ler {file_path}: {e}", file=sys.stderr)

    return matches


def main() -> int:
    """Gera relatório de uso de código legado.

    Returns:
        0 (sempre - é apenas relatório)
    """
    root = Path(__file__).parent.parent
    all_matches: dict[str, list[Match]] = {name: [] for name in LEGACY_PATTERNS}

    # Compilar regexes
    compiled_patterns = {name: re.compile(pattern) for name, pattern in LEGACY_PATTERNS.items()}

    # Escanear diretórios
    scan_dirs = ["src", "tests", "docs", "tools"]
    extensions = {".py", ".md", ".txt", ".yml", ".yaml"}

    print("🔍 Escaneando código legado do módulo Clientes...\n")

    for base_dir in scan_dirs:
        search_path = root / base_dir
        if not search_path.exists():
            continue

        for file_path in search_path.rglob("*"):
            if file_path.suffix not in extensions:
                continue

            # Escanear cada padrão
            for pattern_name, regex in compiled_patterns.items():
                matches = scan_file(file_path, pattern_name, regex)
                all_matches[pattern_name].extend(matches)

    # Gerar relatório
    total_matches = sum(len(matches) for matches in all_matches.values())

    if total_matches == 0:
        print("✅ Nenhuma referência a código legado encontrada!")
        print(f"   Diretórios escaneados: {', '.join(scan_dirs)}")
        return 0

    print(f"📊 {total_matches} referência(s) a código legado encontrada(s)\n")

    for pattern_name, matches in all_matches.items():
        if not matches:
            continue

        print(f"{'=' * 70}")
        print(f"Padrão: {pattern_name}")
        print(f"Total: {len(matches)} ocorrência(s)")
        print(f"{'=' * 70}\n")

        # Agrupar por arquivo
        by_file: dict[Path, list[Match]] = {}
        for m in matches:
            by_file.setdefault(m.file, []).append(m)

        for file_path, file_matches in sorted(by_file.items()):
            rel_path = file_path.relative_to(root)
            print(f"  📁 {rel_path} ({len(file_matches)} ocorrência(s)):")
            for m in sorted(file_matches, key=lambda x: x.line):
                print(f"     Linha {m.line}: {m.matched_text}")
            print()

    print(f"\n{'=' * 70}")
    print(
        f"RESUMO: {total_matches} referência(s) em {len(set(m.file for matches in all_matches.values() for m in matches))} arquivo(s)"
    )
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
