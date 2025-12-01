from __future__ import annotations

import builtins
import sys
import types
from datetime import datetime
from pathlib import Path


from src.utils.file_utils import bytes_utils


def test_read_pdf_text_pypdf_with_text(monkeypatch, tmp_path):
    class FakePage:
        def __init__(self, text: str, raise_exc: bool = False):
            self.text = text
            self.raise_exc = raise_exc

        def extract_text(self) -> str:
            if self.raise_exc:
                raise ValueError("extract error")
            return self.text

    class FakeReader:
        def __init__(self, path: str):
            self.pages = [
                FakePage("First page"),
                FakePage("", raise_exc=True),
                FakePage("Second page"),
            ]

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"pdf")

    monkeypatch.setattr(bytes_utils, "pdfmod", True)
    monkeypatch.setattr(bytes_utils, "PdfReader", FakeReader)

    result = bytes_utils._read_pdf_text_pypdf(pdf_path)
    assert result == "First page\nSecond page"


def test_read_pdf_text_pypdf_without_library(monkeypatch, tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"pdf")

    monkeypatch.setattr(bytes_utils, "pdfmod", False)
    assert bytes_utils._read_pdf_text_pypdf(pdf_path) is None


def test_read_pdf_text_pymupdf_import_failure(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("fitz not available")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert bytes_utils._read_pdf_text_pymupdf(tmp_path / "doc.pdf") is None


def test_read_pdf_text_pymupdf_extracts_pages(monkeypatch, tmp_path):
    class FakePage:
        def __init__(self, text: str):
            self.text = text

        def get_text(self) -> str:
            return self.text

    class FakeDoc:
        def __init__(self, pages):
            self._pages = pages

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter(self._pages)

    def fake_open(path: str):
        pages = [FakePage("hello"), FakePage("   "), FakePage("world")]
        return FakeDoc(pages)

    fake_fitz = types.SimpleNamespace(open=fake_open)
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"pdf")

    result = bytes_utils._read_pdf_text_pymupdf(pdf_path)
    assert result == "hello\nworld"


def test_ocr_pdf_with_pymupdf_import_failure(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"fitz", "pytesseract", "PIL"}:
            raise ImportError("missing dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert bytes_utils._ocr_pdf_with_pymupdf(tmp_path / "doc.pdf") is None


def test_ocr_pdf_with_pymupdf_uses_pixmap_and_limit(monkeypatch, tmp_path):
    class FakePixmap:
        width = 2
        height = 3
        samples = b"rgb"

    class FakePage:
        def __init__(self, text: str, pixmap: FakePixmap):
            self.text = text
            self.pixmap = pixmap
            self.used_dpi = None

        def get_text(self) -> str:
            return self.text

        def get_pixmap(self, dpi: int):
            self.used_dpi = dpi
            return self.pixmap

    class FakeDoc:
        def __init__(self, pages):
            self._pages = pages

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter(self._pages)

    pixmap = FakePixmap()
    pages = [
        FakePage("page text", pixmap),
        FakePage("", pixmap),
        FakePage("ignored", pixmap),
    ]

    def fake_open(path: str):
        return FakeDoc(pages)

    def fake_image_to_string(img, lang=None):
        return "ocr text"

    class FakeImageModule(types.SimpleNamespace):
        @staticmethod
        def frombytes(mode, size, data):
            return {"mode": mode, "size": size, "data": data}

    fake_fitz = types.SimpleNamespace(open=fake_open)
    fake_pytesseract = types.SimpleNamespace(image_to_string=fake_image_to_string)
    image_module = types.ModuleType("PIL.Image")
    image_module.frombytes = FakeImageModule.frombytes
    pil_package = types.ModuleType("PIL")
    pil_package.Image = image_module

    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    monkeypatch.setitem(sys.modules, "pytesseract", fake_pytesseract)
    monkeypatch.setitem(sys.modules, "PIL.Image", image_module)
    monkeypatch.setitem(sys.modules, "PIL", pil_package)

    pdf_path = tmp_path / "ocr.pdf"
    pdf_path.write_bytes(b"pdf")

    result = bytes_utils._ocr_pdf_with_pymupdf(pdf_path, max_pages=2, dpi=123)
    assert result == "page text\nocr text"
    assert pages[1].used_dpi == 123


def test_read_pdf_text_handles_missing_and_fallback(monkeypatch, tmp_path):
    missing = tmp_path / "missing.pdf"
    assert bytes_utils.read_pdf_text(missing) is None

    calls: list[str] = []

    def fake_pymupdf(path: Path):
        calls.append("pymupdf")
        return None

    def fake_pypdf(path: Path):
        calls.append("pypdf")
        return ""

    def fake_ocr(path: Path):
        calls.append("ocr")
        return "ocr result"

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"pdf")

    monkeypatch.setattr(bytes_utils, "_read_pdf_text_pymupdf", fake_pymupdf)
    monkeypatch.setattr(bytes_utils, "_read_pdf_text_pypdf", fake_pypdf)
    monkeypatch.setattr(bytes_utils, "_ocr_pdf_with_pymupdf", fake_ocr)

    assert bytes_utils.read_pdf_text(pdf_path) == "ocr result"
    assert calls == ["pymupdf", "pypdf", "ocr"]


