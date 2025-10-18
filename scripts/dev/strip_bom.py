# -*- coding: utf-8 -*-
"""
Script para remover BOM (Byte Order Mark) de arquivos Python.

UTF-8 é o encoding padrão no Python 3 (PEP 3120).
A presença de BOM (0xEF 0xBB 0xBF) é desnecessária e pode causar problemas.

Referências:
- PEP 3120: https://peps.python.org/pep-3120/
- PEP 263: https://peps.python.org/pep-0263/
"""
from pathlib import Path


def strip_bom_from_python_files():
    """Remove BOM de todos os arquivos .py no projeto."""
    count = 0
    fixed_files = []

    for p in Path(".").rglob("*.py"):
        # Ignora diretórios virtuais e cache
        if (
            ".venv" in p.parts
            or "__pycache__" in p.parts
            or "build" in p.parts
            or "dist" in p.parts
        ):
            continue

        try:
            b = p.read_bytes()
            if b.startswith(b"\xef\xbb\xbf"):
                # Remove os 3 bytes do BOM
                p.write_bytes(b[3:])
                count += 1
                fixed_files.append(str(p))
                print(f"✓ fix: {p}")
        except Exception as e:
            print(f"✗ erro ao processar {p}: {e}")

    print(f'\n{"="*60}')
    print(f"Total de arquivos corrigidos: {count}")
    print(f'{"="*60}')

    if fixed_files:
        print("\nArquivos modificados:")
        for f in fixed_files:
            print(f"  - {f}")
    else:
        print("\n✓ Nenhum arquivo com BOM encontrado!")

    return count


if __name__ == "__main__":
    print("Removendo BOM de arquivos Python...\n")
    strip_bom_from_python_files()
