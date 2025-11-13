"""
Análise de erros do Pyright para CompatPack-01.
Filtra apenas erros (não warnings) em src/, infra/, adapters/.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

# Carregar relatório
try:
    with open('devtools/qa/pyright.json', encoding='utf-8') as f:
        data: Dict[str, Any] = json.load(f)
except UnicodeDecodeError:
    with open('devtools/qa/pyright.json', encoding='utf-16') as f:
        data = json.load(f)

# Filtrar diagnósticos
errors_by_file: Dict[str, List[Dict[str, Any]]] = {}
total_errors = 0
total_warnings = 0

for diag in data.get('generalDiagnostics', []):
    file_path = diag['file']
    severity = diag['severity']
    
    # Contar totais
    if severity == 'error':
        total_errors += 1
    elif severity == 'warning':
        total_warnings += 1
    
    # Filtrar apenas errors em src/infra/adapters
    if severity != 'error':
        continue
    
    # Verificar se está nos diretórios de interesse
    path_lower = file_path.lower().replace('\\', '/')
    if not any(x in path_lower for x in ['/src/', '/infra/', '/adapters/']):
        continue
    
    # Ignorar tests e devtools
    if '/tests/' in path_lower or '/devtools/' in path_lower:
        continue
    
    # Extrair path relativo
    if 'v1.1.31 - Copia' in file_path:
        rel_path = file_path.split('v1.1.31 - Copia\\')[-1]
    else:
        rel_path = Path(file_path).name
    
    if rel_path not in errors_by_file:
        errors_by_file[rel_path] = []
    
    errors_by_file[rel_path].append({
        'line': diag['range']['start']['line'] + 1,  # 0-indexed → 1-indexed
        'message': diag['message'],
        'rule': diag.get('rule', 'unknown')
    })

# Imprimir resumo
print("=" * 80)
print("ANÁLISE PYRIGHT - COMPATPACK-01")
print("=" * 80)
print(f"\nTotal Pyright diagnostics: {total_errors + total_warnings}")
print(f"  Errors: {total_errors}")
print(f"  Warnings: {total_warnings}")

print(f"\nErrors em src/infra/adapters: {sum(len(v) for v in errors_by_file.values())}")
print(f"Arquivos afetados: {len(errors_by_file)}\n")

# Listar por arquivo
for file_path in sorted(errors_by_file.keys()):
    errors = errors_by_file[file_path]
    print(f"\n📁 {file_path} ({len(errors)} errors)")
    for err in errors[:10]:  # Limitar a 10 por arquivo
        print(f"   L{err['line']}: {err['message'][:80]}")
        if len(err['message']) > 80:
            print(f"           {err['message'][80:160]}")
    if len(errors) > 10:
        print(f"   ... e mais {len(errors) - 10} erros")

print("\n" + "=" * 80)
