# -*- coding: utf-8 -*-
"""Teste de regressão para bug de contrato Cartão CNPJ (BATCH 10B).

Garante que extrair_dados_cartao_cnpj_em_pasta aceita tanto:
- classificadores legados: d["type"] == "cnpj_card"
- classificadores novos: d["kind"] == "cartao_cnpj"

E que extrai do PDF candidato ANTES de fazer fallback pesado (find_cartao_cnpj_pdf).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_extrair_cartao_cnpj_aceita_kind_cartao_cnpj_sem_fallback() -> None:
    """Garante que classificador com 'kind':'cartao_cnpj' não chama fallback pesado."""
    from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta

    base_dir = "/fake/pasta"
    mock_pdf_path = str(Path(base_dir) / "cartao.pdf")

    # Simula classificador retornando "kind":"cartao_cnpj" + path
    mock_classified = [{"kind": "cartao_cnpj", "path": mock_pdf_path}]

    with (
        patch("src.utils.file_utils.list_and_classify_pdfs") as mock_classify,
        patch("src.utils.pdf_reader.read_pdf_text") as mock_read,
        patch("src.utils.file_utils.find_cartao_cnpj_pdf") as mock_find,
        patch("src.utils.text_utils.extract_company_fields") as mock_extract,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        mock_classify.return_value = mock_classified
        mock_read.return_value = "CNPJ: 12.345.678/0001-90\nRAZÃO SOCIAL: TESTE LTDA"
        mock_extract.return_value = {"cnpj": "12.345.678/0001-90", "razao_social": "TESTE LTDA"}
        mock_find.side_effect = AssertionError("find_cartao_cnpj_pdf NÃO deve ser chamado!")

        result = extrair_dados_cartao_cnpj_em_pasta(base_dir)

        assert result["cnpj"] == "12.345.678/0001-90"
        assert result["razao_social"] == "TESTE LTDA"
        mock_classify.assert_called_once_with(base_dir)
        mock_read.assert_called_once_with(mock_pdf_path)
        mock_find.assert_not_called()  # NÃO deve chamar fallback pesado


@pytest.mark.unit
def test_extrair_cartao_cnpj_aceita_type_cnpj_card_legado() -> None:
    """Garante compatibilidade com classificador legado 'type':'cnpj_card'."""
    from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta

    base_dir = "/fake/pasta"
    mock_pdf_path = str(Path(base_dir) / "cartao.pdf")

    # Simula classificador legado retornando "type":"cnpj_card"
    mock_classified = [{"type": "cnpj_card", "path": mock_pdf_path}]

    with (
        patch("src.utils.file_utils.list_and_classify_pdfs") as mock_classify,
        patch("src.utils.pdf_reader.read_pdf_text") as mock_read,
        patch("src.utils.file_utils.find_cartao_cnpj_pdf") as mock_find,
        patch("src.utils.text_utils.extract_company_fields") as mock_extract,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        mock_classify.return_value = mock_classified
        mock_read.return_value = "CNPJ: 99.888.777/0001-66\nRAZÃO SOCIAL: ANTIGA LTDA"
        mock_extract.return_value = {"cnpj": "99.888.777/0001-66", "razao_social": "ANTIGA LTDA"}
        mock_find.side_effect = AssertionError("find_cartao_cnpj_pdf NÃO deve ser chamado!")

        result = extrair_dados_cartao_cnpj_em_pasta(base_dir)

        assert result["cnpj"] == "99.888.777/0001-66"
        assert result["razao_social"] == "ANTIGA LTDA"
        mock_find.assert_not_called()


@pytest.mark.unit
def test_extrair_cartao_cnpj_com_meta_completo_nao_le_pdf() -> None:
    """Se meta já tem cnpj+razao completo, não deve ler o PDF."""
    from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta

    base_dir = "/fake/pasta"

    # Meta completo: já tem tudo
    mock_classified = [
        {
            "kind": "cartao_cnpj",
            "path": "/fake/cartao.pdf",
            "meta": {"cnpj": "11.222.333/0001-44", "razao_social": "JÁ EXTRAÍDO SA"},
        }
    ]

    with (
        patch("src.utils.file_utils.list_and_classify_pdfs") as mock_classify,
        patch("src.utils.pdf_reader.read_pdf_text") as mock_read,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        mock_classify.return_value = mock_classified
        mock_read.side_effect = AssertionError("read_pdf_text NÃO deve ser chamado!")

        result = extrair_dados_cartao_cnpj_em_pasta(base_dir)

        assert result["cnpj"] == "11.222.333/0001-44"
        assert result["razao_social"] == "JÁ EXTRAÍDO SA"
        mock_read.assert_not_called()


@pytest.mark.unit
def test_extrair_cartao_cnpj_sem_path_chama_fallback() -> None:
    """Se classificador não retornar path, deve chamar fallback pesado."""
    from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta

    base_dir = "/fake/pasta"

    # Sem path: forçar fallback
    mock_classified = [{"kind": "cartao_cnpj"}]

    with (
        patch("src.utils.file_utils.list_and_classify_pdfs") as mock_classify,
        patch("src.utils.pdf_reader.read_pdf_text") as mock_read,
        patch("src.utils.file_utils.find_cartao_cnpj_pdf") as mock_find,
        patch("src.utils.text_utils.extract_company_fields") as mock_extract,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        mock_classify.return_value = mock_classified
        mock_find.return_value = Path("/fake/pasta/found.pdf")
        mock_read.return_value = "CNPJ: 55.666.777/0001-88"
        mock_extract.return_value = {"cnpj": "55.666.777/0001-88", "razao_social": None}

        result = extrair_dados_cartao_cnpj_em_pasta(base_dir)

        assert result["cnpj"] == "55.666.777/0001-88"
        mock_find.assert_called_once_with(base_dir)


@pytest.mark.unit
def test_extrair_cartao_cnpj_ambos_campos_vazios_fallback() -> None:
    """Se classificador não retornar dados, chama fallback."""
    from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta

    base_dir = "/fake/pasta"

    with (
        patch("src.utils.file_utils.list_and_classify_pdfs") as mock_classify,
        patch("src.utils.file_utils.find_cartao_cnpj_pdf") as mock_find,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        mock_classify.return_value = []  # Nenhum doc
        mock_find.return_value = None

        result = extrair_dados_cartao_cnpj_em_pasta(base_dir)

        assert result["cnpj"] is None
        assert result["razao_social"] is None
        mock_find.assert_called_once_with(base_dir)
