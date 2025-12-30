"""
Script reutilizável para selecionar módulos com 0% de cobertura para batches de testes.
Uso: python scripts/pick_coverage_batch.py <batch_number> [min_stmts] [max_stmts]
Exemplo: python scripts/pick_coverage_batch.py 3
         python scripts/pick_coverage_batch.py 4 50 100
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def normalize_module_path(line: str) -> str:
    """Normaliza path de módulo para comparação (backslash -> ponto, slash -> ponto)."""
    return line.strip().replace("\\", ".").replace("/", ".")


def to_import_path(file_path: str) -> str:
    """Converte caminho de arquivo para import path Python."""
    p = file_path.replace("\\", "/").replace(".py", "")
    if p.endswith("/__init__"):
        p = p[:-9]
    return p.replace("/", ".")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/pick_coverage_batch.py <batch_number> [min_stmts] [max_stmts]")
        sys.exit(1)

    batch_num = int(sys.argv[1])
    min_stmts = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    max_stmts = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    # Configuração: incluir src/ui/ ?
    include_ui = os.environ.get("RC_BATCH_INCLUDE_UI", "0") == "1"

    cov_json = Path("reports/coverage.json")
    if not cov_json.exists():
        print(f"ERRO: {cov_json} não encontrado")
        sys.exit(1)

    data = json.loads(cov_json.read_text(encoding="utf-8"))

    # Módulos já usados em batches anteriores
    done = set()
    for p in Path("reports/inspecao").glob("batch*_modules.txt"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(normalize_module_path(line))

    print(f"Módulos já usados em batches anteriores: {len(done)}")

    # Selecionar candidatos
    files = []
    for path, payload in data.get("files", {}).items():
        summ = (payload or {}).get("summary", {}) or {}
        pct = float(summ.get("percent_covered", 0.0) or 0.0)
        stmts = int(summ.get("num_statements", 0) or 0)

        if pct == 0.0 and min_stmts <= stmts <= max_stmts:
            p_lower = path.lower().replace("\\", "/")

            # Ignorar tests, venv, pycache
            if any(x in p_lower for x in ["/tests/", "test_", ".venv", "__pycache__"]):
                continue

            # Excluir src/ui/ a não ser que explicitamente permitido
            if not include_ui and "src/ui/" in p_lower:
                continue

            # Converter para import path
            imp = to_import_path(path)

            if imp in done:
                continue

            files.append((stmts, path, imp))

    print(f"Candidatos encontrados ({min_stmts}-{max_stmts} stmts): {len(files)}")

    # Se não tiver 25, ampliar automaticamente para 16-80
    if len(files) < 25 and max_stmts == 50:
        print("Menos de 25 módulos. Ampliando para 16-80 statements...")
        return main_with_extended_range(batch_num, min_stmts, 80, done, include_ui)

    # Ordenar por statements (menores primeiro) e pegar até 25
    files.sort(key=lambda t: (t[0], t[1]))
    batch = files[:25]

    if not batch:
        print(f"✗ Nenhum módulo 0% encontrado com {min_stmts}-{max_stmts} statements")
        sys.exit(0)

    # Salvar arquivos
    Path("reports/inspecao").mkdir(parents=True, exist_ok=True)

    modules_file = Path(f"reports/inspecao/batch{batch_num:02d}_modules.txt")
    table_file = Path(f"reports/inspecao/batch{batch_num:02d}_table.md")

    modules_file.write_text("\n".join([imp for _, _, imp in batch]) + "\n", encoding="utf-8")

    # Criar tabela markdown
    lines = [
        f"# Batch {batch_num:02d} - Módulos 0% ({min_stmts}-{max_stmts} statements)",
        "",
        "| Stmts | Arquivo | Import Path |",
        "|---:|---|---|",
    ]
    for stmts, fpath, imp in batch:
        lines.append(f"| {stmts} | {fpath} | `{imp}` |")

    table_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ Selecionados {len(batch)} módulos (batch{batch_num:02d})")
    print(f"✓ {modules_file}")
    print(f"✓ {table_file}")


def main_with_extended_range(batch_num: int, min_stmts: int, max_stmts: int, done: set, include_ui: bool) -> None:
    """Re-executa a seleção com range estendido."""
    cov_json = Path("reports/coverage.json")
    data = json.loads(cov_json.read_text(encoding="utf-8"))

    files = []
    for path, payload in data.get("files", {}).items():
        summ = (payload or {}).get("summary", {}) or {}
        pct = float(summ.get("percent_covered", 0.0) or 0.0)
        stmts = int(summ.get("num_statements", 0) or 0)

        if pct == 0.0 and min_stmts <= stmts <= max_stmts:
            p_lower = path.lower().replace("\\", "/")

            if any(x in p_lower for x in ["/tests/", "test_", ".venv", "__pycache__"]):
                continue

            if not include_ui and "src/ui/" in p_lower:
                continue

            imp = to_import_path(path)

            if imp in done:
                continue

            files.append((stmts, path, imp))

    print(f"Candidatos com range estendido ({min_stmts}-{max_stmts} stmts): {len(files)}")

    files.sort(key=lambda t: (t[0], t[1]))
    batch = files[:25]

    if not batch:
        print(f"✗ Nenhum módulo 0% encontrado mesmo com {min_stmts}-{max_stmts} statements")
        sys.exit(0)

    # Salvar arquivos
    Path("reports/inspecao").mkdir(parents=True, exist_ok=True)

    modules_file = Path(f"reports/inspecao/batch{batch_num:02d}_modules.txt")
    table_file = Path(f"reports/inspecao/batch{batch_num:02d}_table.md")

    modules_file.write_text("\n".join([imp for _, _, imp in batch]) + "\n", encoding="utf-8")

    lines = [
        f"# Batch {batch_num:02d} - Módulos 0% ({min_stmts}-{max_stmts} statements)",
        "",
        "| Stmts | Arquivo | Import Path |",
        "|---:|---|---|",
    ]
    for stmts, fpath, imp in batch:
        lines.append(f"| {stmts} | {fpath} | `{imp}` |")

    table_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ Selecionados {len(batch)} módulos (batch{batch_num:02d})")
    print(f"✓ {modules_file}")
    print(f"✓ {table_file}")


if __name__ == "__main__":
    main()
