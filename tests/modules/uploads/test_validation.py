from __future__ import annotations

from pathlib import Path

import pytest

from src.core.storage_key import make_storage_key, storage_slug_filename, storage_slug_part
from src.modules.uploads import validation


def test_ensure_existing_folder_returns_resolved_path(tmp_path):
    existing = tmp_path / "folder"
    existing.mkdir()

    resolved = validation.ensure_existing_folder(existing)

    assert resolved == existing.resolve()


def test_ensure_existing_folder_raises_when_missing(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        validation.ensure_existing_folder(missing)


def test_iter_local_files_recurses_and_skips_dirs(tmp_path):
    base = tmp_path / "base"
    nested = base / "nested" / "inner"
    nested.mkdir(parents=True)
    file_a = base / "a.txt"
    file_a.write_text("a")
    file_b = nested / "b.pdf"
    file_b.write_bytes(b"data")
    (base / "nested" / "ignore").mkdir()

    found = list(validation.iter_local_files(base))

    assert set(found) == {file_a, file_b}


def test_guess_mime_known_and_unknown(tmp_path):
    known = tmp_path / "file.pdf"
    known.write_text("pdf")
    unknown = tmp_path / "file.unknownext"
    unknown.write_text("data")

    assert validation.guess_mime(known) == "application/pdf"
    assert validation.guess_mime(unknown) == "application/octet-stream"


def test_normalize_relative_path_strips_traversal():
    normalized = validation.normalize_relative_path(r"..\\folder//../safe/./file.pdf")

    assert normalized == "safe/file.pdf"


def test_prepare_folder_entries_builds_metadata(tmp_path):
    base = tmp_path / "uploads"
    target_dir = base / "Cliente Á" / "Pasta"
    target_dir.mkdir(parents=True)
    file_path = target_dir / "Relatório final.pdf"
    file_path.write_text("conteudo do pdf")

    entries = validation.prepare_folder_entries(
        base=base,
        client_id=123,
        subdir="SUB",
        org_id="ORG",
        hash_func=lambda path: f"hash-{Path(path).name}",
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == file_path
    assert entry.relative_path == "Cliente Á/Pasta/Relatório final.pdf"
    assert entry.storage_path == make_storage_key(
        "ORG", "123", "SUB", "Cliente Á", "Pasta", filename="Relatório final.pdf"
    )
    expected_safe_rel = "/".join(
        [storage_slug_part("Cliente Á"), storage_slug_part("Pasta"), storage_slug_filename("Relatório final.pdf")]
    )
    assert entry.safe_relative_path == expected_safe_rel
    assert entry.size_bytes == file_path.stat().st_size
    assert entry.sha256 == "hash-Relatório final.pdf"
    assert entry.mime_type == "application/pdf"


def test_prepare_folder_entries_uses_fallback_relative_when_empty(monkeypatch, tmp_path):
    base = tmp_path / "base"
    base.mkdir()

    class FakePath:
        name = "doc.pdf"

        def relative_to(self, _):
            return ""

        def stat(self):
            return type("stat", (), {"st_size": 7})

        def __str__(self):
            return self.name

    fake_path = FakePath()

    monkeypatch.setattr(validation, "iter_local_files", lambda _: [fake_path])

    seen: list[object] = []

    def fake_hash(value):
        seen.append(value)
        return "hash"

    entries = validation.prepare_folder_entries(
        base=base,
        client_id=1,
        subdir="sub",
        org_id="ORG",
        hash_func=fake_hash,
    )

    assert seen == [fake_path]
    assert len(entries) == 1
    entry = entries[0]
    assert entry.relative_path == "doc.pdf"
    assert entry.safe_relative_path == "doc.pdf"
    assert entry.storage_path == make_storage_key("ORG", "1", "sub", filename="doc.pdf")
    assert entry.sha256 == "hash"
    assert entry.mime_type == "application/pdf"
    assert entry.size_bytes == 7


def test_collect_pdf_items_from_folder_returns_empty_when_not_dir(tmp_path):
    not_dir = tmp_path / "single.pdf"
    not_dir.write_text("pdf")

    result = validation.collect_pdf_items_from_folder(not_dir, lambda path, relative: (path, relative))

    assert result == []


def test_collect_pdf_items_from_folder_filters_and_sorts(tmp_path):
    base = tmp_path / "docs"
    (base / "sub").mkdir(parents=True)
    files = [
        base / "B.PDF",
        base / "a.pdf",
        base / "sub" / "c.Pdf",
        base / "note.txt",
    ]
    for file in files:
        if file.suffix:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("x")

    result = validation.collect_pdf_items_from_folder(base, lambda path, relative: (relative, path.name))

    assert result == [
        ("a.pdf", "a.pdf"),
        ("B.PDF", "B.PDF"),
        ("sub/c.Pdf", "c.Pdf"),
    ]


def test_build_items_from_files_filters_non_pdf_and_orders(tmp_path):
    paths = [
        str(tmp_path / "Doc.PDF"),
        str(tmp_path / "ignore.txt"),
        str(tmp_path / "a.pdf"),
    ]

    result = validation.build_items_from_files(paths, lambda path, relative: (relative, path.name))

    assert result == [
        ("a.pdf", "a.pdf"),
        ("Doc.PDF", "Doc.PDF"),
    ]


def test_split_relative_path_uses_fallback_name():
    directories, filename = validation._split_relative_path("", "fallback.pdf")

    assert directories == []
    assert filename == "fallback.pdf"


def test_sanitize_directory_segments_drops_empty_parts():
    sanitized = validation._sanitize_directory_segments(["", "   ", "folder"])

    assert sanitized == ["folder"]


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            dict(
                cnpj_digits="0001112220001",
                relative_path="../docs/../file.pdf",
                subfolder="/SUB/",
                client_id=42,
                org_id="ORG",
            ),
            "ORG/42/GERAL/SUB/file.pdf",
        ),
        (
            dict(
                cnpj_digits="12345678000199",
                relative_path="dir/a.pdf",
                subfolder=None,
                client_id=None,
                org_id=None,
            ),
            "12345678000199/dir/a.pdf",
        ),
    ],
)
def test_build_remote_path_branches(kwargs, expected):
    result = validation.build_remote_path(**kwargs)

    assert result == expected
