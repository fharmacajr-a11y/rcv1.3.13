#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Guardião de Encoding UTF-8

Verifica se todos os arquivos de texto do projeto estão em UTF-8 válido.
Útil para CI/CD para garantir consistência de encoding.

Uso:
    python scripts/check_utf8.py

Exit codes:
    0 - Todos os arquivos estão em UTF-8
    1 - Encontrados arquivos com encoding inválido
"""
import sys
from pathlib import Path


def main():
    """Verifica encoding UTF-8 em arquivos de texto."""
    # Extensões a verificar
    text_extensions = {
        ".py",
        ".md",
        ".txt",
        ".csv",
        ".json",
        ".yml",
        ".yaml",
        ".ps1",
        ".toml",
        ".ini",
        ".cfg",
        ".rst",
    }

    # Diretórios a ignorar
    ignore_dirs = {
        ".venv",
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "runtime",
        ".tox",
        "dist",
        "build",
        ".import_linter_cache",
        "node_modules",
    }

    root = Path(__file__).parent.parent
    bad_files = []
    checked_count = 0

    print("🔍 Verificando encoding UTF-8...")
    print(f"📁 Raiz: {root}")
    print(f"📋 Extensões: {', '.join(sorted(text_extensions))}")
    print()

    for file_path in root.rglob("*"):
        # Pular se for diretório
        if not file_path.is_file():
            continue

        # Pular se estiver em diretório ignorado
        if any(ignored in file_path.parts for ignored in ignore_dirs):
            continue

        # Pular se extensão não estiver na lista
        if file_path.suffix.lower() not in text_extensions:
            continue

        checked_count += 1
        relative_path = file_path.relative_to(root)

        try:
            # Tentar ler como UTF-8
            content = file_path.read_text(encoding="utf-8")

            # Verificar se há BOM (não recomendado)
            if content.startswith("\ufeff"):
                bad_files.append(
                    f"⚠️  {relative_path} -> Contém BOM UTF-8 (não recomendado)"
                )

        except UnicodeDecodeError as e:
            bad_files.append(f"❌ {relative_path} -> {e}")
        except Exception as e:
            bad_files.append(f"⚠️  {relative_path} -> Erro ao ler: {e}")

    # Resultados
    print(f"✅ Arquivos verificados: {checked_count}")
    print()

    if bad_files:
        print("❌ FALHA: Encontrados arquivos com problemas de encoding:\n")
        for issue in bad_files:
            print(f"   {issue}")
        print()
        print(f"Total de problemas: {len(bad_files)}")
        return 1
    else:
        print("✅ SUCESSO: Todos os arquivos estão em UTF-8 válido!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
