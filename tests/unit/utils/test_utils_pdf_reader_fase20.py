from __future__ import annotations

import types


from src.utils import pdf_reader


class FakePage:
    def __init__(self, texts: dict[str, object]):
        self.texts = texts
        self.calls: list[str] = []

    def get_text(self, mode: str):
        self.calls.append(mode)
        value = self.texts.get(mode, "")
        if isinstance(value, Exception):
            raise value
        return value


class FakeDoc:
    def __init__(self, pages):
        self.pages = pages
        self.closed = False

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def load_page(self, idx: int):
        page = self.pages[idx]
        if isinstance(page, Exception):
            raise page
        return page

    def close(self):
        self.closed = True


def test_flatten_rawdict_basic():
    raw = {"blocks": [{"lines": [{"spans": [{"text": "foo"}, {"text": "bar"}]}]}]}
    assert pdf_reader._flatten_rawdict(raw) == "foo\nbar"


def test_flatten_rawdict_on_error_returns_str(caplog):
    raw = {"blocks": None}
    with caplog.at_level("WARNING"):
        result = pdf_reader._flatten_rawdict(raw)
    assert result == str(raw)
    assert any("Falha ao converter rawdict" in msg for msg in caplog.messages)


def test_read_pdf_text_returns_empty_when_open_fails(monkeypatch, caplog):
    def fake_open(path):
        raise ValueError("invalid pdf")

    caplog.clear()
    monkeypatch.setattr(pdf_reader, "fitz", types.SimpleNamespace(open=fake_open))

    with caplog.at_level("WARNING"):
        result = pdf_reader.read_pdf_text("fake.pdf")

    assert result == ""
    assert any("PDF inv" in msg for msg in caplog.messages)


def test_read_pdf_text_limits_pages_and_closes(monkeypatch):
    pages = [FakePage({"text": "page1"}), FakePage({"text": "page2"})]
    holder: dict[str, FakeDoc] = {}

    def fake_open(path):
        doc = FakeDoc(pages)
        holder["doc"] = doc
        return doc

    monkeypatch.setattr(pdf_reader, "fitz", types.SimpleNamespace(open=fake_open))

    result = pdf_reader.read_pdf_text("any.pdf", max_pages=1)
    assert result == "page1"
    assert holder["doc"].closed is True
    assert pages[0].calls == ["text"]
    assert pages[1].calls == []


def test_read_pdf_text_fallbacks_to_rawdict_and_casts_non_string(monkeypatch):
    pages = [
        FakePage(
            {
                "text": "",
                "rawdict": {"blocks": [{"lines": [{"spans": [{"text": "raw"}]}]}]},
            }
        ),
        FakePage({"text": 123}),
    ]

    def fake_open(path):
        return FakeDoc(pages)

    monkeypatch.setattr(pdf_reader, "fitz", types.SimpleNamespace(open=fake_open))

    result = pdf_reader.read_pdf_text("use-raw.pdf")
    assert result == "raw\n123"
    assert pages[0].calls == ["text", "rawdict"]
    assert pages[1].calls == ["text"]


def test_read_pdf_text_skips_page_on_exception(monkeypatch, caplog):
    pages = [FakePage({"text": "ok1"}), Exception("boom"), FakePage({"text": "ok2"})]

    def fake_open(path):
        return FakeDoc(pages)

    monkeypatch.setattr(pdf_reader, "fitz", types.SimpleNamespace(open=fake_open))

    with caplog.at_level("WARNING"):
        result = pdf_reader.read_pdf_text("err.pdf")

    assert result == "ok1\nok2"
    assert any("Falha ao ler" in msg for msg in caplog.messages)
