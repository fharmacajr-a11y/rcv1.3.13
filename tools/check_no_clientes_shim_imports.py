#!/usr/bin/env python3
"""Guard: Impede uso interno dos shims de compatibilidade do módulo Clientes.

Este script garante que o código interno do projeto use APENAS os caminhos
definitivos em src.modules.clientes.core.*, e não os shims de compatibilidade.

Os shims existem apenas para compatibilidade externa e emitem DeprecationWarning.
Nosso código não deve depender deles.

Uso:
    python tools/check_no_clientes_shim_imports.py

Exit codes:
    0: OK - Nenhum import de shim encontrado
    1: ERRO - Imports de shims encontrados (detalhes impressos)

Integração CI/pre-commit: adicionar junto com check_no_clientes_v2_imports.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple

# Arquivos shim permitidos (podem ter imports circulares por definição)
ALLOWED_SHIM_FILES = {
    "src/modules/clientes/export.py",
    "src/modules/clientes/viewmodel.py",
    "src/modules/clientes/service.py",
    "src/modules/clientes/components/helpers.py",
    "src/modules/clientes/views/main_screen_helpers.py",
}

# Padrões PROIBIDOS (imports dos shims)
FORBIDDEN_PATTERNS = {
    "src.modules.clientes.export",
    "src.modules.clientes.viewmodel",
    "src.modules.clientes.service",
    "src.modules.clientes.components.helpers",
    "src.modules.clientes.views.main_screen_helpers",
}

# Padrões CORRETOS (core/*)
CORRECT_PATTERNS = {
    "src.modules.clientes.core.export",
    "src.modules.clientes.core.viewmodel",
    "src.modules.clientes.core.service",
    "src.modules.clientes.core.constants",
    "src.modules.clientes.core.ui_helpers",
}


class Violation(NamedTuple):
    """Representa uma violação encontrada."""

    file: Path
    line: int
    col: int
    import_path: str


def normalize_path(p: Path) -> str:
    """Normaliza path para comparação (forward slashes)."""
    return str(p).replace("\\", "/")


def is_shim_file(file_path: Path) -> bool:
    """Verifica se arquivo é um dos shims permitidos."""
    normalized = normalize_path(file_path)
    return normalized in ALLOWED_SHIM_FILES


def check_file(file_path: Path) -> list[Violation]:
    """Verifica imports proibidos em um arquivo Python.

    Args:
        file_path: Path do arquivo a verificar

    Returns:
        Lista de violações encontradas (vazia se OK)
    """
    # Pular arquivos shim
    if is_shim_file(file_path):
        return []

    violations: list[Violation] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        print(f"⚠️  Erro ao parsear {file_path}: {e}", file=sys.stderr)
        return []

    for node in ast.walk(tree):
        # from X import Y
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Verificar se é um dos padrões proibidos
            if module in FORBIDDEN_PATTERNS:
                violations.append(
                    Violation(
                        file=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        import_path=module,
                    )
                )

        # import X (menos comum, mas verificar)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_PATTERNS:
                    violations.append(
                        Violation(
                            file=file_path,
                            line=node.lineno,
                            col=node.col_offset,
                            import_path=alias.name,
                        )
                    )

    return violations


def main() -> int:
    """Executa verificação em src/ e tests/.

    Returns:
        0 se OK, 1 se violações encontradas
    """
    root = Path(__file__).parent.parent
    all_violations: list[Violation] = []

    # Verificar src/ e tests/
    for base_dir in ["src", "tests"]:
        search_path = root / base_dir
        if not search_path.exists():
            continue

        for py_file in search_path.rglob("*.py"):
            violations = check_file(py_file)
            all_violations.extend(violations)

    # Reportar resultados
    if not all_violations:
        print("✅ OK: Nenhum import de shim encontrado")
        print(f"   Verificados: src/ e tests/")
        print(f"   Shims permitidos: {len(ALLOWED_SHIM_FILES)} arquivo(s)")
        return 0

    print(f"❌ ERRO: {len(all_violations)} import(s) de shim encontrado(s)\n")
    print("Imports proibidos (use caminhos core/* ao invés):\n")

    # Agrupar por arquivo
    by_file: dict[Path, list[Violation]] = {}
    for v in all_violations:
        by_file.setdefault(v.file, []).append(v)

    for file_path, file_violations in sorted(by_file.items()):
        rel_path = file_path.relative_to(root)
        print(f"  {rel_path}:")
        for v in sorted(file_violations, key=lambda x: x.line):
            print(f"    Linha {v.line}, Col {v.col}: from {v.import_path} import ...")

    print("\n💡 Use os caminhos corretos:")
    for correct in sorted(CORRECT_PATTERNS):
        print(f"   ✓ {correct}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