def test_read_pdf_text_stops_on_first_success(monkeypatch, tmp_path):
    calls: list[str] = []

    def fake_pymupdf(path: Path):
        calls.append("pymupdf")
        return "first"

    def fake_pypdf(path: Path):
        calls.append("pypdf")
        return "second"

    def fake_ocr(path: Path):
        calls.append("ocr")
        return "third"

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"pdf")

    monkeypatch.setattr(bytes_utils, "_read_pdf_text_pymupdf", fake_pymupdf)
    monkeypatch.setattr(bytes_utils, "_read_pdf_text_pypdf", fake_pypdf)
    monkeypatch.setattr(bytes_utils, "_ocr_pdf_with_pymupdf", fake_ocr)

    assert bytes_utils.read_pdf_text(pdf_path) == "first"
    assert calls == ["pymupdf"]


def test_looks_like_cartao_cnpj():
    text = "Cartao CNPJ 12.345.678/0001-90 com situacao cadastral"
    assert bytes_utils._looks_like_cartao_cnpj(text)
    assert not bytes_utils._looks_like_cartao_cnpj("sem cnpj valido aqui")


def test_find_cartao_cnpj_pdf_returns_match(monkeypatch, tmp_path):
    pdf_ok = tmp_path / "ok.pdf"
    pdf_ok.write_bytes(b"ok")
    pdf_other = tmp_path / "other.pdf"
    pdf_other.write_bytes(b"other")

    mapping = {
        str(pdf_other): "documento comum",
        str(pdf_ok): "cartao cnpj 12.345.678/0001-90",
    }

    def fake_read(path: Path):
        return mapping.get(str(path))

    monkeypatch.setattr(bytes_utils, "read_pdf_text", fake_read)
    result = bytes_utils.find_cartao_cnpj_pdf(tmp_path, max_mb=0)
    assert result == pdf_ok


def test_find_cartao_cnpj_pdf_handles_missing_and_no_match(monkeypatch, tmp_path):
    monkeypatch.setattr(bytes_utils, "read_pdf_text", lambda p: None)
    assert bytes_utils.find_cartao_cnpj_pdf(tmp_path / "absent") is None

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"doc")
    assert bytes_utils.find_cartao_cnpj_pdf(tmp_path) is None


def test_list_and_classify_pdfs(monkeypatch, tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"a")
    nested = tmp_path / "nested"
    nested.mkdir()
    pdf2 = nested / "b.pdf"
    pdf2.write_bytes(b"b")

    seen: list[str] = []

    def fake_classify(path: str):
        seen.append(Path(path).name)
        return {"label": f"doc-{Path(path).name}"}

    monkeypatch.setattr(bytes_utils, "classify_document", fake_classify)
    docs = bytes_utils.list_and_classify_pdfs(tmp_path)

    assert {"path": str(pdf1), "label": "doc-a.pdf"} in docs
    assert {"path": str(pdf2), "label": "doc-b.pdf"} in docs
    assert set(seen) == {"a.pdf", "b.pdf"}


def test_write_and_read_marker_id(monkeypatch, tmp_path):
    monkeypatch.setattr(bytes_utils, "CLOUD_ONLY", False)
    folder = tmp_path / "client"
    marker = bytes_utils.write_marker(str(folder), 123)
    assert Path(marker).read_text(encoding="utf-8") == "123\n"
    assert bytes_utils.read_marker_id(str(folder)) == "123"


def test_read_marker_id_handles_legacy_and_missing(tmp_path):
    missing = tmp_path / "missing"
    assert bytes_utils.read_marker_id(str(missing)) is None

    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "cliente_old.marker"
    legacy_file.write_text("ID=789", encoding="utf-8")
    assert bytes_utils.read_marker_id(str(legacy_dir)) == "789"

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    (empty_dir / bytes_utils.MARKER_NAME).write_text("   ", encoding="utf-8")
    assert bytes_utils.read_marker_id(str(empty_dir)) is None


def test_migrate_legacy_marker_creates_new_and_removes_old(tmp_path):
    folder = tmp_path / "client"
    folder.mkdir()
    legacy = folder / "cliente_abc.marker"
    legacy.write_text("ID=456", encoding="utf-8")

    new_path = bytes_utils.migrate_legacy_marker(str(folder))
    assert new_path == str(folder / bytes_utils.MARKER_NAME)
    assert Path(new_path).read_text(encoding="utf-8") == "456\n"
    assert not legacy.exists()


def test_migrate_legacy_marker_without_ids(tmp_path):
    folder = tmp_path / "empty"
    folder.mkdir()
    assert bytes_utils.migrate_legacy_marker(str(folder)) is None


def test_get_marker_updated_at(tmp_path):
    folder = tmp_path / "client"
    folder.mkdir()
    marker = folder / bytes_utils.MARKER_NAME
    marker.write_text("1", encoding="utf-8")

    ts = bytes_utils.get_marker_updated_at(str(folder))
    assert isinstance(ts, datetime)


def test_format_datetime_variants():
    dt = datetime(2025, 1, 2, 3, 4, 5)
    assert bytes_utils.format_datetime(dt) == "02/01/2025 - 03:04:05"
    assert bytes_utils.format_datetime("2025-01-02T03:04:05") == "02/01/2025 - 03:04:05"
    assert bytes_utils.format_datetime("not-a-date") == "not-a-date"
    assert bytes_utils.format_datetime(None) == ""
