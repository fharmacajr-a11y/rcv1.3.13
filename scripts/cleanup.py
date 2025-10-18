# scripts/cleanup.py
"""
Script de consolidação e limpeza do projeto.
- Consolida material auxiliar em ./ajuda/
- Remove código legado não utilizado
- Gera log detalhado

Execute:
    python scripts/cleanup.py                # Dry-run (não modifica nada)
    python scripts/cleanup.py --apply        # Aplica as mudanças
    python scripts/cleanup.py --legacy-only  # Apenas limpeza de legados
"""
from __future__ import annotations
import argparse
import re
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
AJUDA = ROOT / "ajuda"
LOGFILE = AJUDA / "_consolidation_log.txt"

# Pastas/arquivos auxiliares que queremos mover para ./ajuda/
MOVE_DIRS = [
    "docs",
    "tests",
    "relays",
    "relay",
    "comandos",
    "commands",
]

# Arquivos soltos que normalmente são auxiliares
MOVE_FILES_GLOBS = [
    "README-Implantacao.txt",
    "POLIMENTO-VISUAL-GUIA.md",
    "PROMPT-*-CHANGES.md",
    "*quick*start*.*",
    "*QUICK*START*.*",
    "CHANGELOG*.md",
    "RELEASE-GUIDE.md",
    "release-commands.*",
    "release-curl-commands.*",
]

# Lixos seguros para remover
SAFE_DELETE_GLOBS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
]

# Pastas legadas sem uso
LEGACY_DIRS = [
    "infrastructure",
    "core/auth",
]


def log(msg: str, print_msg: bool = True):
    """Escreve mensagem no log e opcionalmente no console."""
    AJUDA.mkdir(exist_ok=True)
    with LOGFILE.open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")
    if print_msg:
        print(msg)


def has_import(target_module: str, exclude_ajuda: bool = True) -> bool:
    """Verifica se algum .py importa o módulo/pasta indicada."""
    mod = target_module.replace("/", ".").replace("\\", ".")

    for py in ROOT.rglob("*.py"):
        # Pula ajuda/ se solicitado
        if exclude_ajuda and str(AJUDA) in str(py):
            continue

        # Pula arquivos em pastas excluídas
        if any(
            excl in py.parts
            for excl in ["__pycache__", ".venv", "dist", "build", ".git"]
        ):
            continue

        try:
            txt = py.read_text(encoding="utf-8", errors="ignore")
            # Busca imports do tipo: from X import ... ou import X
            if re.search(
                rf"\bfrom\s+{re.escape(mod)}\b|\bimport\s+{re.escape(mod)}\b", txt
            ):
                return True
        except Exception:
            continue

    return False


def move_path(src: Path, dest_dir: Path, apply: bool) -> bool:
    """Move arquivo ou diretório para dest_dir."""
    if not src.exists():
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    # Evita mover para si mesmo
    if src.resolve() == dest.resolve():
        return False

    # Se destino já existe, pula
    if dest.exists():
        log(f"   ⏭️  PULAR: {src.relative_to(ROOT)} (destino já existe)")
        return False

    if apply:
        try:
            shutil.move(str(src), str(dest))
            log(f"   ✅ MOVIDO: {src.relative_to(ROOT)} → {dest.relative_to(ROOT)}")
            return True
        except Exception as e:
            log(f"   ❌ ERRO ao mover {src.name}: {e}")
            return False
    else:
        log(f"   🔍 MOVER: {src.relative_to(ROOT)} → {dest.relative_to(ROOT)}")
        return True


def remove_path(p: Path, apply: bool) -> bool:
    """Remove arquivo ou diretório."""
    if not p.exists():
        return False

    if apply:
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
            log(f"   ✅ REMOVIDO: {p.relative_to(ROOT)}")
            return True
        except Exception as e:
            log(f"   ❌ ERRO ao remover {p.name}: {e}")
            return False
    else:
        log(f"   🗑️  REMOVER: {p.relative_to(ROOT)}")
        return True


