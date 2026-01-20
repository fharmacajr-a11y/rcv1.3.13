"""Script de migração automática TTK → CustomTkinter (Microfase 28).

Remove imports ttk e substitui widgets básicos por equivalentes CTk.
Executar com: python scripts/migrate_ttk_to_ctk.py --dry-run (preview)
              python scripts/migrate_ttk_to_ctk.py (aplica mudanças)
"""

import re
import sys
from pathlib import Path

# Mapeamento de substituições simples
REPLACEMENTS = [
    # Imports
    (r'^from tkinter import ttk\n', '', 're.MULTILINE'),
    (r'^import tkinter\.ttk as ttk\n', '', 're.MULTILINE'),
    
    # Widgets básicos (sem Treeview/Combobox/Progressbar - já migrados)
    (r'\bttk\.Frame\b', 'ctk.CTkFrame', 'plain'),
    (r'\bttk\.Label\b', 'ctk.CTkLabel', 'plain'),
    (r'\bttk\.Button\b', 'ctk.CTkButton', 'plain'),
    (r'\bttk\.Entry\b', 'ctk.CTkEntry', 'plain'),
    (r'\bttk\.Checkbutton\b', 'ctk.CTkCheckBox', 'plain'),
    (r'\bttk\.Radiobutton\b', 'ctk.CTkRadioButton', 'plain'),
    (r'\bttk\.Scrollbar\b', 'ctk.CTkScrollbar', 'plain'),
    
    # Separator → Frame fino
    (r'ttk\.Separator\([^,)]+,\s*orient\s*=\s*"horizontal"[^)]*\)', 
     'ctk.CTkFrame(\\1, height=2)', 'plain'),
]

# Arquivos a PULAR (Treeview complexos que precisam migração manual)
SKIP_FILES = {
    'ctk_tableview.py',
    'ctk_config.py',
    'ttk_compat.py',
    'lists.py',  # Manual - zebra complex
    'notifications_popup.py',  # Manual - dialog complex
    'file_list.py',  # Manual
    'passwords_screen.py',  # Manual
    'lixeira.py',  # Manual
    'client_passwords_dialog.py',  # Manual
}

def migrate_file(file_path: Path, dry_run: bool = True) -> tuple[bool, str]:
    """Migra um arquivo removendo ttk e substituindo widgets."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content
        
        # Verificar se tem ttk
        if 'from tkinter import ttk' not in content and 'import tkinter.ttk' not in content:
            return False, "Sem imports ttk"
        
        # Verificar se deve pular (Treeview etc)
        if any(skip in file_path.name for skip in SKIP_FILES):
            return False, f"PULADO: {file_path.name} (requer migração manual)"
        
        if 'ttk.Treeview' in content or 'ttk.Combobox' in content:
            return False, "PULADO: Contém Treeview/Combobox (manual)"
        
        # Aplicar substituições
        for pattern, replacement, mode in REPLACEMENTS:
            if mode == 're.MULTILINE':
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                content = content.replace(pattern, replacement)
        
        # Adicionar import CTk se ainda não existe
        if 'from src.ui.ctk_config import ctk' not in content:
            # Inserir após os imports padrão
            import_section = content.split('\n\n')[0]
            if 'from __future__ import annotations' in import_section:
                content = content.replace(
                    'from __future__ import annotations\n',
                    'from __future__ import annotations\n\nfrom src.ui.ctk_config import ctk\n',
                    1
                )
            else:
                content = f"from src.ui.ctk_config import ctk\n\n{content}"
        
        if content == original:
            return False, "Nenhuma mudança necessária"
        
        if not dry_run:
            file_path.write_text(content, encoding='utf-8')
            return True, "MIGRADO"
        else:
            return True, "SERIA MIGRADO (dry-run)"
            
    except Exception as e:
        return False, f"ERRO: {e}"

def main():
    dry_run = '--dry-run' in sys.argv
    src_dir = Path('src')
    
    migrated = []
    skipped = []
    errors = []
    
    for py_file in src_dir.rglob('*.py'):
        if py_file.name.startswith('__'):
            continue
            
        success, message = migrate_file(py_file, dry_run=dry_run)
        
        if success:
            migrated.append((py_file, message))
        elif 'ERRO' in message:
            errors.append((py_file, message))
        else:
            skipped.append((py_file, message))
    
    print(f"\n{'='*60}")
    print(f"MIGRACAO TTK -> CTK ({'DRY RUN' if dry_run else 'APLICADO'})")
    print(f"{'='*60}\n")
    
    if migrated:
        print(f"OK MIGRADOS ({len(migrated)}):")
        for f, msg in migrated:
            print(f"  - {f.relative_to('src')}: {msg}")
    
    if errors:
        print(f"\nERRO ({len(errors)}):")
        for f, msg in errors:
            print(f"  - {f.relative_to('src')}: {msg}")
    
    if skipped:
        print(f"\nPULADOS ({len(skipped)}):")
        for f, msg in skipped[:10]:  # Primeiros 10
            print(f"  - {f.relative_to('src')}: {msg}")
        if len(skipped) > 10:
            print(f"  ... e mais {len(skipped) - 10} arquivos")
    
    print(f"\n{'='*60}")
    print(f"Total: {len(migrated)} migrados, {len(skipped)} pulados, {len(errors)} erros")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
