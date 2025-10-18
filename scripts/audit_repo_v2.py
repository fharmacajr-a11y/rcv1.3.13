# -*- coding: utf-8 -*-
"""
Gera relatórios de limpeza (sem deletar), com:
- duplicados por hash (sha256) + tamanho
- arquivos 'stale' por época de modificação
- itens que NÃO entram no runtime (não copiados pelo manifesto)
- top N maiores arquivos + estatísticas por pasta de 1º nível
Saídas:
  ajuda/CLEANUP_PLAN.json
  ajuda/CLEANUP_PLAN.md
Requisitos: PyYAML (já instalado), Python 3.10+
"""
from __future__ import annotations
import argparse
import json
import os
import time
import fnmatch
import hashlib
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
AJUDA = ROOT / "ajuda"
MANIFEST = ROOT / "config" / "runtime_manifest.yaml"
RUNTIME = ROOT / "runtime"

SKIP_DIRS = {
    ".venv",
    "dist",
    "build",
    "ajuda",
    "runtime",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".git",
}
HASH_BLOCK = 1024 * 1024


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_BLOCK), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    if MANIFEST.exists():
        cfg = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        inc = cfg.get("include", []) or []
        exc = cfg.get("exclude", []) or []
        return inc, exc
    return [], []


def match_any(rel: Path, patterns: list[str]) -> bool:
    s = rel.as_posix()
    return any(fnmatch.fnmatch(s, p) for p in patterns)


