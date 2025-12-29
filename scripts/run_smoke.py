#!/usr/bin/env python3
"""Runner para suíte de testes smoke.

Lê nodeids de scripts/suites/smoke_nodeids.txt e executa pytest.

Uso:
    python scripts/run_smoke.py           # Roda os testes
    python scripts/run_smoke.py --dry-run # Apenas mostra o comando
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def load_nodeids(filepath: Path) -> list[str]:
    """Carrega nodeids do arquivo, ignorando comentários e linhas vazias."""
    nodeids: list[str] = []
    if not filepath.exists():
        print(f"ERRO: Arquivo não encontrado: {filepath}")
        sys.exit(1)

    with filepath.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Ignorar linhas vazias e comentários
            if not stripped or stripped.startswith("#"):
                continue
            nodeids.append(stripped)

    return nodeids


def main() -> int:
    """Executa a suíte smoke."""
    # Determinar paths
    script_dir = Path(__file__).parent
    nodeids_file = script_dir / "suites" / "smoke_nodeids.txt"
    project_root = script_dir.parent

    # Carregar nodeids
    nodeids = load_nodeids(nodeids_file)
    if not nodeids:
        print("ERRO: Nenhum nodeid encontrado no arquivo.")
        return 1

    print(f"[smoke] Carregados {len(nodeids)} nodeids de {nodeids_file.name}")

    # Montar comando
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-x",
        "--tb=short",
        *nodeids,
    ]

    # Verificar --dry-run
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("\n[dry-run] Comando que seria executado:")
        print(" ".join(cmd))
        return 0

    # Executar pytest
    print(f"\n[smoke] Executando pytest com {len(nodeids)} nodeids...")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=project_root)  # noqa: S603

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
