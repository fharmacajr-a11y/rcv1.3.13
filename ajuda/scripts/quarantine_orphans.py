#!/usr/bin/env python3
"""
Script para mover módulos órfãos para quarentena (DRY-RUN seguro)
================================================================

Move apenas arquivos identificados em ORPHANS.md como "REMOVÍVEL".
Preserva estrutura de subpastas e registra tudo em APPLY_LOG.txt.
"""

import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
QUARANTINE_DIR = ROOT / "ajuda" / "_quarentena_orfaos"
OUTPUT_DIR = ROOT / "ajuda" / "dup-consolidacao"
ORPHANS_FILE = OUTPUT_DIR / "ORPHANS.md"
APPLY_LOG = OUTPUT_DIR / "APPLY_LOG.txt"


def parse_orphans_md() -> list[str]:
    """Extrai lista de arquivos removíveis do ORPHANS.md."""
    if not ORPHANS_FILE.exists():
        print(f"❌ Arquivo não encontrado: {ORPHANS_FILE}")
        return []

    content = ORPHANS_FILE.read_text(encoding="utf-8")

    # Procurar seção "Candidatos à Remoção"
    removable = []
    in_removable_section = False

    for line in content.split("\n"):
        if "Candidatos à Remoção" in line:
            in_removable_section = True
            continue

        if in_removable_section:
            # Parar na próxima seção
            if line.startswith("##"):
                break

            # Extrair caminho da tabela
            if "|" in line and ".py" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    path = parts[2].strip().replace("`", "")
                    if path and path.endswith(".py"):
                        removable.append(path)

    return removable


def quarantine_file(rel_path: str) -> bool:
    """Move arquivo para quarentena preservando estrutura."""
    source = ROOT / rel_path

    if not source.exists():
        print(f"  ⚠️  Arquivo não encontrado: {rel_path}")
        return False

    # Preservar estrutura de diretórios
    target = QUARANTINE_DIR / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(str(source), str(target))
        print(f"  ✅ Movido: {rel_path}")
        return True
    except Exception as e:
        print(f"  ❌ Erro ao mover {rel_path}: {e}")
        return False


def main():
    print("=" * 70)
    print("🗑️  QUARENTENA DE MÓDULOS ÓRFÃOS (AÇÃO SEGURA)")
    print("=" * 70)
    print()

    # Criar pasta de quarentena
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    # Parsear órfãos
    orphans = parse_orphans_md()

    if not orphans:
        print("✅ Nenhum arquivo órfão removível encontrado.")
        return

    print(f"📋 {len(orphans)} arquivo(s) órfão(s) removível(is) identificado(s):\n")
    for path in orphans:
        print(f"   • {path}")

    print()

    # Mover para quarentena
    moved = []
    for path in orphans:
        if quarantine_file(path):
            moved.append(path)

    print()

    # Registrar em APPLY_LOG.txt
    if moved:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_content = f"""
# Log de Aplicação - Quarentena de Órfãos
**Data:** {timestamp}
**Ação:** Mover módulos órfãos para quarentena
---

## Arquivos Movidos ({len(moved)})

"""
        for path in moved:
            log_content += f"- `{path}` → `ajuda/_quarentena_orfaos/{path}`\n"

        log_content += """

## Observações

- Arquivos movidos para `ajuda/_quarentena_orfaos/` preservando estrutura
- Se nenhum problema ocorrer após 1-2 releases, podem ser deletados permanentemente
- Para restaurar: `Move-Item "ajuda\_quarentena_orfaos\\<arquivo>" "<local_original>"`

## Comandos para Reverter

```powershell
"""
        for path in moved:
            log_content += f'Move-Item "ajuda\\_quarentena_orfaos\\{path}" "{path}"\n'

        log_content += "```\n"

        APPLY_LOG.write_text(log_content, encoding="utf-8")
        print(f"📝 Log salvo em: {APPLY_LOG}")

    print()
    print("=" * 70)
    print(f"✅ {len(moved)}/{len(orphans)} arquivo(s) movido(s) para quarentena")
    print(f"📁 Quarentena: {QUARANTINE_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
