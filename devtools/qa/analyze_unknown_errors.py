"""
Análise de erros Unknown do Pyright para CompatPack-04.
Filtra apenas erros relacionados a Unknown types em src/ui e src/core/services.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

# Carregar relatório
try:
    with open("devtools/qa/pyright.json", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
except UnicodeDecodeError:
    with open("devtools/qa/pyright.json", encoding="utf-16") as f:
        data = json.load(f)

# Palavras-chave para identificar erros relacionados a Unknown
UNKNOWN_KEYWORDS = [
    "Unknown",
    "partially unknown",
    "type is Unknown",
]

# Filtrar diagnósticos
unknown_errors_by_file: Dict[str, List[Dict[str, Any]]] = {}
total_errors = 0
total_unknown_errors = 0

# Arquivos prioritários (forms, pipeline, lixeira_service)
PRIORITY_FILES = [
    "forms.py",
    "pipeline.py",
    "lixeira_service.py",
]

for diag in data.get("generalDiagnostics", []):
    file_path = diag["file"]
    severity = diag["severity"]

    # Contar totais
    if severity == "error":
        total_errors += 1

    # Filtrar apenas errors
    if severity != "error":
        continue

    # Verificar se está nos diretórios de interesse
    path_lower = file_path.lower().replace("\\", "/")
    if not any(x in path_lower for x in ["/src/ui/", "/src/core/services/"]):
        continue

    # Ignorar tests e devtools
    if "/tests/" in path_lower or "/devtools/" in path_lower:
        continue

    # Verificar se mensagem contém palavras-chave de Unknown
    message = diag["message"]
    if not any(keyword in message for keyword in UNKNOWN_KEYWORDS):
        continue

    total_unknown_errors += 1

    # Extrair path relativo
    if "v1.1.31 - Copia" in file_path:
        rel_path = file_path.split("v1.1.31 - Copia\\")[-1]
    else:
        rel_path = Path(file_path).name

    if rel_path not in unknown_errors_by_file:
        unknown_errors_by_file[rel_path] = []

    unknown_errors_by_file[rel_path].append(
        {
            "line": diag["range"]["start"]["line"] + 1,  # 0-indexed → 1-indexed
            "message": message,
            "rule": diag.get("rule", "unknown"),
        }
    )

# Imprimir resumo
print("=" * 80)
print("ANÁLISE PYRIGHT - COMPATPACK-04 (Unknown types)")
print("=" * 80)
print(f"\nTotal Pyright errors: {total_errors}")
print(f"Unknown-related errors in src/ui and src/core/services: {total_unknown_errors}")
print(f"Arquivos afetados: {len(unknown_errors_by_file)}\n")

# Listar arquivos prioritários primeiro
print("=== ARQUIVOS PRIORITÁRIOS ===\n")
for priority_file in PRIORITY_FILES:
    for file_path in sorted(unknown_errors_by_file.keys()):
        if priority_file in file_path.lower():
            errors = unknown_errors_by_file[file_path]
            print(f"\n📁 {file_path} ({len(errors)} Unknown errors)")
            for err in errors[:5]:  # Limitar a 5 por arquivo
                print(f"   L{err['line']}: {err['message'][:100]}")
                if len(err["message"]) > 100:
                    print(f"           {err['message'][100:200]}")
            if len(errors) > 5:
                print(f"   ... e mais {len(errors) - 5} erros")

# Listar outros arquivos
print("\n\n=== OUTROS ARQUIVOS ===\n")
for file_path in sorted(unknown_errors_by_file.keys()):
    if not any(pf in file_path.lower() for pf in PRIORITY_FILES):
        errors = unknown_errors_by_file[file_path]
        print(f"\n📁 {file_path} ({len(errors)} Unknown errors)")
        for err in errors[:3]:  # Limitar a 3 por arquivo
            print(f"   L{err['line']}: {err['message'][:100]}")
        if len(errors) > 3:
            print(f"   ... e mais {len(errors) - 3} erros")

print("\n" + "=" * 80)
print(f"Total: {total_unknown_errors} Unknown-related errors")
print("Target para CompatPack-04: 10 erros mais fáceis (forms, pipeline, lixeira)")
print("=" * 80)
