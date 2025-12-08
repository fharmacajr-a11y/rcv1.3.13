# -*- coding: utf-8 -*-
"""Testes para validação das funções canônicas de CNPJ após FASE 3.

Este arquivo documenta o comportamento esperado das implementações canônicas
em src/core/cnpj_norm.py e verifica que os wrappers delegam corretamente.
"""

from __future__ import annotations

import pytest


class TestNormalizeCNPJDigits:
    """Valida comportamento da função canônica normalize_cnpj_digits."""

    def test_canonical_location(self) -> None:
        """Implementação canônica deve estar em src.core.cnpj_norm."""
        from src.core.cnpj_norm import normalize_cnpj_digits

        assert normalize_cnpj_digits is not None
        assert callable(normalize_cnpj_digits)

    @pytest.mark.parametrize(
        ("input_value", "expected_output"),
        [
            # None retorna string vazia
            (None, ""),
            # String vazia retorna string vazia
            ("", ""),
            # CNPJ formatado -> apenas dígitos
            ("12.345.678/0001-90", "12345678000190"),
            # CNPJ já limpo
            ("12345678000190", "12345678000190"),
            # Com espaços
            ("12 345 678 0001 90", "12345678000190"),
            # Com letras (remove)
            ("ABC12345678000190XYZ", "12345678000190"),
            # Apenas letras (retorna vazio)
            ("ABCDEF", ""),
            # Números misturados
            ("123", "123"),
            # Zero
            (0, "0"),
            # Inteiro
            (12345678000190, "12345678000190"),
        ],
    )
    def test_normalize_cnpj_digits_behavior(self, input_value: object, expected_output: str) -> None:
        """Valida comportamento canônico de normalize_cnpj_digits."""
        from src.core.cnpj_norm import normalize_cnpj_digits

        result = normalize_cnpj_digits(input_value)
        assert result == expected_output
        assert isinstance(result, str)


class TestNormalizeCNPJ:
    """Valida comportamento da função normalize_cnpj (alfanumérico)."""

    def test_canonical_location(self) -> None:
        """Implementação canônica deve estar em src.core.cnpj_norm."""
        from src.core.cnpj_norm import normalize_cnpj

        assert normalize_cnpj is not None
        assert callable(normalize_cnpj)

    @pytest.mark.parametrize(
        ("input_value", "expected_output"),
        [
            # None retorna string vazia
            (None, ""),
            # String vazia retorna string vazia
            ("", ""),
            # CNPJ numérico
            ("12.345.678/0001-90", "12345678000190"),
            # CNPJ alfanumérico hipotético
            ("ABC123XYZ456", "ABC123XYZ456"),
            # Com diacríticos (remove)
            ("AÇÚCAR123", "ACUCAR123"),
            # Lowercase -> uppercase
            ("abc123", "ABC123"),
            # Com pontuação (remove)
            ("A.B-C/123", "ABC123"),
        ],
    )
    def test_normalize_cnpj_behavior(self, input_value: object, expected_output: str) -> None:
        """Valida comportamento canônico de normalize_cnpj alfanumérico."""
        from src.core.cnpj_norm import normalize_cnpj

        result = normalize_cnpj(input_value)
        assert result == expected_output
        assert isinstance(result, str)


class TestIsValidCNPJ:
    """Valida comportamento da função canônica is_valid_cnpj."""

    def test_canonical_location(self) -> None:
        """Implementação canônica deve estar em src.core.cnpj_norm."""
        from src.core.cnpj_norm import is_valid_cnpj

        assert is_valid_cnpj is not None
        assert callable(is_valid_cnpj)

    @pytest.mark.parametrize(
        ("cnpj", "expected_valid"),
        [
            # CNPJs válidos conhecidos (validados com algoritmo DV)
            ("11.222.333/0001-65", True),
            ("11222333000165", True),
            ("12.345.678/0001-10", True),
            ("12345678000110", True),
            # CNPJ inválido (DV errado)
            ("11.222.333/0001-99", False),
            ("12345678000195", False),
            ("12345678000190", False),
            # Todos os dígitos iguais (inválido)
            ("00000000000000", False),
            ("11111111111111", False),
            ("99999999999999", False),
            # Tamanho errado
            ("123", False),
            ("123456789012345", False),
            ("", False),
            # None
            (None, False),
            # String vazia
            ("", False),
            # Apenas letras
            ("ABCDEFGHIJKLMN", False),
        ],
    )
    def test_is_valid_cnpj_behavior(self, cnpj: object, expected_valid: bool) -> None:
        """Valida comportamento canônico de is_valid_cnpj."""
        from src.core.cnpj_norm import is_valid_cnpj

        result = is_valid_cnpj(cnpj)
        assert result == expected_valid
        assert isinstance(result, bool)

    def test_is_valid_cnpj_with_formatting(self) -> None:
        """CNPJ válido com formatação deve ser aceito."""
        from src.core.cnpj_norm import is_valid_cnpj

        # CNPJ válido conhecido com várias formatações
        valid_cnpj = "11222333000165"
        assert is_valid_cnpj(valid_cnpj) is True
        assert is_valid_cnpj("11.222.333/0001-65") is True
        assert is_valid_cnpj("11 222 333 0001 65") is True

    def test_is_valid_cnpj_rejects_repeated_digits(self) -> None:
        """CNPJs com todos os dígitos iguais devem ser rejeitados."""
        from src.core.cnpj_norm import is_valid_cnpj

        for digit in "0123456789":
            repeated = digit * 14
            assert is_valid_cnpj(repeated) is False, f"CNPJ {repeated} deveria ser inválido"


