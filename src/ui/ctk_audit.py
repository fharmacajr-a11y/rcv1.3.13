# -*- coding: utf-8 -*-
"""Script de auditoria para detectar mistura de tk/ttk no caminho CTk.

MICROFASE 35: Ferramenta para encontrar uso de widgets Tk/TTK que deveriam
ser CTk no código do Hub e outras views.

Uso:
    python -m src.ui.ctk_audit
    python -m src.ui.ctk_audit --fix  (mostra sugestões de correção)

Este script varre os arquivos Python em src/modules/hub/views e outros
diretórios especificados, procurando por padrões que indicam mistura
de widgets Tk/TTK em código que deveria usar apenas CustomTkinter.

Padrões detectados:
    - tk.Frame, tk.Label, tk.Button (dentro de contexto CTk)
    - ttk.* (dentro de contexto CTk)
    - ScrolledText (deveria ser CTkTextbox)
    - Uso de 'bg=' em vez de 'fg_color='
    - Uso de 'foreground=' em vez de 'text_color='
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple


class AuditResult(NamedTuple):
    """Resultado de auditoria de um arquivo."""
    file: str
    line_num: int
    line: str
    pattern: str
    suggestion: str


# Padrões a serem detectados com suas sugestões
AUDIT_PATTERNS = [
    # tk.* widgets (quando deveria ser CTk)
    (r'\btk\.Frame\b', 'tk.Frame', 'Use ctk.CTkFrame com fg_color'),
    (r'\btk\.Label\b', 'tk.Label', 'Use ctk.CTkLabel com text_color'),
    (r'\btk\.Button\b', 'tk.Button', 'Use ctk.CTkButton'),
    (r'\btk\.Entry\b', 'tk.Entry', 'Use ctk.CTkEntry'),
    (r'\btk\.Canvas\b', 'tk.Canvas', 'Use ctk.CTkCanvas ou CTkFrame'),
    (r'\btk\.Scrollbar\b', 'tk.Scrollbar', 'Desnecessário com CTkScrollableFrame'),
    (r'\btk\.Text\b', 'tk.Text', 'Use ctk.CTkTextbox'),
    (r'\btk\.LabelFrame\b', 'tk.LabelFrame', 'Use CTkFrame com border'),
    
    # ttk.* widgets
    (r'\bttk\.Frame\b', 'ttk.Frame', 'Use ctk.CTkFrame'),
    (r'\bttk\.Label\b', 'ttk.Label', 'Use ctk.CTkLabel'),
    (r'\bttk\.Button\b', 'ttk.Button', 'Use ctk.CTkButton'),
    (r'\bttk\.Entry\b', 'ttk.Entry', 'Use ctk.CTkEntry'),
    (r'\bttk\.Treeview\b', 'ttk.Treeview', 'Usar CTkTable ou manter TTK com tema'),
    (r'\bttk\.Scrollbar\b', 'ttk.Scrollbar', 'Desnecessário com CTk'),
    (r'\bttk\.LabelFrame\b', 'ttk.LabelFrame', 'Use CTkFrame com border'),
    
    # ScrolledText
    (r'\bScrolledText\b', 'ScrolledText', 'Use ctk.CTkTextbox'),
    
    # Atributos Tk em contexto CTk
    (r'\bbg\s*=', 'bg=', 'Use fg_color= para CTkFrame/CTkLabel'),
    (r'\bforeground\s*=', 'foreground=', 'Use text_color= para CTkLabel'),
    (r'\bbackground\s*=', 'background=', 'Use fg_color= para widgets CTk'),
    (r'\brelief\s*=', 'relief=', 'Não suportado em CTk, remover'),
    (r'\bbd\s*=', 'bd=', 'Use border_width= para CTkFrame'),
    (r'\bhighlightthickness\s*=', 'highlightthickness=', 'Não suportado em CTk'),
]

# Diretórios a serem auditados
AUDIT_DIRS = [
    'src/modules/hub/views',
    'src/ui',
]

# Arquivos a ignorar (ex: fallbacks legítimos)
IGNORE_FILES = [
    'ctk_audit.py',
    'ctk_config.py',
    'ctk_text_compat.py',
]

# Padrões que indicam fallback legítimo (não reportar)
FALLBACK_PATTERNS = [
    r'if not.*HAS_CUSTOMTKINTER',
    r'else:.*#.*fallback',
    r'# fallback',
    r'# Fallback',
]


def is_in_fallback_context(lines: list[str], line_idx: int) -> bool:
    """Verifica se a linha está em um contexto de fallback Tk legítimo.
    
    Args:
        lines: Todas as linhas do arquivo.
        line_idx: Índice da linha atual.
        
    Returns:
        True se estiver em contexto de fallback, False caso contrário.
    """
    # Verificar as últimas 5 linhas para contexto de fallback
    start = max(0, line_idx - 5)
    context = '\n'.join(lines[start:line_idx + 1])
    
    for pattern in FALLBACK_PATTERNS:
        if re.search(pattern, context, re.IGNORECASE):
            return True
    return False


def audit_file(filepath: Path, show_suggestions: bool = False) -> list[AuditResult]:
    """Audita um arquivo Python para uso de tk/ttk em contexto CTk.
    
    Args:
        filepath: Caminho do arquivo a auditar.
        show_suggestions: Se True, inclui sugestões de correção.
        
    Returns:
        Lista de resultados de auditoria.
    """
    results: list[AuditResult] = []
    
    # Ignorar arquivos na lista de exclusão
    if filepath.name in IGNORE_FILES:
        return results
    
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.splitlines()
    except Exception as e:
        print(f"⚠ Erro ao ler {filepath}: {e}", file=sys.stderr)
        return results
    
    # Verificar se o arquivo usa CTk (se não usa, não auditar)
    if 'HAS_CUSTOMTKINTER' not in content and 'ctk.' not in content:
        return results
    
    for line_num, line in enumerate(lines, 1):
        # Pular linhas de comentário e imports
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('from ') or stripped.startswith('import '):
            continue
        
        # Pular type hints e anotações de tipo
        if 'tk.Frame' in line or 'tk.Label' in line or 'tk.Button' in line:
            # Verificar se é type hint (: tk.Frame, -> tk.Frame, | tk.Frame)
            if re.search(r':\s*tk\.\w+|:\s*\w+\s*\|\s*tk\.\w+|->\s*tk\.\w+|->\s*\w+\s*\|\s*tk\.\w+', line):
                continue
            # Verificar se é definição de função/método com type hint
            if 'def ' in line or 'class ' in line:
                continue
            # Verificar se é atributo com type hint (self.xxx: tk.Frame)
            if re.search(r'self\.\w+:\s*tk\.\w+', line):
                continue
        
        # Pular docstrings e comentários inline
        if '"""' in line or "'''" in line:
            continue
        
        # Verificar cada padrão
        for pattern, name, suggestion in AUDIT_PATTERNS:
            if re.search(pattern, line):
                # Verificar se está em contexto de fallback
                if is_in_fallback_context(lines, line_num - 1):
                    continue
                
                results.append(AuditResult(
                    file=str(filepath),
                    line_num=line_num,
                    line=line.rstrip(),
                    pattern=name,
                    suggestion=suggestion if show_suggestions else '',
                ))
    
    return results


