"""
Testes para utilitário de PDF - pypdf backend
"""

import fitz  # PyMuPDF
from pypdf import PdfReader


def _make_pdf_with_text(path, text="Hello RC"):
    """Cria PDF com texto usando PyMuPDF"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)  # 1 inch da borda
    doc.save(path)
    doc.close()


def test_extract_text_with_pypdf(tmp_path):
    """Gera PDF e extrai texto com pypdf"""
    pdf = tmp_path / "hello.pdf"
    _make_pdf_with_text(str(pdf), "Hello RC")

    r = PdfReader(str(pdf))
    content = (r.pages[0].extract_text() or "").strip()

    assert "Hello RC" in content


def test_extract_text_multiline(tmp_path):
    """PDF com múltiplas linhas"""
    pdf = tmp_path / "multiline.pdf"

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Linha 1")
    page.insert_text((72, 92), "Linha 2")
    page.insert_text((72, 112), "Linha 3")
    doc.save(str(pdf))
    doc.close()

    r = PdfReader(str(pdf))
    content = r.pages[0].extract_text() or ""

    assert "Linha 1" in content
    assert "Linha 2" in content
    assert "Linha 3" in content


def test_extract_text_empty_pdf(tmp_path):
    """PDF vazio (sem texto)"""
    pdf = tmp_path / "empty.pdf"

    doc = fitz.open()
    doc.new_page()  # Página sem conteúdo
    doc.save(str(pdf))
    doc.close()

    r = PdfReader(str(pdf))
    content = (r.pages[0].extract_text() or "").strip()

    # PDF vazio deve retornar string vazia ou None
    assert content == ""


def test_pdf_reader_integration_with_file_utils(tmp_path):
    """Integração com utils.file_utils.read_pdf_text"""
    from utils.file_utils import read_pdf_text

    pdf = tmp_path / "integration.pdf"
    _make_pdf_with_text(str(pdf), "Integration Test RC")

    # Testa a função pública do módulo
    result = read_pdf_text(str(pdf))

    assert result is not None
    assert "Integration Test RC" in result
