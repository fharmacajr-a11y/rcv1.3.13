# -*- coding: utf-8 -*-
"""Script de validação da política CustomTkinter (SSoT).

Uso:
    python scripts/validate_ctk_policy.py

Verifica se há violações da política de imports de customtkinter.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """Representa uma violação da política."""

    file: Path
    line_number: int
    line_content: str
    import_type: str


# Padrão regex que captura imports diretos de customtkinter
CTK_IMPORT_PATTERN = re.compile(
    r"^\s*(import\s+customtkinter|from\s+customtkinter\s+import)",
    re.MULTILINE,
)

# Arquivo whitelist (único permitido)
WHITELIST = {"src/ui/ctk_config.py"}


def find_violations(root: Path) -> list[Violation]:
    """Busca violações da política em arquivos Python."""
    violations: list[Violation] = []

    for py_file in root.rglob("*.py"):
        # Normalizar path para comparação (usar forward slashes)
        relative_path = py_file.relative_to(root).as_posix()

        # Pular arquivos whitelisted
        if relative_path in WHITELIST:
            continue

        # Pular diretórios especiais
        if any(part.startswith(".") for part in py_file.parts):
            continue
        if "__pycache__" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Buscar padrões linha por linha
        for line_number, line in enumerate(content.splitlines(), start=1):
            match = CTK_IMPORT_PATTERN.search(line)
            if match:
                import_type = "import" if "import customtkinter" in line else "from"
                violations.append(
                    Violation(
                        file=py_file,
                        line_number=line_number,
                        line_content=line.strip(),
                        import_type=import_type,
                    )
                )

    return violations


def main() -> int:
    """Executa validação e reporta resultados."""
    print("🔍 Validando política CustomTkinter (SSoT)...\n")

    root = Path(__file__).parent.parent
    violations = find_violations(root)

    if not violations:
        print("✅ Nenhuma violação encontrada!")
        print(f"✅ Todos os imports de customtkinter estão em: {', '.join(WHITELIST)}")
        return 0

    print(f"❌ {len(violations)} violação(ões) encontrada(s):\n")

    for v in violations:
        relative = v.file.relative_to(root)
        print(f"  📄 {relative}:{v.line_number}")
        print(f"     {v.line_content}")
        print(f"     Tipo: {v.import_type}\n")

    print("🔧 Como corrigir:")
    print("   1. Substitua imports diretos por:")
    print("      from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk")
    print("   2. Use 'ctk.CTkButton' ao invés de 'customtkinter.CTkButton'")
    print("   3. Rode: pre-commit run no-direct-customtkinter-import --all-files")
    print("\n📚 Documentação: docs/CTK_IMPORT_POLICY.md")

    return 1


if __name__ == "__main__":
    sys.exit(main())
