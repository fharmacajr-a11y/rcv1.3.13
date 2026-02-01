#!/usr/bin/env python3
"""Guard: Impede uso de forms/_archived (movido para docs/).

Este guard garante que nenhum código ativo referencie forms/_archived,
que foi movido para docs/_archive/clientes_forms/ (fora do runtime).

Uso:
    python tools/check_no_clientes_archived_forms_paths.py

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

# Padrões PROIBIDOS (forms/_archived foi movido para docs/)
FORBIDDEN_PATTERNS = [
    r"forms\._archived",
    r"forms/_archived",
    r"forms\\_archived",
    r"from _archived",
    r"import _archived",
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
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(
                        Violation(file=file_path, line=line_num, matched_text=line.strip())
                    )
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
        print("✅ OK: Nenhuma referência a forms/_archived encontrada")
        print("   (código legado movido para docs/_archive/clientes_forms/)")
        return 0

    print(f"❌ ERRO: {len(all_violations)} referência(s) a forms/_archived encontrada(s)\n")
    print("forms/_archived foi MOVIDO para docs/_archive/clientes_forms/\n")
    print("Use os substitutos modernos:")
    print("  - form_cliente → ClientEditorDialog")
    print("  - ClientPicker → treeview em ClientesV2Frame")
    print("  - open_subpastas_dialog → SubpastaDialog\n")

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

    return 1


if __name__ == "__main__":
    sys.exit(main())