def audit_directory(dirpath: Path, show_suggestions: bool = False) -> list[AuditResult]:
    """Audita todos os arquivos Python em um diretório.
    
    Args:
        dirpath: Caminho do diretório a auditar.
        show_suggestions: Se True, inclui sugestões de correção.
        
    Returns:
        Lista de resultados de auditoria.
    """
    results: list[AuditResult] = []
    
    if not dirpath.exists():
        print(f"⚠ Diretório não encontrado: {dirpath}", file=sys.stderr)
        return results
    
    for filepath in dirpath.rglob('*.py'):
        results.extend(audit_file(filepath, show_suggestions))
    
    return results


def main() -> int:
    """Função principal do script de auditoria.
    
    Returns:
        Código de saída (0 = sucesso, 1 = problemas encontrados).
    """
    show_suggestions = '--fix' in sys.argv or '--suggest' in sys.argv
    
    print("=" * 70)
    print("🔍 CTk Audit - Detecção de mistura tk/ttk em código CustomTkinter")
    print("=" * 70)
    print()
    
    # Determinar diretório base
    base_dir = Path(__file__).parent.parent.parent  # src/../..
    
    all_results: list[AuditResult] = []
    
    for dir_rel in AUDIT_DIRS:
        dir_path = base_dir / dir_rel
        print(f"📁 Auditando: {dir_rel}")
        results = audit_directory(dir_path, show_suggestions)
        all_results.extend(results)
    
    print()
    
    if not all_results:
        print("✅ Nenhum problema encontrado!")
        return 0
    
    # Agrupar por arquivo
    by_file: dict[str, list[AuditResult]] = {}
    for result in all_results:
        by_file.setdefault(result.file, []).append(result)
    
    print(f"⚠ {len(all_results)} problemas encontrados em {len(by_file)} arquivo(s):")
    print()
    
    for filepath, results in sorted(by_file.items()):
        rel_path = Path(filepath).relative_to(base_dir)
        print(f"📄 {rel_path}")
        for result in sorted(results, key=lambda r: r.line_num):
            print(f"   L{result.line_num:4d}: {result.pattern:20s} | {result.line[:60]}...")
            if result.suggestion:
                print(f"         💡 {result.suggestion}")
        print()
    
    print("-" * 70)
    print(f"Total: {len(all_results)} ocorrências em {len(by_file)} arquivo(s)")
    print()
    print("Dica: Use --fix para ver sugestões de correção")
    print("      Linhas em contexto 'else: # fallback' são ignoradas")
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
