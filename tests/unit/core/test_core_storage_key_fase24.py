from __future__ import annotations

import hashlib


from src.core.storage_key import make_storage_key, storage_slug_filename, storage_slug_part


def test_storage_slug_part_sanitizes_diacritics_percent_and_spaces() -> None:
    assert storage_slug_part("  élé% / espaço  ") == "ele / espaco"
    assert storage_slug_part(None) == ""


def test_storage_slug_filename_defaults_when_empty_or_sanitized_to_empty() -> None:
    assert storage_slug_filename("") == "arquivo"
    assert storage_slug_filename("%%%   ") == "arquivo"


def test_make_storage_key_basic_and_normalizes_slashes() -> None:
    key = make_storage_key("org", "clientes", 123, filename="nota.pdf")
    assert key == "org/clientes/123/nota.pdf"

    key2 = make_storage_key(" org ", "sub//child", filename="  spaced name.txt")
    assert key2 == "org/sub/child/spaced name.txt"


def test_make_storage_key_fallback_when_disallowed_characters_present() -> None:
    # "#" is not accepted by the allowed regex, triggering the fallback hash.
    fname = "relatorio#ç.pdf"
    expected_fname = "relatorio#c.pdf"
    digest = hashlib.sha256(expected_fname.encode("utf-8")).hexdigest()[:8]
    expected = f"org/{expected_fname.rpartition('.')[0]}-{digest}.pdf"

    key = make_storage_key("org", filename=fname)
    assert key == expected


def test_make_storage_key_skips_empty_parts_and_none_filename() -> None:
    key = make_storage_key(None, "", filename=None)
    assert key == "arquivo"
