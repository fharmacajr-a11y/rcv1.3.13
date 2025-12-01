from __future__ import annotations

from pathlib import Path
from time import sleep

from PIL import Image

from src.modules.pdf_tools.pdf_batch_from_images import convert_subfolders_images_to_pdf


def _create_image(path: Path, color: str = "white") -> None:
    img = Image.new("RGB", (100, 100), color=color)
    try:
        img.save(path)
    finally:
        img.close()


def test_generates_one_pdf_per_subfolder(tmp_path) -> None:
    root = tmp_path
    sub1 = root / "cliente1"
    sub2 = root / "cliente2"
    sub1.mkdir()
    sub2.mkdir()

    _create_image(sub1 / "1.jpg")
    _create_image(sub1 / "2.jpg")
    _create_image(sub2 / "1.jpg")
    _create_image(sub2 / "2.png")

    generated = convert_subfolders_images_to_pdf(root)

    assert len(generated) == 2
    for subdir in (sub1, sub2):
        pdf_path = subdir / f"{subdir.name}.pdf"
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0


def test_skip_when_pdf_already_exists(tmp_path) -> None:
    root = tmp_path
    sub1 = root / "cliente1"
    sub2 = root / "cliente2"
    sub1.mkdir()
    sub2.mkdir()

    _create_image(sub1 / "1.jpg")
    _create_image(sub1 / "2.jpg")
    _create_image(sub2 / "1.jpg")

    existing_pdf = sub1 / f"{sub1.name}.pdf"
    existing_pdf.write_bytes(b"existing")
    mtime_before = existing_pdf.stat().st_mtime

    generated = convert_subfolders_images_to_pdf(root, overwrite=False)

    assert len(generated) == 1
    assert {p.parent for p in generated} == {sub2}

    # PDF existente nao deve ser alterado
    sleep(0.01)
    assert existing_pdf.stat().st_mtime == mtime_before

    pdf_sub2 = sub2 / f"{sub2.name}.pdf"
    assert pdf_sub2.exists()
    assert pdf_sub2.stat().st_size > 0


def test_delete_images_when_flag_true(tmp_path) -> None:
    root = tmp_path
    sub = root / "cliente1"
    sub.mkdir()

    img1 = sub / "3.jpg"
    img2 = sub / "3-1.jpg"
    _create_image(img1)
    _create_image(img2)

    generated = convert_subfolders_images_to_pdf(
        root_folder=root,
        delete_images=True,
    )

    pdf_path = sub / f"{sub.name}.pdf"
    assert generated == [pdf_path]
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    # Todas as imagens originais devem ter sido apagadas
    assert not img1.exists()
    assert not img2.exists()


def test_no_images_in_subfolder(tmp_path) -> None:
    root = tmp_path
    sub = root / "cliente_sem_imagens"
    sub.mkdir()
    (sub / "ignore.txt").write_text("sem imagem", encoding="utf-8")

    generated = convert_subfolders_images_to_pdf(root)

    assert generated == []
    assert not any(sub.glob("*.pdf"))


def test_overwrite_true_recreates_pdf(tmp_path) -> None:
    root = tmp_path
    sub = root / "cliente1"
    sub.mkdir()

    _create_image(sub / "1.jpg")
    _create_image(sub / "2.jpg")

    first_run = convert_subfolders_images_to_pdf(root)
    pdf_path = sub / f"{sub.name}.pdf"
    assert first_run == [pdf_path]
    mtime_before = pdf_path.stat().st_mtime

    _create_image(sub / "3.jpg", color="blue")
    sleep(1.1)  # garantir mtime diferente em Windows

    second_run = convert_subfolders_images_to_pdf(root, overwrite=True)
    assert second_run == [pdf_path]
    assert pdf_path.stat().st_mtime > mtime_before


def test_custom_image_extensions_only_png(tmp_path) -> None:
    root = tmp_path
    sub = root / "cliente1"
    sub.mkdir()

    jpg_img = sub / "1.jpg"
    png_img = sub / "2.png"
    _create_image(jpg_img)
    _create_image(png_img, color="red")

    generated = convert_subfolders_images_to_pdf(
        root,
        image_extensions=(".png",),
        delete_images=True,
    )

    pdf_path = sub / f"{sub.name}.pdf"
    assert generated == [pdf_path]
    assert pdf_path.exists()
    assert not png_img.exists()
    assert jpg_img.exists()


def test_prefers_newer_revision_and_mtime(monkeypatch, tmp_path) -> None:
    from src.modules.pdf_tools import pdf_batch_from_images as module

    root = tmp_path
    sub = root / "cliente1"
    sub.mkdir()

    img_base = sub / "3.jpg"
    img_rev1 = sub / "3-1.jpg"
    img_rev2 = sub / "3-2.jpg"
    img_rev1_alt = sub / "3-1.png"
    doc_rev1 = sub / "doc-1.jpg"
    doc_rev1_newer = sub / "doc-1.png"

    _create_image(img_base, color="green")
    _create_image(img_rev1, color="yellow")
    _create_image(img_rev2, color="purple")
    _create_image(img_rev1_alt, color="orange")
    _create_image(doc_rev1, color="black")
    _create_image(doc_rev1_newer, color="white")
    sleep(1.1)
    img_rev1_alt.touch()
    doc_rev1_newer.touch()

    opened_paths: list[Path] = []
    original_open = module.Image.open

    def _spy_open(path, *args, **kwargs):
        opened_paths.append(Path(path))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(module.Image, "open", _spy_open)

    generated = convert_subfolders_images_to_pdf(root)

    pdf_path = sub / f"{sub.name}.pdf"
    assert generated == [pdf_path]
    # Apenas os melhores por base devem ser abertos:
    # base "3" -> 3-2.jpg (rev mais alta)
    # base "doc" -> doc-1.png (mesma rev, mtime mais novo)
    assert {p.name for p in opened_paths} == {"3-2.jpg", "doc-1.png"}


def test_custom_pdf_name_and_unlink_error(monkeypatch, tmp_path) -> None:
    root = tmp_path
    sub = root / "cliente1"
    sub.mkdir()

    img1 = sub / "1.jpg"
    img2 = sub / "2.jpg"
    _create_image(img1)
    _create_image(img2)

    original_unlink = Path.unlink

    def _fake_unlink(self, *args, **kwargs):
        if self.name == "1.jpg":
            raise OSError("cannot delete")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _fake_unlink)

    generated = convert_subfolders_images_to_pdf(
        root_folder=root,
        pdf_name="custom.pdf",
        delete_images=True,
    )

    pdf_path = sub / "custom.pdf"
    assert generated == [pdf_path]
    assert pdf_path.exists()
    assert img1.exists()  # nao apagou por erro de unlink
    assert not img2.exists()


def test_progress_callback_receives_monotonic_bytes(tmp_path) -> None:
    root = tmp_path
    sub = root / "cliente1"
    sub.mkdir()

    img1 = sub / "1.jpg"
    img2 = sub / "2.jpg"
    _create_image(img1)
    _create_image(img2)

    events: list[tuple[int, int]] = []

    def progress_cb(processed_bytes, total_bytes, *_args):
        events.append((processed_bytes, total_bytes))

    generated = convert_subfolders_images_to_pdf(
        root_folder=root,
        progress_cb=progress_cb,
    )

    assert generated
    assert events
    prev = 0
    last_total = None
    for processed, total in events:
        assert processed >= prev
        assert processed <= total
        prev = processed
        last_total = total
    assert last_total is not None
