#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard anti-regressão: impede novos imports de clientes_v2.

Este script varre src/ e tests/ procurando por referências a clientes_v2
(exceto o próprio shim em src/modules/clientes_v2).

Uso:
    python tools/check_no_clientes_v2_imports.py

Retorna:
    - Exit code 0 se nenhuma referência encontrada
    - Exit code 1 se encontrar qualquer referência (com lista de arquivos/linhas)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_clientes_v2_references(root_path: Path) -> List[Tuple[Path, int, str]]:
    """Encontra todas as referências a clientes_v2 no código.
    
    Args:
        root_path: Diretório raiz para busca
        
    Returns:
        Lista de tuplas (arquivo, linha_num, conteúdo_linha)
    """
    # Padrões para detectar imports/referências de clientes_v2
    patterns = [
        re.compile(r'from\s+src\.modules\.clientes_v2'),
        re.compile(r'import\s+src\.modules\.clientes_v2'),
        re.compile(r'from\s+modules\.clientes_v2'),
        re.compile(r'"src\.modules\.clientes_v2'),
        re.compile(r"'src\.modules\.clientes_v2"),
    ]
    
    # Diretórios a excluir da busca
    excluded_dirs = {
        '__pycache__',
        '.git',
        '.venv',
        'venv',
        'node_modules',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        'htmlcov',
        'dist',
        'build',
        '.eggs',
    }
    
    # Caminho do shim (permitido ter referências)
    shim_path = root_path / 'src' / 'modules' / 'clientes_v2'
    
    matches = []
    
    # Buscar em src/ e tests/
    search_dirs = [root_path / 'src', root_path / 'tests']
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        for py_file in search_dir.rglob('*.py'):
            # Pular se estiver no shim ou em diretórios excluídos
            if shim_path in py_file.parents:
                continue
                
            if any(excluded_dir in py_file.parts for excluded_dir in excluded_dirs):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, start=1):
                        # Verificar se algum padrão coincide
                        for pattern in patterns:
                            if pattern.search(line):
                                matches.append((py_file, line_num, line.strip()))
                                break  # Uma match por linha é suficiente
            except (UnicodeDecodeError, PermissionError):
                # Ignorar arquivos que não podem ser lidos
                continue
    
    return matches


def main() -> int:
    """Executa a verificação e retorna exit code apropriado."""
    workspace_root = Path(__file__).parent.parent
    
    print("🔍 Verificando referências a clientes_v2 em src/ e tests/...")
    print(f"📁 Workspace: {workspace_root}")
    print()
    
    matches = find_clientes_v2_references(workspace_root)
    
    if not matches:
        print("✅ SUCESSO: Nenhuma referência a clientes_v2 encontrada!")
        print("   (clientes_v2 foi removido definitivamente)")
        return 0
    
    # Encontrou referências - listar e falhar
    print(f"❌ FALHA: Encontradas {len(matches)} referência(s) a clientes_v2:")
    print()
    
    # Agrupar por arquivo para melhor legibilidade
    by_file = {}
    for file_path, line_num, line_content in matches:
        rel_path = file_path.relative_to(workspace_root)
        if rel_path not in by_file:
            by_file[rel_path] = []
        by_file[rel_path].append((line_num, line_content))
    
    for rel_path, lines in sorted(by_file.items()):
        print(f"📄 {rel_path}")
        for line_num, line_content in lines:
            print(f"   Linha {line_num}: {line_content}")
        print()
    
    print("⚠️  AÇÃO NECESSÁRIA:")
    print("   1. Substituir 'src.modules.clientes_v2' por 'src.modules.clientes.ui'")
    print("   2. Atualizar imports para usar o novo caminho")
    print("   3. Re-executar este script até passar")
    print()
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
