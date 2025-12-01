"""
TESTE_1 - pdf_preview/download_service

Objetivo: aumentar a cobertura de src/modules/pdf_preview/download_service.py na fase 50,
cobrindo geração de caminho único, salvamento de PDF/imagem, erros de IO e casos de borda.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.modules.pdf_preview.download_service as download_service


def make_ctx(base_name: str, tmp_path: Path, ext: str):
    return download_service.DownloadContext(base_name=base_name, default_dir=tmp_path, extension=ext)


def test_build_unique_path_sem_existente(tmp_path):
    ctx = make_ctx("arquivo", tmp_path, ".pdf")
    path = download_service.build_unique_path(ctx)
    assert path == tmp_path / "arquivo.pdf"


def test_build_unique_path_incrementa_sufixo(tmp_path):
    base = "arquivo"
    first = tmp_path / f"{base}.pdf"
    first.write_text("existe")
    second = tmp_path / f"{base} (1).pdf"
    second.write_text("tambem")
    ctx = make_ctx(base, tmp_path, ".pdf")

    path = download_service.build_unique_path(ctx)

    assert path.name == "arquivo (2).pdf"


def test_save_pdf_com_bytes_cria_arquivo(tmp_path):
    ctx = make_ctx("doc", tmp_path, ".pdf")
    result = download_service.save_pdf(b"conteudo", None, ctx)
    assert result.exists()
    assert result.read_bytes() == b"conteudo"


def test_save_pdf_copia_de_origem(tmp_path):
    origem = tmp_path / "origem.pdf"
    origem.write_bytes(b"origem")
    ctx = make_ctx("copia", tmp_path, ".pdf")

    result = download_service.save_pdf(None, str(origem), ctx)

    assert result.exists()
    assert result.read_bytes() == b"origem"
    assert result.name == "copia.pdf"


def test_save_pdf_sem_bytes_e_sem_origem_lanca(tmp_path):
    ctx = make_ctx("falha", tmp_path, ".pdf")
    with pytest.raises(FileNotFoundError):
        download_service.save_pdf(None, None, ctx)


def test_save_image_caminho_feliz_png(tmp_path):
    image = MagicMock()
    image.mode = "RGB"
    saved = {}

    def fake_save(target, format=None):
        saved["path"] = Path(target)
        saved["format"] = format

    image.save = fake_save
    ctx = make_ctx("img", tmp_path, ".png")

    result = download_service.save_image(image, ctx)

    assert saved["path"] == result
    assert result.name == "img.png"
    assert saved["format"] is None  # usa padrão do PIL quando já é png


def test_save_image_fallback_para_png(tmp_path):
    image = MagicMock()
    image.mode = "P"
    saved = []
    convert_calls = {"n": 0}

    class BadConverted:
        mode = "RGBA"

        def save(self, target, format=None):
            raise RuntimeError("fail save")

    class GoodConverted:
        mode = "RGBA"

        def save(self, target, format=None):
            saved.append((Path(target), format))

    def fake_convert(mode):
        convert_calls["n"] += 1
        return BadConverted() if convert_calls["n"] == 1 else GoodConverted()

    image.convert = fake_convert
    image.save = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail save"))  # força fallback

    ctx = make_ctx("foto", tmp_path, ".jpg")

    result = download_service.save_image(image, ctx)

    assert saved, "fallback deve ter chamado save"
    path, fmt = saved[0]
    assert path.suffix == ".png"
    assert fmt == "PNG"
    assert result == path


def test_save_image_com_none_lanca(tmp_path):
    ctx = make_ctx("nulo", tmp_path, ".png")
    with pytest.raises(ValueError):
        download_service.save_image(None, ctx)
