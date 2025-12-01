from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Exemplo de uso:
# python devtools/pdf_batch_from_images.py "D:\\caminho\\para\\win 1"


def _main() -> None:
    REPO_ROOT = Path(__file__).resolve().parent.parent
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from src.modules.pdf_tools.pdf_batch_from_images import (
        convert_subfolders_images_to_pdf,
    )

    parser = argparse.ArgumentParser(description="Converte imagens .jpg/.jpeg de cada subpasta em PDFs separados.")
    parser.add_argument(
        "root",
        type=Path,
        help="Pasta mãe contendo as subpastas com imagens.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve PDFs existentes nas subpastas.",
    )
    args = parser.parse_args()

    root_path = args.root
    if not root_path.is_dir():
        parser.error(f"O caminho informado não é uma pasta válida: {root_path}")

    subfolders = [p for p in root_path.iterdir() if p.is_dir()]
    generated = convert_subfolders_images_to_pdf(
        root_folder=root_path,
        image_extensions=None,
        pdf_name=None,
        overwrite=args.overwrite,
        delete_images=False,
    )

    print(f"Subpastas encontradas: {len(subfolders)}")
    print(f"PDFs gerados: {len(generated)}")
    for pdf_path in generated:
        try:
            relative = pdf_path.relative_to(root_path)
        except ValueError:
            relative = pdf_path
        print(f"- {relative}")


if __name__ == "__main__":
    _main()
