#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Remove BOM UTF-8 de arquivos de texto.

Uso:
    python scripts/remove_bom.py
"""
import sys
from pathlib import Path


def remove_bom(file_path: Path) -> bool:
    """
    Remove BOM UTF-8 de um arquivo.

    Args:
        file_path: Caminho do arquivo

    Returns:
        True se o BOM foi removido, False caso contrário
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if content.startswith("\ufeff"):
            # Remover BOM e regravar
            file_path.write_text(content[1:], encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"❌ Erro ao processar {file_path}: {e}")
        return False


def main():
    """Remove BOM de arquivos específicos."""
    root = Path(__file__).parent.parent

    # Arquivos com BOM detectados
    files_with_bom = [
        "ajuda/dup-consolidacao/AUDIT_CONSOLIDATION_LOG.txt",
        "ajuda/dup-consolidacao/DEPTRY.txt",
        "ajuda/dup-consolidacao/INVENTARIO.csv",
        ".github/workflows/security-audit.yml",
    ]

    print("🔧 Removendo BOM UTF-8 de arquivos...\n")

    removed_count = 0
    for file_rel_path in files_with_bom:
        file_path = root / file_rel_path
        if file_path.exists():
            if remove_bom(file_path):
                print(f"✅ {file_rel_path} - BOM removido")
                removed_count += 1
            else:
                print(f"ℹ️  {file_rel_path} - Sem BOM (já estava correto)")
        else:
            print(f"⚠️  {file_rel_path} - Arquivo não encontrado")

    print(f"\n✅ Total: {removed_count} arquivo(s) corrigido(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
