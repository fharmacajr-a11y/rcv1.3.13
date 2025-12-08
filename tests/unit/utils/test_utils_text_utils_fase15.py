from __future__ import annotations

import src.utils.text_utils as text_utils


def test_fix_mojibake_with_marker_returns_original_on_decode_error() -> None:
    s = "abcǟdef"  # contém marcador esperado, mas falha ao decodificar latin1->utf8
    assert text_utils.fix_mojibake(s) == s


def test_normalize_ascii_strips_accents() -> None:
    assert text_utils.normalize_ascii("ação ÇÃÕ") == "acao CAO"
    assert text_utils.normalize_ascii("") == ""


def test_clean_text_collapses_whitespace() -> None:
    assert text_utils.clean_text("  a \n b\tc  ") == "a b c"
    assert text_utils.clean_text("") == ""


def test_only_digits_and_cnpj_validation() -> None:
    assert text_utils.only_digits("12a.34-56") == "123456"
    # CNPJ válido com DV correto (12.345.678/0001-10)
    assert text_utils.cnpj_is_valid("12.345.678/0001-10") is True
    assert text_utils.cnpj_is_valid("123") is False


def test_format_cnpj_valid_and_invalid() -> None:
    assert text_utils.format_cnpj("12345678000190") == "12.345.678/0001-90"
    assert text_utils.format_cnpj("short") == "short"


def test_clean_company_name_handles_none_and_spaces() -> None:
    assert text_utils._clean_company_name(None) is None
    assert text_utils._clean_company_name("   ") is None
    assert text_utils._clean_company_name("Empresa  --  X") == "Empresa -- X"


def test_label_detection_helpers() -> None:
    assert text_utils._match_label("Razão Social: ACME Ltda")
    assert text_utils._is_label_only("Razão Social:")
    assert text_utils._is_skip_value(" Matriz ")


def test_next_nonempty_value_skips_labels_and_cnpj() -> None:
    lines = ["", "CNPJ: 12.345.678/0001-90", "Razao Social:", "Filial", "   ", "Empresa Legal Ltda"]
    value = text_utils._next_nonempty_value(lines, 1)
    assert value is None


def test_next_nonempty_value_returns_value_when_first_non_label() -> None:
    lines = ["CNPJ:", "", "   ", "Empresa Legal Ltda"]
    value = text_utils._next_nonempty_value(lines, 0)
    assert value == "Empresa Legal Ltda"


def test_extract_razao_by_label_with_inline_value() -> None:
    lines = ["Razao Social -   ACME LTDA", "Outra linha"]
    razao = text_utils._extract_razao_by_label(lines)
    assert razao == "ACME LTDA"


def test_extract_razao_near_cnpj_picks_longest_candidate() -> None:
    lines = [
        "linha vazia",
        "CNPJ: 12.345.678/0001-90",
        "ACME",
        "ACME Industria e Comercio Ltda",
        "CNPJ repetido 00.000.000/0000-00",
    ]
    razao = text_utils._extract_razao_near_cnpj(lines, 1)
    assert razao == "ACME Industria e Comercio Ltda"


def test_extract_company_fields_with_label_and_cnpj() -> None:
    text = "Razão Social: Minha Empresa\nCNPJ: 12.345.678/0001-90"
    result = text_utils.extract_company_fields(text)
    assert result["cnpj"] == "12.345.678/0001-90"
    assert result["razao_social"] == "Minha Empresa"


def test_extract_company_fields_without_label_uses_near_cnpj() -> None:
    text = "Linha qualquer\nCNPJ: 12.345.678/0001-90\nEmpresa XYZ S.A."
    result = text_utils.extract_company_fields(text)
    assert result["cnpj"] == "12.345.678/0001-90"
    assert result["razao_social"] == "XYZ S.A."


def test_extract_company_fields_missing_returns_none_fields() -> None:
    assert text_utils.extract_company_fields("") == {"cnpj": None, "razao_social": None}


def test_extract_cnpj_razao_tuple() -> None:
    cnpj, razao = text_utils.extract_cnpj_razao("CNPJ: 12.345.678/0001-90\nEmpresa ABC")
    assert cnpj == "12.345.678/0001-90"
    assert razao == "ABC"
