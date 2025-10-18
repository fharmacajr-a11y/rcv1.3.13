#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gera árvore do projeto em UTF-8 puro (alternativa ao tree.com)
"""
from pathlib import Path


def generate_tree(root_path, prefix="", output_file=None, max_depth=5, current_depth=0):
    """
    Gera árvore de diretórios em UTF-8 com caracteres ASCII.

    Args:
        root_path: Caminho raiz
        prefix: Prefixo para indentação
        output_file: Arquivo de saída
        max_depth: Profundidade máxima
        current_depth: Profundidade atual
    """
    if current_depth >= max_depth:
        return

    root = Path(root_path)

    # Ignorar diretórios
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
        "*.egg-info",
    }

    try:
        items = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        items = [item for item in items if item.name not in ignore_dirs]
    except PermissionError:
        return

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "+-- " if is_last else "|-- "

        line = f"{prefix}{connector}{item.name}"
        if item.is_dir():
            line += "/"

        if output_file:
            output_file.write(line + "\n")
        else:
            print(line)

        if item.is_dir() and item.name not in ignore_dirs:
            extension = "    " if is_last else "|   "
            generate_tree(
                item, prefix + extension, output_file, max_depth, current_depth + 1
            )


if __name__ == "__main__":

    root_path = Path(__file__).parent.parent
    output_path = root_path / "ajuda" / "dup-consolidacao" / "ARVORE.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Árvore do Projeto: {root_path.name}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{root_path.name}/\n")
        generate_tree(root_path, "", f, max_depth=4)

    print(f"✅ Árvore gerada em: {output_path}")
