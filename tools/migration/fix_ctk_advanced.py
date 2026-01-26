#!/usr/bin/env python3
"""Script para corrigir mais argumentos inválidos em widgets CTk."""

import re
from pathlib import Path


def fix_ctk_scrollbar_orient(content: str) -> str:
    """Remove orient= de CTkScrollbar (é redundante)."""
    # CTkScrollbar sempre é vertical por padrão
    pattern = r'ctk\.CTkScrollbar\(([^)]+),\s*orient="vertical"([^)]*)\)'
    replacement = r"ctk.CTkScrollbar(\1\2)"
    return re.sub(pattern, replacement, content, flags=re.IGNORECASE)


def fix_labelwidget(content: str) -> str:
    """Remove .configure(labelwidget=...) calls."""
    pattern = r"\.configure\(labelwidget=([^)]+)\)"
    replacement = r"  # TODO: labelwidget=\1 not supported in CTk"
    return re.sub(pattern, replacement, content, flags=re.IGNORECASE)


def fix_tkinter_font(content: str) -> str:
    """Converte Font() para tuplas."""
    # tkinter.font.Font para tupla
    pattern = r'font\.Font\(family="([^"]*)",\s*size=(\d+)(?:,\s*weight="([^"]*)")?\)'

    def replace_font(match):
        family = match.group(1)
        size = match.group(2)
        weight = match.group(3) if match.group(3) else "normal"
        return f'("{family}", {size}, "{weight}")'

    return re.sub(pattern, replace_font, content)


def fix_ctk_frame_remaining_padding(content: str) -> str:
    """Fix remaining CTkFrame padding patterns."""
    patterns = [
        # super().__init__(master, padding=X)
        (
            r"super\(\).__init__\(([^,]+),\s*padding=([^,)]+)([^)]*)\)",
            r"super().__init__(\1\3)  # TODO: padding=\2 -> usar pack/grid",
        ),
        # CTkFrame(parent, text=X, padding=Y)
        (
            r"ctk\.CTkFrame\(([^,]+),\s*text=([^,]+),\s*padding=([^)]+)\)",
            r"ctk.CTkFrame(\1)  # TODO: text=\2, padding=\3 -> usar CTkLabel + pack/grid",
        ),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    return content


def fix_selectmode(content: str) -> str:
    """Remove selectmode from CTk widgets."""
    pattern = r"([a-zA-Z_]+)\(([^)]+),\s*selectmode=([^,)]+)([^)]*)\)"
    replacement = r"\1(\2\4)  # TODO: selectmode=\3 -> handle in CTk way"
    return re.sub(pattern, replacement, content, flags=re.IGNORECASE)


def process_file(file_path: Path) -> bool:
    """Processa um arquivo Python, retorna True se foi modificado."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Aplicar todas as correções
        content = original_content
        content = fix_ctk_scrollbar_orient(content)
        content = fix_labelwidget(content)
        content = fix_tkinter_font(content)
        content = fix_ctk_frame_remaining_padding(content)
        content = fix_selectmode(content)

        if content != original_content:
            print(f"🔧 CORRIGINDO: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"❌ ERRO em {file_path}: {e}")
        return False


def main():
    """Processa todos os arquivos .py em src/."""
    src_path = Path("src")
    if not src_path.exists():
        print("❌ Pasta 'src' não encontrada")
        return

    modified_count = 0
    total_count = 0

    for py_file in src_path.rglob("*.py"):
        total_count += 1
        if process_file(py_file):
            modified_count += 1

    print(f"\n✅ Concluído: {modified_count}/{total_count} arquivos modificados")


if __name__ == "__main__":
    main()
