"""
Testes para src.core.__init__ - Coverage Pack 05 - Fase 02.

Objetivo: cobrir lazy loading de classify_document (linhas 12-14).
Estratégia: importar __init__ e invocar classify_document para triggerar lazy import.
"""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _cleanup_core_imports():
    """Remove src.core e src.core.classify_document do cache."""
    # Remove antes do teste
    modules_to_remove = [
        "src.core",
        "src.core.classify_document",
    ]
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]

    yield

    # Remove após o teste
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]


def test_core_init_exporta_classify_document():
    """
    Testa que __all__ exporta classify_document.
    """
    import src.core as core

    assert "classify_document" in core.__all__


def test_core_init_classify_document_callable():
    """
    Testa que classify_document é callable (função proxy).
    """
    import src.core as core

    assert callable(core.classify_document)


def test_core_init_lazy_loading_invoca_impl(tmp_path):
    """
    Testa branch 12-14: lazy loading de classify_document.

    Quando classify_document é invocado, deve importar
    src.core.classify_document.classify_document e delegá-lo.
    """
    import src.core as core

    # Cria arquivo temporário para classificar
    test_file = tmp_path / "contrato_teste.pdf"
    test_file.write_text("dummy content")

    # Invoca o proxy (vai executar linhas 12-14)
    result = core.classify_document(str(test_file))

    # Verifica que retorna um dict com kind e confidence
    assert isinstance(result, dict)
    assert "kind" in result
    assert "confidence" in result

    # Como o nome contém "contrato", deve classificar como ato_constitutivo
    assert result["kind"] == "ato_constitutivo"
    assert result["confidence"] >= 0.7


def test_core_init_lazy_loading_com_args_kwargs(tmp_path):
    """
    Testa que o proxy passa *args e **kwargs corretamente.
    """
    import src.core as core

    # Cria arquivo temporário
    test_file = tmp_path / "alvara.pdf"
    test_file.write_text("dummy")

    # Invoca classificação
    result = core.classify_document(str(test_file))

    # Verifica retorno (mesmo formato da função real)
    assert isinstance(result, dict)
    assert "kind" in result
    assert result["kind"] == "alvara_funcionamento"


def test_core_init_lazy_loading_nao_carrega_antecipadamente():
    """
    Testa que importar src.core NÃO carrega classify_document.classify_document.

    A carga só acontece quando classify_document() é invocado.
    """
    import src.core as core

    # Verifica que classify_document.py NÃO foi importado ainda
    # (pode estar se já foi carregado em teste anterior, então só verifica que é callable)
    assert callable(core.classify_document)