def included_by_manifest(rel: Path, inc_pats: list[str], exc_pats: list[str]) -> bool:
    return match_any(rel, inc_pats) and not match_any(rel, exc_pats)


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        d = Path(dirpath)
        # prune
        dirnames[:] = [n for n in dirnames if (d / n).name not in SKIP_DIRS]
        if d.name in SKIP_DIRS:
            continue
        for fn in filenames:
            p = d / fn
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if not p.is_file():
                continue
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--stale-days",
        type=int,
        default=60,
        help="Dias sem modificação para marcar como 'stale'",
    )
    ap.add_argument("--top", type=int, default=50, help="Top N maiores arquivos")
    args = ap.parse_args()

    print("🔍 Auditando repositório...")
    print(f"📁 ROOT: {ROOT}")
    print(f"📅 Stale: arquivos não modificados há > {args.stale_days} dias")
    print(f"📊 Top: {args.top} maiores arquivos")
    print()

    now = time.time()
    inc, exc = load_manifest()

    files = []
    by_size = {}
    top_dirs = {}

    print("📂 Coletando arquivos...")
    for p in walk_files():
        try:
            stat = p.stat()
            rel = p.relative_to(ROOT)
            first = rel.parts[0] if rel.parts else ""
            size = stat.st_size
            mtime = stat.st_mtime
            files.append({"rel": rel.as_posix(), "size": size, "mtime": int(mtime)})
            if first:
                td = top_dirs.setdefault(first, {"count": 0, "bytes": 0})
                td["count"] += 1
                td["bytes"] += size
            by_size.setdefault(size, []).append(p)
        except Exception as e:
            print(f"  ⚠️  Erro ao processar {p}: {e}")
            continue

    print(f"  ✅ {len(files)} arquivos coletados")
    print()

    # Duplicados (primeiro por tamanho, depois sha256)
    print("🔍 Buscando duplicados por hash SHA-256...")
    dups = []
    candidate_groups = sum(
        1 for same_size_files in by_size.values() if len(same_size_files) >= 2
    )
    print(f"  📊 {candidate_groups} grupos com mesmo tamanho")

    processed = 0
    for size, same_size_files in by_size.items():
        if len(same_size_files) < 2:
            continue
        buckets = {}
        for p in same_size_files:
            try:
                h = sha256_file(p)
                buckets.setdefault(h, []).append(p)
                processed += 1
                if processed % 100 == 0:
                    print(f"  📈 {processed} arquivos hasheados...")
            except Exception:
                pass
        for h, group in buckets.items():
            if len(group) > 1:
                dups.append(
                    {
                        "sha256": h,
                        "size": size,
                        "items": [str(g.relative_to(ROOT)) for g in group],
                    }
                )

    print(f"  ✅ {len(dups)} grupos duplicados encontrados")
    print()

    # Stale por data
    print(f"🕐 Identificando arquivos stale (> {args.stale_days} dias)...")
    stale_cut = now - (args.stale_days * 86400)
    stale = [f for f in files if f["mtime"] < stale_cut]
    print(f"  ✅ {len(stale)} arquivos stale")
    print()

    # Não copiados pelo manifest (logo, não entram no runtime)
    print("📋 Verificando arquivos fora do runtime manifest...")
    not_in_runtime = []
    for f in files:
        rel = Path(f["rel"])
        if not included_by_manifest(rel, inc, exc):
            not_in_runtime.append(f["rel"])
    print(f"  ✅ {len(not_in_runtime)} arquivos fora do runtime")
    print()

    # Top N maiores
    print(f"📊 Identificando top {args.top} maiores arquivos...")
    largest = sorted(files, key=lambda x: (-x["size"], x["rel"]))[: args.top]
    print(f"  ✅ Top {len(largest)} maiores")
    print()

    # Resultado
    plan = {
        "generated_at": int(now),
        "root": str(ROOT),
        "params": {"stale_days": args.stale_days, "top": args.top},
        "stats": {
            "files": len(files),
            "top_dirs": sorted(
                [{"name": k, **v} for k, v in top_dirs.items()],
                key=lambda x: (-x["bytes"], x["name"]),
            ),
        },
        "duplicates": sorted(dups, key=lambda x: (-x["size"], x["sha256"]))[:200],
        "stale": sorted(stale, key=lambda x: x["mtime"])[:500],
        "not_in_runtime_manifest": sorted(not_in_runtime),
        "largest": largest,
        "notes": [
            "Ninguém foi deletado. Isto é um plano de limpeza (dry-run).",
            "Duplicados: hash sha256 no conteúdo (mesmo tamanho + mesmo hash).",
            "not_in_runtime_manifest: não seriam copiados para runtime/ pelo manifesto atual.",
        ],
    }

    print("💾 Salvando relatórios...")
    AJUDA.mkdir(exist_ok=True)
    (AJUDA / "CLEANUP_PLAN.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown enxuto
    md = []
    md.append("# Plano de Limpeza (dry-run)\n")
    md.append(
        f"**Gerado em:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}\n"
    )
    md.append("## 📊 Estatísticas Gerais\n")
    md.append(f"- Arquivos totais: **{len(files):,}**")
    md.append(f"- Duplicados (por hash): **{len(plan['duplicates'])} grupos**")
    md.append(f"- Stale (> {args.stale_days}d): **{len(plan['stale']):,}**")
    md.append(
        f"- Fora do runtime (manifest): **{len(plan['not_in_runtime_manifest']):,}**"
    )

    md.append("\n## 📁 Top pastas por tamanho\n")
    for row in plan["stats"]["top_dirs"][:15]:
        size_mb = row["bytes"] / (1024 * 1024)
        md.append(
            f"- `{row['name']}` — {size_mb:.2f} MB ({row['bytes']:,} bytes), {row['count']:,} arquivos"
        )

    md.append("\n## 📦 Top arquivos grandes\n")
    for i, row in enumerate(plan["largest"][:20], 1):
        size_mb = row["size"] / (1024 * 1024)
        md.append(f"{i}. `{row['rel']}` — {size_mb:.2f} MB ({row['size']:,} bytes)")

    md.append("\n## 🔄 Duplicados (amostra dos maiores)\n")
    if plan["duplicates"]:
        for g in plan["duplicates"][:15]:
            size_mb = g["size"] / (1024 * 1024)
            md.append(
                f"\n### {size_mb:.2f} MB — {len(g['items'])} cópias — sha256={g['sha256'][:16]}…\n"
            )
            for it in g["items"][:8]:
                md.append(f"  - `{it}`")
            if len(g["items"]) > 8:
                md.append(f"  - *(+{len(g['items']) - 8} mais)*")
    else:
        md.append("*Nenhum duplicado encontrado.*")

    md.append("\n## 🕐 Arquivos Stale (amostra dos mais antigos)\n")
    if stale:
        for f in stale[:30]:
            age_days = (now - f["mtime"]) / 86400
            date_str = time.strftime("%Y-%m-%d", time.localtime(f["mtime"]))
            md.append(
                f"- `{f['rel']}` — modificado em {date_str} ({age_days:.0f} dias atrás)"
            )
    else:
        md.append("*Nenhum arquivo stale encontrado.*")

    md.append("\n## 📋 Fora do Runtime (amostra)\n")
    if not_in_runtime:
        md.append(
            f"\n*Total: {len(not_in_runtime):,} arquivos não serão copiados para runtime/*\n"
        )
        md.append("**Top 50:**\n")
        for item in not_in_runtime[:50]:
            md.append(f"- `{item}`")
        if len(not_in_runtime) > 50:
            md.append(f"\n*(+{len(not_in_runtime) - 50} mais no arquivo JSON)*")
    else:
        md.append("*Todos os arquivos estão incluídos no runtime.*")

    md.append("\n---\n")
    md.append("## ⚠️ IMPORTANTE\n")
    md.append("- **Nada foi deletado** - Este é apenas um relatório (dry-run)")
    md.append("- Revise cada grupo antes de tomar ações")
    md.append("- Use quarentena antes de deletar qualquer arquivo")
    md.append("- Arquivo completo: `ajuda/CLEANUP_PLAN.json`")

    (AJUDA / "CLEANUP_PLAN.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("  ✅ ajuda/CLEANUP_PLAN.json")
    print("  ✅ ajuda/CLEANUP_PLAN.md")
    print()
    print("✅ Auditoria concluída!")
    print()
    print("📊 Resumo:")
    print(f"  - {len(files):,} arquivos analisados")
    print(f"  - {len(dups)} grupos duplicados")
    print(f"  - {len(stale):,} arquivos stale")
    print(f"  - {len(not_in_runtime):,} fora do runtime")


if __name__ == "__main__":
    main()
