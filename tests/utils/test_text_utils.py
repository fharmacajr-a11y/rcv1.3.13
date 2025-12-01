import logging

import src.utils.text_utils as text_utils


def test_fix_mojibake_pass_through():
    original = "Joao"
    assert text_utils.fix_mojibake(original) == original
    assert text_utils.fix_mojibake(None) is None


def test_normalize_ascii_removes_accents():
    assert text_utils.normalize_ascii("Áéíõ Ç") == "Aeio C"
    assert text_utils.normalize_ascii(None) == ""


def test_clean_text_collapses_whitespace():
    assert text_utils.clean_text("  hello \n  world\t") == "hello world"
    assert text_utils.clean_text(None) == ""


def test_only_digits_and_cnpj_checks():
    assert text_utils.only_digits("12.a-34") == "1234"
    assert text_utils.cnpj_is_valid("12.345.678/0001-95") is True
    assert text_utils.cnpj_is_valid("123") is False


def test_format_cnpj_returns_formatted_when_valid():
    assert text_utils.format_cnpj("12345678000195") == "12.345.678/0001-95"
    assert text_utils.format_cnpj("invalid") == "invalid"


def test_clean_company_name_handles_none_and_trims():
    assert text_utils._clean_company_name(None) is None
    assert text_utils._clean_company_name("   ") is None
    assert text_utils._clean_company_name("  ACME   Ltda  ") == "ACME Ltda"
    assert text_utils._clean_company_name("ACME – SA") == "ACME – SA"


def test_match_and_label_helpers():
    assert text_utils._match_label("Razao Social: ACME") is not None
    assert text_utils._is_label_only("Razao Social:") is True
    assert text_utils._is_label_only("ACME") is False
    assert text_utils._is_skip_value("Filial") is True
    assert text_utils._is_skip_value("ACME") is False


def test_next_nonempty_value_skips_empty_and_cnpj():
    lines = ["Razao Social:", "", "ACME LTDA", "CNPJ 12.345.678/0001-95"]
    assert text_utils._next_nonempty_value(lines, 0) == "ACME LTDA"


def test_extract_razao_by_label_prefers_inline_value():
    lines = ["Razao Social: ACME Ltda", "Outra linha"]
    assert text_utils._extract_razao_by_label(lines) == "ACME Ltda"


def test_extract_razao_near_cnpj_finds_longest_candidate():
    lines = ["linha", "CNPJ 12.345.678/0001-95", "ACME", "ACME INDUSTRIA LTDA"]
    assert text_utils._extract_razao_near_cnpj(lines, 1) == "ACME INDUSTRIA LTDA"


def test_extract_company_fields_with_label_and_cnpj():
    text = "Razao Social: ACME Ltda\nCNPJ: 12345678000195\nEndereco"
    result = text_utils.extract_company_fields(text)
    assert result == {"cnpj": "12.345.678/0001-95", "razao_social": "ACME Ltda"}


def test_extract_cnpj_razao_delegates_to_fields():
    text = "CNPJ 12.345.678/0001-95\nRazao Social: ACME"
    assert text_utils.extract_cnpj_razao(text) == ("12.345.678/0001-95", "ACME")


def test_fix_mojibake_logs_decode_error(caplog):
    value = "erro\u00c3texto"
    with caplog.at_level(logging.ERROR):
        result = text_utils.fix_mojibake(value)
    assert result == value
    assert "Erro ao corrigir mojibake" in caplog.text


def test_match_label_none_for_empty_input():
    assert text_utils._match_label("") is None
    assert text_utils._match_label(None) is None


def test_is_label_only_false_for_empty_input():
    assert text_utils._is_label_only("") is False
    assert text_utils._is_label_only(None) is False


def test_next_nonempty_value_none_when_out_of_range():
    assert text_utils._next_nonempty_value(["Razao Social"], 0) is None


def test_next_nonempty_value_ignores_cnpj_number():
    lines = ["Razao Social:", "12.345.678/0001-95"]
    assert text_utils._next_nonempty_value(lines, 0) is None


def test_next_nonempty_value_ignores_cnpj_label_text():
    lines = ["Razao Social:", "CNPJ informado na linha seguinte"]
    assert text_utils._next_nonempty_value(lines, 0) is None


def test_next_nonempty_value_rejects_label_only_candidate():
    lines = ["Razao Social:", " Razao Social:"]
    assert text_utils._next_nonempty_value(lines, 0) is None


def test_extract_razao_by_label_returns_none_without_value():
    lines = ["Razao Social:", "", "CNPJ: 12.345.678/0001-95"]
    assert text_utils._extract_razao_by_label(lines) is None


def test_extract_razao_near_cnpj_skips_only_invalid_candidates():
    lines = [
        "",
        "Filial",
        "CNPJ: 12.345.678/0001-90",
        "CNPJ repetido 11.111.111/1111-11",
        "CNPJ apenas texto",
    ]
    assert text_utils._extract_razao_near_cnpj(lines, 2) is None


def test_extract_company_fields_returns_none_when_text_missing():
    assert text_utils.extract_company_fields("") == {"cnpj": None, "razao_social": None}


def test_extract_company_fields_without_cnpj_returns_label_value():
    text = "Razao Social: Empresa Sem CNPJ"
    result = text_utils.extract_company_fields(text)
    assert result == {"cnpj": None, "razao_social": "Empresa Sem"}


def test_extract_company_fields_without_label_uses_near_cnpj():
    text = "Linha qualquer\nCNPJ: 12.345.678/0001-95\nOficina Importante Ltda"
    result = text_utils.extract_company_fields(text)
    assert result == {"cnpj": "12.345.678/0001-95", "razao_social": "Oficina Importante Ltda"}


def test_extract_company_fields_fallback_search_when_line_scan_misses(monkeypatch):
    text = "Linha A 12.345.678/0001-95\nLinha B Sem Label"
    original_pattern = text_utils.RE_CNPJ

    class WholeTextPattern:
        def search(self, value: str):
            if "\n" in value:
                return original_pattern.search(value)
            return None

    monkeypatch.setattr(text_utils, "RE_CNPJ", WholeTextPattern())
    result = text_utils.extract_company_fields(text)
    assert result == {"cnpj": "12.345.678/0001-95", "razao_social": "Linha B Sem Label"}
