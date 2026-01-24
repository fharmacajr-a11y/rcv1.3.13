#!/usr/bin/env python
"""Script para migrar em massa ttk.* para CTk equivalentes.

MICROFASE 29 - Elimina\u00e7\u00e3o completa de tkinter.ttk de src/.
"""

import re
import sys
from pathlib import Path

# Mapeamento de widgets ttk para CTk
TTK_TO_CTK_WIDGETS = {
    "ttk.Frame": "ctk.CTkFrame",
    "ttk.Label": "ctk.CTkLabel",
    "ttk.Button": "ctk.CTkButton",
    "ttk.Entry": "ctk.CTkEntry",
    "ttk.Combobox": "ctk.CTkComboBox",
    "ttk.Checkbutton": "ctk.CTkCheckBox",
    "ttk.Radiobutton": "ctk.CTkRadioButton",
    "ttk.Scale": "ctk.CTkSlider",
    "ttk.Progressbar": "ctk.CTkProgressBar",
    "ttk.Scrollbar": "ctk.CTkScrollbar",  # ou considerar CTkScrollableFrame
    "ttk.Separator": "ctk.CTkFrame",  # usar com width=2/height=2 como linha
    "ttk.Labelframe": "ctk.CTkFrame",  # CTk n\u00e3o tem LabelFrame direto
    "ttk.Notebook": "ctk.CTkTabview",
}

# Imports para remover/substituir
IMPORT_PATTERNS = [
    (r"from tkinter import ttk\b", ""),  # Remover import
    (r"import tkinter\.ttk as ttk\b", ""),  # Remover import
    (r"import tkinter\.ttk\b", ""),  # Remover import
]


def migrate_file(file_path: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Migra um arquivo de ttk para CTk.

    Returns:
        (n\u00famero de substitui\u00e7\u00f5es, lista de mudan\u00e7as)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        changes = []

        # Substituir widgets
        for ttk_widget, ctk_widget in TTK_TO_CTK_WIDGETS.items():
            pattern = re.compile(r"\b" + re.escape(ttk_widget) + r"\b")
            matches = pattern.findall(content)
            if matches:
                content = pattern.sub(ctk_widget, content)
                changes.append(f"  - {ttk_widget} \u2192 {ctk_widget} ({len(matches)}x)")

        # Remover imports ttk
        for pattern, replacement in IMPORT_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                changes.append(f"  - Removido import ttk ({len(matches)}x)")

        n_changes = len(changes)

        if not dry_run and n_changes > 0:
            file_path.write_text(content, encoding="utf-8")

        return n_changes, changes

    except Exception as e:
        return 0, [f"  ERRO: {e}"]


def main():
    dry_run = "--dry-run" in sys.argv
    src_dir = Path(__file__).parent.parent / "src"

    if not src_dir.exists():
        print(f"Erro: diret\u00f3rio {src_dir} n\u00e3o encontrado")
        return 1

    # Listar arquivos Python com ttk
    files_with_ttk = []
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"\bttk\.", content):
            files_with_ttk.append(py_file)

    print(f"=== MIGRA\u00c7\u00c3O TTK \u2192 CTK ({'DRY RUN' if dry_run else 'LIVE'}) ===")
    print(f"Arquivos com ttk encontrados: {len(files_with_ttk)}\n")

    total_changes = 0
    modified_files = []

    for file_path in files_with_ttk:
        n_changes, changes = migrate_file(file_path, dry_run=dry_run)

        if n_changes > 0:
            total_changes += n_changes
            modified_files.append(file_path)
            rel_path = file_path.relative_to(src_dir.parent)
            print(f"\u2705 {rel_path}")
            for change in changes:
                print(change)
            print()

    print("\n=== RESUMO ===")
    print(f"Arquivos modificados: {len(modified_files)}")
    print(f"Total de mudan\u00e7as: {total_changes}")

    if dry_run:
        print("\n\u26a0\ufe0f  DRY RUN - nenhum arquivo foi modificado")
        print("Execute sem --dry-run para aplicar mudan\u00e7as")

    return 0


if __name__ == "__main__":
    sys.exit(main())
