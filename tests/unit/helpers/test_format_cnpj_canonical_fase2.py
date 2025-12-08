# -*- coding: utf-8 -*-
"""Testes para validação da função canônica format_cnpj após FASE 2.

Este arquivo documenta o comportamento esperado da implementação canônica
e verifica que os wrappers delegam corretamente para ela.
"""

from __future__ import annotations

import pytest


class TestFormatCNPJCanonical:
    """Valida comportamento da implementação canônica de format_cnpj."""

    def test_canonical_location(self) -> None:
        """Implementação canônica deve estar em src.helpers.formatters."""
        from src.helpers.formatters import format_cnpj

        assert format_cnpj is not None
        assert callable(format_cnpj)

    @pytest.mark.parametrize(
        ("input_value", "expected_output"),
        [
            # None retorna string vazia
            (None, ""),
            # String vazia retorna string vazia
            ("", ""),
            # Zero retorna string vazia
            (0, ""),
            # 14 dígitos - formatado
            ("12345678000190", "12.345.678/0001-90"),
            (12345678000190, "12.345.678/0001-90"),
            # Já formatado - idempotente
            ("12.345.678/0001-90", "12.345.678/0001-90"),
            # Menos de 14 dígitos - retorna original
            ("123", "123"),
            ("12345", "12345"),
            # Mais de 14 dígitos - retorna original
            ("123456789012345", "123456789012345"),
            # Com caracteres especiais mas 14 dígitos - formatado
            ("12.345.678/0001-90", "12.345.678/0001-90"),
            ("12 345 678 0001 90", "12.345.678/0001-90"),
        ],
    )
    def test_canonical_behavior(self, input_value: str | int | float | None, expected_output: str) -> None:
        """Valida comportamento canônico para vários tipos de entrada."""
        from src.helpers.formatters import format_cnpj

        result = format_cnpj(input_value)  # type: ignore[arg-type]
        assert result == expected_output


class TestFormatCNPJWrappers:
    """Valida que wrappers delegam corretamente para implementação canônica."""

    def test_text_utils_wrapper_delegates(self) -> None:
        """text_utils.format_cnpj deve delegar para canônico."""
        from src.helpers.formatters import format_cnpj as canonical
        from src.utils.text_utils import format_cnpj as wrapper

        # Comportamento idêntico para casos comuns
        assert wrapper("12345678000190") == canonical("12345678000190")
        assert wrapper("123") == canonical("123")
        assert wrapper("") is None  # Mantém comportamento original

        # None input -> None output (compatibilidade)
        assert wrapper(None) is None

    def test_passwords_utils_wrapper_delegates(self) -> None:
        """passwords/utils.format_cnpj deve delegar para canônico."""
        from src.helpers.formatters import format_cnpj as canonical
        from src.modules.passwords.utils import format_cnpj as wrapper

        assert wrapper("12345678000190") == canonical("12345678000190")
        assert wrapper("12.345.678/0001-90") == canonical("12.345.678/0001-90")
        assert wrapper("123") == canonical("123")

    def test_uploads_helpers_wrapper_delegates(self) -> None:
        """uploads/helpers.format_cnpj_for_display deve delegar para canônico."""
        from src.helpers.formatters import format_cnpj as canonical
        from src.modules.uploads.components.helpers import format_cnpj_for_display as wrapper

        assert wrapper("12345678000190") == canonical("12345678000190")
        assert wrapper("12.345.678/0001-90") == canonical("12.345.678/0001-90")
        assert wrapper("") == canonical("")

    def test_pick_mode_wrapper_delegates(self) -> None:
        """pick_mode._format_cnpj_for_pick deve delegar para canônico."""
        from src.helpers.formatters import format_cnpj as canonical
        from src.modules.clientes.views.pick_mode import PickModeController

        assert PickModeController._format_cnpj_for_pick("12345678000190") == canonical("12345678000190")
        assert PickModeController._format_cnpj_for_pick(None) == canonical(None)
        assert PickModeController._format_cnpj_for_pick("") == canonical("")

    def test_client_picker_wrapper_delegates(self) -> None:
        """client_picker._format_cnpj deve delegar para canônico."""
        from src.helpers.formatters import format_cnpj as canonical
        from src.modules.clientes.forms.client_picker import _format_cnpj as wrapper

        assert wrapper("12345678000190") == canonical("12345678000190")
        assert wrapper("12.345.678/0001-90") == canonical("12.345.678/0001-90")
        assert wrapper("") == canonical("")


class TestBackwardCompatibility:
    """Garante que comportamentos específicos de wrappers foram preservados."""

    def test_text_utils_returns_none_for_none_input(self) -> None:
        """text_utils.format_cnpj deve retornar None quando receber None (compatibilidade)."""
        from src.utils.text_utils import format_cnpj

        assert format_cnpj(None) is None

    def test_text_utils_returns_none_for_empty_string(self) -> None:
        """text_utils.format_cnpj deve retornar None quando receber string vazia."""
        from src.utils.text_utils import format_cnpj

        # String vazia retorna None (compatibilidade com comportamento original)
        assert format_cnpj("") is None

    def test_all_wrappers_handle_14_digits(self) -> None:
        """Todos os wrappers devem formatar corretamente CNPJ com 14 dígitos."""
        from src.helpers.formatters import format_cnpj as canonical
        from src.modules.clientes.forms.client_picker import _format_cnpj as picker_wrapper
        from src.modules.clientes.views.pick_mode import PickModeController
        from src.modules.passwords.utils import format_cnpj as pwd_wrapper
        from src.modules.uploads.components.helpers import format_cnpj_for_display as upload_wrapper
        from src.utils.text_utils import format_cnpj as text_wrapper

        cnpj_raw = "12345678000190"
        expected = "12.345.678/0001-90"

        assert canonical(cnpj_raw) == expected
        assert text_wrapper(cnpj_raw) == expected
        assert pwd_wrapper(cnpj_raw) == expected
        assert upload_wrapper(cnpj_raw) == expected
        assert PickModeController._format_cnpj_for_pick(cnpj_raw) == expected
        assert picker_wrapper(cnpj_raw) == expected
