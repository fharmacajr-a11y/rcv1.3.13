"""
Verifica links quebrados em documentação ativa (ignora _archive).

Valida apenas links relativos em docs/ excluindo:
- docs/_archive/**
- docs/customtk/_archive/** (se existir)
- Links externos (http/https/mailto)
- Anchors (#)
"""

import re
import sys
from pathlib import Path


def is_active_doc(path: Path, root: Path) -> bool:
    """Retorna True se o arquivo está nas docs ativas (não em _archive, _plans ou microfases).

    Docs ativas:
    - docs/README.md, STATUS.md, ROADMAP.md
    - docs/ci/*.md
    - docs/releases/*.md
    - docs/customtk/README.md, MIGRATION_SUMMARY.md, TECHNICAL_DOCS.md

    Docs históricas (ignoradas):
    - docs/_archive/**
    - docs/_plans/**
    - docs/customtk/customtk_clientes/** (53 microfases históricas)
    """
    relative = path.relative_to(root)
    parts = relative.parts

    # Ignora qualquer caminho contendo _archive ou _plans
    if "_archive" in parts or "_plans" in parts:
        return False

    # Ignora microfases históricas (docs/customtk/customtk_clientes/**)
    if "customtk_clientes" in parts:
        return False

    return True


def check_docs_links() -> int:
    """Verifica links quebrados nas docs ativas."""
    root = Path("docs").resolve()
    bad_links = []
    link_re = re.compile(r"\]\(([^)]+)\)")

    # Encontrar todos os .md nas docs ativas
    active_docs = [md for md in root.rglob("*.md") if is_active_doc(md, root)]

    print(f"Verificando {len(active_docs)} documentos ativos...")

    for md in active_docs:
        txt = md.read_text(encoding="utf-8", errors="ignore")

        for target in link_re.findall(txt):
            target = target.strip()

            # Ignorar links externos e anchors
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # Remover anchor e query string
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue

            # Resolver caminho do link
            target_path = (md.parent / target).resolve()

            # Só validar links que apontam para dentro de docs/
            # (ignora links para src/, tests/, etc)
            try:
                target_path.relative_to(root)
            except ValueError:
                # Link aponta para fora de docs/, ignorar
                continue

            # Verificar se existe
            if not target_path.exists():
                rel_md = md.relative_to(root)
                bad_links.append((str(rel_md).replace("\\", "/"), target))

    if bad_links:
        print("\n❌ BROKEN LINKS ENCONTRADOS NAS DOCS ATIVAS:\n")
        for file, link in bad_links:
            print(f"  {file} -> {link}")
        print(f"\nTotal: {len(bad_links)} links quebrados")
        return 1

    print("\n✅ OK: Nenhum link quebrado nas docs ativas")
    return 0


if __name__ == "__main__":
    sys.exit(check_docs_links())
