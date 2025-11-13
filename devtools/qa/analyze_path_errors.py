"""
Análise de erros Path/PathLike do Pyright para CompatPack-03.
Filtra apenas erros relacionados a Path, str, PathLike em src/, infra/, adapters/.
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

# Palavras-chave para identificar erros relacionados a Path
PATH_KEYWORDS = [
    'Path',
    'PathLike',
    '__fspath__',
    'os.fspath',
    'pathlib',
]

# Filtrar diagnósticos
path_errors_by_file: Dict[str, List[Dict[str, Any]]] = {}
total_errors = 0
total_path_errors = 0

for diag in data.get('generalDiagnostics', []):
    file_path = diag['file']
    severity = diag['severity']

    # Contar totais
    if severity == 'error':
        total_errors += 1

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

    # Verificar se mensagem contém palavras-chave de Path
    message = diag['message']
    if not any(keyword in message for keyword in PATH_KEYWORDS):
        continue

    total_path_errors += 1

    # Extrair path relativo
    if 'v1.1.31 - Copia' in file_path:
        rel_path = file_path.split('v1.1.31 - Copia\\')[-1]
    else:
        rel_path = Path(file_path).name

    if rel_path not in path_errors_by_file:
        path_errors_by_file[rel_path] = []

    path_errors_by_file[rel_path].append({
        'line': diag['range']['start']['line'] + 1,  # 0-indexed → 1-indexed
        'message': message,
        'rule': diag.get('rule', 'unknown')
    })

# Imprimir resumo
print("=" * 80)
print("ANÁLISE PYRIGHT - COMPATPACK-03 (Path/PathLike errors)")
print("=" * 80)
print(f"\nTotal Pyright errors: {total_errors}")
print(f"Path-related errors in src/infra/adapters: {total_path_errors}")
print(f"Arquivos afetados: {len(path_errors_by_file)}\n")

# Listar por arquivo
for file_path in sorted(path_errors_by_file.keys()):
    errors = path_errors_by_file[file_path]
    print(f"\n📁 {file_path} ({len(errors)} Path errors)")
    for err in errors:
        print(f"   L{err['line']}: {err['message']}")
        print()

print("=" * 80)
print(f"Total: {total_path_errors} Path-related errors a corrigir")
print("=" * 80)
