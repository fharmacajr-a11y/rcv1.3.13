#!/usr/bin/env python3
"""Guard: Impede referências a clientes_v2 (removido definitivamente).

Este guard garante que nenhum código novo referencie clientes_v2,
que foi completamente removido após migração para clientes.ui

Uso:
    python tools/check_no_clientes_v2_paths.py

Exit codes:
    0: OK - Nenhuma referência encontrada
    1: ERRO - Referências encontradas (bloqueia commit/CI)

Integração: pre-commit + CI
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

# Padrões PROIBIDOS (clientes_v2 foi removido)
FORBIDDEN_PATTERNS = [
    r"modules\.clientes_v2",
    r"src/modules/clientes_v2",
    r"src\\modules\\clientes_v2",
    r"from clientes_v2",
    r"import clientes_v2",
]


class Violation(NamedTuple):
    """Representa uma violação encontrada."""

    file: Path
    line: int
    matched_text: str


def check_file(file_path: Path) -> list[Violation]:
    """Verifica referências proibidas em um arquivo.

    Args:
        file_path: Path do arquivo a verificar

    Returns:
        Lista de violações encontradas
    """
    violations: list[Violation] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, line):
                    violations.append(Violation(file=file_path, line=line_num, matched_text=line.strip()))
                    break  # Uma violação por linha é suficiente
    except Exception:
        pass  # Ignorar erros de leitura

    return violations


def main() -> int:
    """Executa verificação em src/ e tests/.

    Returns:
        0 se OK, 1 se violações encontradas
    """
    root = Path(__file__).parent.parent
    all_violations: list[Violation] = []

    # Verificar src/ e tests/ (código ativo)
    for base_dir in ["src", "tests"]:
        search_path = root / base_dir
        if not search_path.exists():
            continue

        for py_file in search_path.rglob("*.py"):
            violations = check_file(py_file)
            all_violations.extend(violations)

    # Reportar resultados
    if not all_violations:
        print("✅ OK: Nenhuma referência a clientes_v2 encontrada")
        print("   (clientes_v2 foi removido - use clientes.ui)")
        return 0

    print(f"❌ ERRO: {len(all_violations)} referência(s) a clientes_v2 encontrada(s)\n")
    print("clientes_v2 foi REMOVIDO. Use clientes.ui ao invés:\n")

    # Agrupar por arquivo
    by_file: dict[Path, list[Violation]] = {}
    for v in all_violations:
        by_file.setdefault(v.file, []).append(v)

    for file_path, file_violations in sorted(by_file.items()):
        rel_path = file_path.relative_to(root)
        print(f"  {rel_path}:")
        for v in sorted(file_violations, key=lambda x: x.line):
            print(f"    Linha {v.line}: {v.matched_text[:80]}")
        print()

    print("💡 Use: from src.modules.clientes.ui import ClientesV2Frame")

    return 1


if __name__ == "__main__":
    sys.exit(main())
