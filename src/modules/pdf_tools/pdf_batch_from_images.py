from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from PIL import Image

ProgressCallback = Callable[[int, int, int, int, Path | None, Path | None], None]


def convert_subfolders_images_to_pdf(
    root_folder: Path,
    image_extensions: Iterable[str] | None = None,
    pdf_name: str | None = None,
    overwrite: bool = False,
    delete_images: bool = False,
    progress_cb: ProgressCallback | None = None,
) -> list[Path]:
    """Converte imagens de cada subpasta em um único PDF.

    Para cada subpasta direta de `root_folder`, agrupa imagens e gera um PDF.
    Aplica dedup por base+revisão (ex.: doc, doc-1, doc-2 -> apenas doc-2).

    Args:
        root_folder: Pasta raiz contendo subpastas com imagens
        image_extensions: Extensões de imagem aceitas (padrão: .jpg, .jpeg, .png, .jfif)
        pdf_name: Nome customizado para o PDF (padrão: <nome_subpasta>.pdf)
        overwrite: Se True, sobrescreve PDFs existentes
        delete_images: Se True, remove imagens após criar o PDF
        progress_cb: Callback(processed_bytes, total_bytes, idx, total_subdirs, subdir, img_path)

    Returns:
        Lista de caminhos dos PDFs gerados
    """
    extensions = (
        tuple(ext.lower() for ext in image_extensions)
        if image_extensions is not None
        else (".jpg", ".jpeg", ".png", ".jfif")
    )
    generated_pdfs: list[Path] = []

    subdirs = [p for p in root_folder.iterdir() if p.is_dir()]
    total_bytes = 0
    subdir_images: dict[Path, list[Path]] = {}
    for subdir in subdirs:
        all_image_paths = [path for path in subdir.iterdir() if path.is_file() and path.suffix.lower() in extensions]
        if not all_image_paths:
            continue
        subdir_images[subdir] = all_image_paths
        total_bytes += sum(path.stat().st_size for path in all_image_paths)

    if not subdir_images:
        return []

    processed_bytes = 0
    for idx, (subdir, all_image_paths) in enumerate(subdir_images.items(), start=1):
        best_for_base: dict[str, tuple[int, float, Path]] = {}
        for path in all_image_paths:
            stem = path.stem
            base = stem
            rev = 0

            parts = stem.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                base = parts[0]
                rev = int(parts[1])

            mtime = path.stat().st_mtime
            current = best_for_base.get(base)
            if current is None or rev > current[0] or (rev == current[0] and mtime > current[1]):
                best_for_base[base] = (rev, mtime, path)

        image_paths = sorted(
            (info[2] for info in best_for_base.values()),
            key=lambda p: p.name,
        )

        if pdf_name is None:
            pdf_filename = f"{subdir.name}.pdf"
        else:
            pdf_filename = pdf_name

        pdf_path = subdir / pdf_filename
        if not overwrite and pdf_path.exists():
            continue

        temp_images: list[Image.Image] = []
        max_width = 0
        max_height = 0
        for path in image_paths:
            img = Image.open(path)
            temp_images.append(img)
            if img.width > max_width:
                max_width = img.width
            if img.height > max_height:
                max_height = img.height
            size = path.stat().st_size
            processed_bytes += size
            if progress_cb is not None:
                progress_cb(
                    processed_bytes,
                    total_bytes,
                    idx,
                    len(subdir_images),
                    subdir,
                    path,
                )

        images_rgb: list[Image.Image] = []
        try:
            for img in temp_images:
                rgb = img.convert("RGB")
                canvas = Image.new("RGB", (max_width, max_height), "white")
                x = (max_width - rgb.width) // 2
                y = (max_height - rgb.height) // 2
                canvas.paste(rgb, (x, y))
                images_rgb.append(canvas)

            first, *rest = images_rgb
            first.save(pdf_path, save_all=True, append_images=rest)
            generated_pdfs.append(pdf_path)

            if delete_images:
                for path in all_image_paths:
                    try:
                        path.unlink()
                    except OSError:
                        pass
        finally:
            for img in temp_images:
                img.close()
            for img in images_rgb:
                img.close()

    return generated_pdfs
