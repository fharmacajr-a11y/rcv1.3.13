#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_runtime.py — Monta a pasta runtime/ com apenas o necessário para execução.

Uso:
    python scripts/make_runtime.py              # dry-run (apenas lista)
    python scripts/make_runtime.py --apply      # copia de verdade

Regras:
- Não apaga nada do projeto original
- Não altera código de produção
- Não move .env
- Não toca no .spec
"""
import argparse
import shutil
import sys
from pathlib import Path
import fnmatch

try:
    import yaml
except ImportError:
    print("❌ PyYAML não encontrado. Instale com: pip install pyyaml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
MANIFEST = ROOT / "config" / "runtime_manifest.yaml"


def load_manifest():
    """Carrega o manifesto YAML com includes/excludes."""
    if not MANIFEST.exists():
        print(f"❌ Manifesto não encontrado: {MANIFEST}")
        sys.exit(1)

    cfg = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    inc = cfg.get("include", [])
    exc = cfg.get("exclude", [])
    white = set(cfg.get("whitelist_scripts", []))
    return inc, exc, white


def match_any(path, patterns):
    """Verifica se o path bate com algum pattern (suporta globs)."""
    rp = str(path.as_posix())
    return any(fnmatch.fnmatch(rp, p) for p in patterns)


def iter_included(inc_patterns, exc_patterns):
    """
    Itera sobre os arquivos incluídos segundo os patterns.
    Varre apenas o que está nos includes, depois filtra excludes.
    """
    seen = set()
    for pat in inc_patterns:
        for p in ROOT.glob(pat):
            if p.is_dir():
                # Recursivo em subpastas
                for sub in p.rglob("*"):
                    if sub.is_file():
                        rel = sub.relative_to(ROOT)
                        if rel not in seen and not match_any(rel, exc_patterns):
                            seen.add(rel)
                            yield sub
            elif p.is_file():
                rel = p.relative_to(ROOT)
                if rel not in seen and not match_any(rel, exc_patterns):
                    seen.add(rel)
                    yield p


def main():
    ap = argparse.ArgumentParser(
        description="Monta a pasta runtime/ com apenas o necessário para execução."
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Aplica a cópia (por padrão, apenas dry-run)",
    )
    args = ap.parse_args()

    print(f"📁 Raiz do projeto: {ROOT}")
    print(f"📋 Manifesto: {MANIFEST}")
    print()

    # Carrega configuração
    inc, exc, white = load_manifest()

    # Coleta arquivos
    files = sorted(set(iter_included(inc, exc)))

    # Remove scripts whitelisted (eles não vão pro runtime por engano)
    files = [f for f in files if str(f.relative_to(ROOT)) not in white]

    print(f"✅ Arquivos selecionados: {len(files)}")
    print()

    if not args.apply:
        print("🔍 DRY-RUN (use --apply para copiar de verdade)")
        print()

    total_size = 0
    for f in files:
        rel = f.relative_to(ROOT)
        dst = RUNTIME / rel
        size = f.stat().st_size
        total_size += size

        print(f"  {'✓' if args.apply else '→'} {rel}")

        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)

    # Estatísticas
    print()
    print(f"📊 Total: {len(files)} arquivos ({total_size / 1024:.1f} KB)")

    if args.apply:
        # Cria README de runtime
        readme_content = f"""Runtime gerado automaticamente por make_runtime.py
========================================================

Data: {Path(__file__).stat().st_mtime}
Arquivos: {len(files)}
Tamanho: {total_size / 1024:.1f} KB

Esta pasta contém apenas o necessário para executar o aplicativo,
sem testes, documentação, scripts de build, etc.

Para executar:
    python app_gui.py

ATENÇÃO: Configure o arquivo .env na raiz do projeto antes de executar.
"""
        (RUNTIME / "README-RUNTIME.txt").write_text(readme_content, encoding="utf-8")

        print()
        print(f"✅ Runtime gerado com sucesso em: {RUNTIME}")
        print()
        print("Para testar:")
        print(f"  cd {RUNTIME}")
        print("  python app_gui.py")
    else:
        print()
        print("💡 Para aplicar as mudanças, execute:")
        print("  python scripts/make_runtime.py --apply")

    return 0


if __name__ == "__main__":
    sys.exit(main())
