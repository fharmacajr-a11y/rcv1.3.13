#!/usr/bin/env python3
"""Script para corrigir automaticamente argumentos inválidos em CTkFrame."""

import re
import os
from pathlib import Path

def fix_ctk_frame_padding(content: str) -> str:
    """Remove padding= de CTkFrame calls e sugere alternativas."""
    
    # Padrão: CTkFrame(parent, padding=valor)
    pattern = r'ctk\.CTkFrame\(([^)]+),\s*padding=([^,)]+)\)'
    
    def replace_padding(match):
        parent = match.group(1).strip()
        padding_val = match.group(2).strip()
        # Remover padding e deixar comentário
        return f'ctk.CTkFrame({parent})  # TODO: padding={padding_val} -> usar padx/pady no pack/grid'
    
    return re.sub(pattern, replace_padding, content, flags=re.IGNORECASE)

def fix_ctk_frame_text(content: str) -> str:
    """Remove text= de CTkFrame calls."""
    
    # Padrão: CTkFrame(parent, text=valor) 
    pattern = r'ctk\.CTkFrame\(([^)]+),\s*text=([^,)]+)\)'
    
    def replace_text(match):
        parent = match.group(1).strip()
        text_val = match.group(2).strip()
        return f'ctk.CTkFrame({parent})  # TODO: text={text_val} -> usar CTkLabel separado'
    
    return re.sub(pattern, replace_text, content, flags=re.IGNORECASE)

def fix_ctk_frame_orient(content: str) -> str:
    """Remove orient= de CTkFrame calls."""
    
    # Padrão: CTkFrame(parent, orient=valor)
    pattern = r'ctk\.CTkFrame\(([^)]+),\s*orient=([^,)]+)\)'
    
    def replace_orient(match):
        parent = match.group(1).strip()
        orient_val = match.group(2).strip()
        if 'horizontal' in orient_val.lower():
            return f'ctk.CTkFrame({parent}, height=2)  # Separador horizontal'
        else:
            return f'ctk.CTkFrame({parent}, width=2)  # Separador vertical'
    
    return re.sub(pattern, replace_orient, content, flags=re.IGNORECASE)

def process_file(file_path: Path) -> bool:
    """Processa um arquivo Python, retorna True se foi modificado."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Aplicar correções
        content = original_content
        content = fix_ctk_frame_padding(content)
        content = fix_ctk_frame_text(content)
        content = fix_ctk_frame_orient(content)
        
        if content != original_content:
            print(f"🔧 CORRIGINDO: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
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