
# tools/test_resolver.py
from __future__ import annotations
import argparse
from core.services.path_resolver import resolve_cliente_path, resolve_unique_path, TRASH_DIR
from config.paths import DOCS_DIR

def main():
    ap = argparse.ArgumentParser(description="Testa resolução de pastas de cliente por PK.")
    ap.add_argument("pk", type=int, help="ID do cliente (PK)")
    args = ap.parse_args()

    r = resolve_cliente_path(args.pk)
    print("DOCS_DIR:", DOCS_DIR)
    print("TRASH_DIR:", TRASH_DIR)
    print("PK:", r.pk)
    print("Slug esperado:", r.slug)
    print("Ativo:", r.active or "<não encontrado>")
    print("Lixeira:", r.trash or "<não encontrado>")

    path, loc = resolve_unique_path(args.pk)
    print("\nDecisão final:", (path or "<não encontrado>"), "[", (loc or "--"), "]")

if __name__ == "__main__":
    main()
