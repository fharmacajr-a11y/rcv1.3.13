import unittest

from utils.text_utils import extract_company_fields


class ExtractCompanyFieldsTests(unittest.TestCase):
    def test_label_same_line(self) -> None:
        text = "CNPJ: 09.023.986/0001-90\n" "Raz\u00e3o Social: C C CAMPOS LTDA"
        result = extract_company_fields(text)
        self.assertEqual("09.023.986/0001-90", result["cnpj"])
        self.assertEqual("C C CAMPOS LTDA", result["razao_social"])

    def test_label_next_line(self) -> None:
        text = "NOME EMPRESARIAL\n" "A DE LIMA FARMACIA\n" "... outras linhas ...\n" "CNPJ 05788603000113"
        result = extract_company_fields(text)
        self.assertEqual("05.788.603/0001-13", result["cnpj"])
        self.assertEqual("A DE LIMA FARMACIA", result["razao_social"])

    def test_label_without_accent(self) -> None:
        text = "Razao Social - ACME INDUSTRIA E COMERCIO LTDA \u2013 EPP\n" "CNPJ: 19571609000109"
        result = extract_company_fields(text)
        self.assertEqual("19.571.609/0001-09", result["cnpj"])
        self.assertEqual("ACME INDUSTRIA E COMERCIO LTDA \u2013 EPP", result["razao_social"])


if __name__ == "__main__":
    unittest.main()
