from __future__ import annotations

from pathlib import Path

import pytest

import src.core.classify_document as classify_document


@pytest.mark.parametrize(
    ("filename", "expected_label"),
    [
        ("cartao_cnpj_relatorio.pdf", "cartao_cnpj"),
        ("Contrato-Social.pdf", "ato_constitutivo"),
        ("ALVARA_funcionamento.pdf", "alvara_funcionamento"),
        ("CRF_regularidade.PDF", "crf_regularidade"),
        ("extrato-caixa-abril.pdf", "extrato_caixa"),
        ("comprovante_endereco_empresa.pdf", "endereco_empresa"),
        ("conta_luz_empresa.pdf", "endereco_empresa"),
    ],
)
def test_guess_by_name_detects_expected_labels(filename: str, expected_label: str) -> None:
    label, score = classify_document._guess_by_name(Path(filename))

    assert label == expected_label
    assert score == pytest.approx(0.9)


def test_guess_by_name_returns_unknown_label_for_other_files() -> None:
    label, score = classify_document._guess_by_name(Path("documento_generico.pdf"))

    assert label == "desconhecido"
    assert score == pytest.approx(0.2)


def test_classify_document_builds_payload_for_known_label() -> None:
    result = classify_document.classify_document("contrato-social.pdf")

    assert result["path"].endswith("contrato-social.pdf")
    assert result["kind"] == "ato_constitutivo"
    assert result["title"] == "Ato Constitutivo"
    assert result["confidence"] == pytest.approx(0.9)
    assert result["source"] == "filename"


def test_classify_document_uses_generic_title_when_label_missing(monkeypatch) -> None:
    def fake_guess(_: Path) -> tuple[str, float]:
        return "novo_documento", 0.37

    monkeypatch.setattr(classify_document, "_guess_by_name", fake_guess)
    result = classify_document.classify_document("qualquer.pdf")

    assert result["kind"] == "novo_documento"
    assert result["title"] == "Documento"
    assert result["confidence"] == pytest.approx(0.37)
    assert result["source"] == "filename"
