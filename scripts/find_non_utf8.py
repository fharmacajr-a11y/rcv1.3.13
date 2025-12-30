# -*- coding: utf-8 -*-
"""Script para encontrar arquivos Python com problemas de encoding UTF-8."""

from __future__ import annotations

import sys
from pathlib import Path


def check_file_encoding(file_path: Path) -> tuple[bool, str | None]:
    """
    Verifica se um arquivo pode ser lido como UTF-8.

    Returns:
        (is_valid, error_message)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read()
        return True, None
    except UnicodeDecodeError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Erro inesperado: {e}"


def main() -> int:
    """Escaneia diretórios em busca de arquivos com problemas de encoding."""
    project_root = Path(__file__).parent.parent

    # Diretórios a verificar
    dirs_to_check = ["src", "infra", "adapters", "data", "security", "helpers", "tests"]

    problematic_files = []

    for dir_name in dirs_to_check:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue

        print(f"Verificando {dir_name}/...")

        for py_file in dir_path.rglob("*.py"):
            is_valid, error = check_file_encoding(py_file)
            if not is_valid:
                rel_path = py_file.relative_to(project_root)
                problematic_files.append((rel_path, error))
                print(f"  ❌ {rel_path}: {error}")

    print("\n" + "=" * 70)
    if problematic_files:
        print(f"❌ Encontrados {len(problematic_files)} arquivo(s) com problema de encoding:")
        for file_path, error in problematic_files:
            print(f"  - {file_path}")
            print(f"    {error}")
        return 1
    else:
        print("✅ Todos os arquivos Python estão em UTF-8 válido!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
