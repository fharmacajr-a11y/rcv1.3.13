#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converte arquivos UTF-16 para UTF-8.

Uso:
    python scripts/convert_utf16_to_utf8.py
"""
import sys
from pathlib import Path


def convert_to_utf8(file_path: Path) -> bool:
    """
    Converte arquivo UTF-16 para UTF-8.

    Args:
        file_path: Caminho do arquivo

    Returns:
        True se converteu com sucesso
    """
    try:
        # Tentar ler como UTF-16
        content = file_path.read_text(encoding="utf-16")
        # Regravar como UTF-8 sem BOM
        file_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"❌ Erro ao converter {file_path}: {e}")
        return False


def main():
    """Converte arquivos UTF-16 para UTF-8."""
    root = Path(__file__).parent.parent

    # Arquivos UTF-16 detectados
    utf16_files = [
        "ajuda/ARCH_RULES_REPORT.txt",
        "ajuda/DEPTRY_AFTER.txt",
        "ajuda/DEPTRY_BEFORE.txt",
        "ajuda/VULTURE_AFTER.txt",
        "ajuda/VULTURE_BEFORE.txt",
    ]

    print("🔄 Convertendo UTF-16 para UTF-8...\n")

    converted_count = 0
    for file_rel_path in utf16_files:
        file_path = root / file_rel_path
        if file_path.exists():
            if convert_to_utf8(file_path):
                print(f"✅ {file_rel_path} - Convertido para UTF-8")
                converted_count += 1
        else:
            print(f"⚠️  {file_rel_path} - Arquivo não encontrado")

    print(f"\n✅ Total: {converted_count} arquivo(s) convertido(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