class TestWrapperDelegation:
    """Valida que wrappers delegam corretamente para implementação canônica."""

    def test_validators_normalize_cnpj_delegates(self) -> None:
        """validators.normalize_cnpj deve delegar para normalize_cnpj_digits."""
        from src.core.cnpj_norm import normalize_cnpj_digits as canonical
        from src.utils.validators import normalize_cnpj as wrapper

        assert wrapper("12.345.678/0001-90") == canonical("12.345.678/0001-90")
        assert wrapper(None) == canonical(None)
        assert wrapper("") == canonical("")

    def test_validators_is_valid_cnpj_delegates(self) -> None:
        """validators.is_valid_cnpj deve delegar para core."""
        from src.core.cnpj_norm import is_valid_cnpj as canonical
        from src.utils.validators import is_valid_cnpj as wrapper

        # CNPJ válido
        assert wrapper("11.222.333/0001-65") == canonical("11.222.333/0001-65")
        assert wrapper("11.222.333/0001-65") is True

        # CNPJ inválido
        assert wrapper("12345678000195") == canonical("12345678000195")
        assert wrapper("12345678000195") is False

        # None
        assert wrapper(None) == canonical(None)
        assert wrapper(None) is False

    def test_text_utils_cnpj_is_valid_delegates(self) -> None:
        """text_utils.cnpj_is_valid deve delegar para core com validação DV."""
        from src.core.cnpj_norm import is_valid_cnpj as canonical
        from src.utils.text_utils import cnpj_is_valid as wrapper

        # CNPJ válido
        assert wrapper("11.222.333/0001-65") == canonical("11.222.333/0001-65")
        assert wrapper("11.222.333/0001-65") is True

        # CNPJ inválido (agora valida DV, não apenas tamanho!)
        assert wrapper("12345678000195") is False  # DV errado
        assert wrapper("00000000000000") is False  # Todos iguais

        # None
        assert wrapper(None) == canonical(None)
        assert wrapper(None) is False


class TestBackwardCompatibility:
    """Garante compatibilidade com comportamentos esperados."""

    def test_all_wrappers_validate_dv(self) -> None:
        """Todos os wrappers agora validam DV completo."""
        from src.core.cnpj_norm import is_valid_cnpj as canonical
        from src.utils.text_utils import cnpj_is_valid as text_wrapper
        from src.utils.validators import is_valid_cnpj as validators_wrapper

        valid_cnpj = "11.222.333/0001-65"
        invalid_cnpj = "12345678000195"

        # Todos devem validar DV
        assert canonical(valid_cnpj) is True
        assert text_wrapper(valid_cnpj) is True
        assert validators_wrapper(valid_cnpj) is True

        assert canonical(invalid_cnpj) is False
        assert text_wrapper(invalid_cnpj) is False
        assert validators_wrapper(invalid_cnpj) is False

    def test_normalize_cnpj_digits_consistent(self) -> None:
        """normalize_cnpj_digits deve ser consistente em todos os pontos."""
        from src.core.cnpj_norm import normalize_cnpj_digits as canonical
        from src.utils.validators import normalize_cnpj as validators_wrapper

        cnpj_formatted = "12.345.678/0001-90"
        expected = "12345678000190"

        assert canonical(cnpj_formatted) == expected
        assert validators_wrapper(cnpj_formatted) == expected
