"""
TESTE_1 - pdf_preview/raster_service

Objetivo: aumentar a cobertura de src/modules/pdf_preview/raster_service.py na fase 51,
cobrindo abertura de PDF, rasterização de páginas, cache e tratamento de erros.
"""

from __future__ import annotations

import types

import pytest

import src.modules.pdf_preview.raster_service as raster_service


@pytest.fixture
def fake_fitz(monkeypatch):
    calls = {"open": 0, "load_page": 0, "matrix": 0}

    class Pix:
        def __init__(self):
            self.width = 100
            self.height = 200

    class Page:
        def __init__(self, idx):
            self.idx = idx
            self.rect = types.SimpleNamespace(width=100, height=200)

        def get_pixmap(self, matrix=None, alpha=False):
            calls["load_page"] += 1
            return Pix()

    class Doc:
        page_count = 2

        def __init__(self):
            self.pages = [Page(0), Page(1)]

        def __iter__(self):
            return iter(self.pages)

        def load_page(self, idx):
            if idx >= len(self.pages):
                raise ValueError("out of range")
            return self.pages[idx]

        def close(self):
            calls["close"] = True

    def open_fn(*args, **kwargs):
        calls["open"] += 1
        return Doc()

    class Matrix:
        def __init__(self, x, y):
            calls["matrix"] += 1
            self.x = x
            self.y = y

    mod = types.SimpleNamespace(open=open_fn, Matrix=Matrix)
    monkeypatch.setattr(raster_service, "fitz", mod)
    return calls


def test_open_document_caminho_feliz(fake_fitz):
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc._doc is not None
    assert fake_fitz["open"] == 1


def test_page_count_com_doc(fake_fitz):
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc.page_count == 2


def test_page_count_sem_doc(monkeypatch):
    monkeypatch.setattr(raster_service, "fitz", None)
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc.page_count == 1


def test_get_page_sizes_caminho_feliz(fake_fitz):
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    sizes = svc.get_page_sizes()
    assert sizes == [(100, 200), (100, 200)]


def test_get_page_sizes_sem_doc(monkeypatch):
    monkeypatch.setattr(raster_service, "fitz", None)
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc.get_page_sizes() == [(800, 1100)]


def test_get_text_buffer_sem_doc(monkeypatch):
    monkeypatch.setattr(raster_service, "fitz", None)
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert "indisponível" in svc.get_text_buffer()[0].lower()


def test_get_page_pixmap_caminho_feliz(fake_fitz):
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    result = svc.get_page_pixmap(0, 1.5)
    assert result is not None
    assert result.width == 100 and result.height == 200
    # cache na segunda chamada
    again = svc.get_page_pixmap(0, 1.5)
    assert again is result


def test_get_page_pixmap_sem_fitz(monkeypatch):
    monkeypatch.setattr(raster_service, "fitz", None)
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc.get_page_pixmap(0, 1.0) is None


def test_get_page_pixmap_indice_invalido(fake_fitz):
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc.get_page_pixmap(5, 1.0) is None


def test_get_page_pixmap_erro_raster(fake_fitz):
    class BadPage:
        def get_pixmap(self, *a, **k):
            raise RuntimeError("fail")

    class BadDoc:
        page_count = 1

        def load_page(self, idx):
            return BadPage()

    def bad_open(*a, **k):
        return BadDoc()

    raster_service.fitz.open = bad_open  # type: ignore
    svc = raster_service.PdfRasterService(pdf_path="dummy.pdf")
    assert svc.get_page_pixmap(0, 1.0) is None