def consolidate_auxiliaries(apply: bool) -> dict:
    """Consolida material auxiliar em ./ajuda/"""
    stats = {"moved": 0, "removed": 0, "skipped": 0}

    log("\n" + "=" * 70)
    log(f"CONSOLIDAÇÃO DE AUXILIARES - {'APLICANDO' if apply else 'DRY-RUN'}")
    log("=" * 70)
    log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1) Mover pastas auxiliares (se não forem importadas)
    log("\n📁 VERIFICANDO PASTAS AUXILIARES...")
    for d in MOVE_DIRS:
        src = ROOT / d
        if not src.exists():
            continue

        if src.name == "scripts":
            # Scripts: preservar cleanup.py na raiz, mover o resto
            log(f"\n   📂 {d}/ (mover conteúdo, manter cleanup.py)")
            scripts_dest = AJUDA / "scripts"
            scripts_dest.mkdir(parents=True, exist_ok=True)

            for item in src.iterdir():
                if item.name == "cleanup.py":
                    log("   ⏭️  MANTER: scripts/cleanup.py (executável principal)")
                    continue
                if move_path(item, scripts_dest, apply):
                    stats["moved"] += 1
        else:
            # Verifica se é importado
            if has_import(d):
                log(f"\n   ⚠️  MANTER: {d}/ (há imports ativos)")
                stats["skipped"] += 1
            else:
                log(f"\n   📂 {d}/")
                if move_path(src, AJUDA, apply):
                    stats["moved"] += 1

    # 2) Mover arquivos auxiliares por glob
    log("\n📄 VERIFICANDO ARQUIVOS AUXILIARES...")
    for pat in MOVE_FILES_GLOBS:
        for f in ROOT.glob(pat):
            if not f.is_file():
                continue
            if f.parent == AJUDA or AJUDA in f.parents:
                continue

            if move_path(f, AJUDA, apply):
                stats["moved"] += 1

    # 3) Lixos seguros
    log("\n🗑️  REMOVENDO LIXO...")
    for pat in SAFE_DELETE_GLOBS:
        for p in ROOT.glob(pat):
            # Nunca limpar dentro de ajuda, .venv, etc
            if any(
                excl in p.parts for excl in ["ajuda", ".venv", "dist", "build", ".git"]
            ):
                continue

            if remove_path(p, apply):
                stats["removed"] += 1

    return stats


def cleanup_legacy(apply: bool) -> dict:
    """Remove pastas legadas sem uso."""
    stats = {"removed": 0, "skipped": 0}

    log("\n" + "=" * 70)
    log(f"LIMPEZA DE CÓDIGO LEGADO - {'APLICANDO' if apply else 'DRY-RUN'}")
    log("=" * 70)

    for legacy in LEGACY_DIRS:
        ldir = ROOT / legacy
        if not ldir.exists():
            continue

        log(f"\n🔍 Verificando: {legacy}/")

        if has_import(legacy, exclude_ajuda=False):
            log(f"   ⚠️  MANTER: {legacy}/ (há imports ativos)")
            stats["skipped"] += 1
        else:
            log("   ✅ Sem imports ativos")
            if remove_path(ldir, apply):
                stats["removed"] += 1

    return stats


def print_summary(stats_consolidate: dict, stats_legacy: dict, apply: bool):
    """Imprime resumo da operação."""
    log("\n" + "=" * 70)
    log("📊 RESUMO DA OPERAÇÃO")
    log("=" * 70)

    total_moved = stats_consolidate["moved"]
    total_removed = stats_consolidate["removed"] + stats_legacy["removed"]
    total_skipped = stats_consolidate["skipped"] + stats_legacy["skipped"]

    log(f"   📦 Itens movidos para ajuda/: {total_moved}")
    log(f"   🗑️  Itens removidos: {total_removed}")
    log(f"   ⏭️  Itens mantidos: {total_skipped}")

    if not apply:
        log("\n⚠️  MODO DRY-RUN: Nenhuma mudança foi aplicada")
        log("   Execute com --apply para aplicar as mudanças")
    else:
        log("\n✅ MUDANÇAS APLICADAS COM SUCESSO!")

    log(f"\n📝 Log completo: {LOGFILE.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(
        description="Consolida arquivos auxiliares em ./ajuda/ e remove código legado"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica as mudanças (sem --apply é dry-run)",
    )
    parser.add_argument(
        "--legacy-only",
        action="store_true",
        help="Apenas remove código legado (não consolida auxiliares)",
    )
    args = parser.parse_args()

    # Limpa log anterior
    if LOGFILE.exists():
        LOGFILE.unlink(missing_ok=True)

    print("=" * 70)
    print("🧹 SCRIPT DE CONSOLIDAÇÃO E LIMPEZA")
    print("=" * 70)

    if not args.apply:
        print("\n⚠️  MODO DRY-RUN (apenas visualização)")
        print("   Nenhuma mudança será aplicada")
        print("   Use --apply para aplicar as mudanças de verdade")
    else:
        print("\n✅ MODO APLICAÇÃO")
        print("   As mudanças serão aplicadas!")

    # Executa operações
    if args.legacy_only:
        print("\n🔍 Apenas limpeza de código legado...")
        stats_consolidate = {"moved": 0, "removed": 0, "skipped": 0}
        stats_legacy = cleanup_legacy(args.apply)
    else:
        stats_consolidate = consolidate_auxiliaries(args.apply)
        stats_legacy = cleanup_legacy(args.apply)

    # Resumo
    print_summary(stats_consolidate, stats_legacy, args.apply)

    print("\n" + "=" * 70)
    print("✅ OPERAÇÃO CONCLUÍDA!")
    print("=" * 70)

    if not args.apply:
        print("\n💡 Próximos passos:")
        print("   1. Revise o log: ajuda/_consolidation_log.txt")
        print("   2. Execute com --apply se estiver OK")
        print("   3. Teste o app: python app_gui.py")
    else:
        print("\n💡 Próximos passos:")
        print("   1. Teste o app: python app_gui.py")
        print("   2. Build: pyinstaller build/rc_gestor.spec")
        print("   3. Commit: git add . && git commit")


if __name__ == "__main__":
    main()
