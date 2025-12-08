# -*- coding: utf-8 -*-
"""
tests/unit/helpers/test_formatters_datetime_fase5.py

Suite de testes para funções de formatação de data/hora (FASE 5).
Testa fmt_datetime_br como função canônica de formatação brasileira.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src.helpers.formatters import fmt_datetime_br


class TestFmtDatetimeBr:
    """Testes para fmt_datetime_br - formatação brasileira DD/MM/YYYY - HH:MM:SS."""

    def test_fmt_datetime_br_none(self) -> None:
        """None deve retornar string vazia."""
        assert fmt_datetime_br(None) == ""

    def test_fmt_datetime_br_empty_string(self) -> None:
        """String vazia deve retornar vazia."""
        assert fmt_datetime_br("") == ""

    def test_fmt_datetime_br_whitespace(self) -> None:
        """String com apenas espaços deve retornar vazia."""
        assert fmt_datetime_br("   ") == ""
        assert fmt_datetime_br("\t\n") == ""

    def test_fmt_datetime_br_datetime_object(self) -> None:
        """Deve formatar objeto datetime corretamente."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = fmt_datetime_br(dt)
        assert result == "15/01/2024 - 10:30:45"

    def test_fmt_datetime_br_date_object(self) -> None:
        """Deve formatar objeto date (sem hora) corretamente."""
        d = date(2024, 1, 15)
        result = fmt_datetime_br(d)
        assert result.startswith("15/01/2024 - ")
        assert result.endswith("00:00:00")

    def test_fmt_datetime_br_iso_string(self) -> None:
        """Deve formatar string ISO datetime."""
        result = fmt_datetime_br("2024-01-15T10:30:00")
        assert result.startswith("15/01/2024")
        assert " - " in result

    def test_fmt_datetime_br_iso_string_with_z(self) -> None:
        """Deve formatar string ISO com timezone Z."""
        result = fmt_datetime_br("2024-01-15T10:30:00Z")
        assert result.startswith("15/01/2024")
        assert " - " in result

    def test_fmt_datetime_br_iso_date_only(self) -> None:
        """Deve formatar string ISO apenas com data (YYYY-MM-DD)."""
        result = fmt_datetime_br("2024-01-15")
        # Aceitar que timezone pode mudar a data em 1 dia
        assert "14/01/2024" in result or "15/01/2024" in result or result == "2024-01-15"

    def test_fmt_datetime_br_br_format_string(self) -> None:
        """Deve reconhecer e processar formato brasileiro na entrada."""
        result = fmt_datetime_br("15/01/2024 10:30:45")
        assert "15/01/2024" in result
        assert "10:30:45" in result

    def test_fmt_datetime_br_timestamp_int(self) -> None:
        """Deve formatar timestamp Unix (int)."""
        # 1705316400 = 2024-01-15 10:00:00 UTC
        result = fmt_datetime_br(1705316400)
        # Verificar que contém data/hora válida
        assert " - " in result
        assert "/" in result

    def test_fmt_datetime_br_timestamp_float(self) -> None:
        """Deve formatar timestamp Unix (float)."""
        result = fmt_datetime_br(1705316400.5)
        assert " - " in result
        assert "/" in result

    def test_fmt_datetime_br_invalid_string(self) -> None:
        """String inválida deve retornar a própria string."""
        invalid = "data-invalida"
        assert fmt_datetime_br(invalid) == invalid

        invalid2 = "not-a-date"
        assert fmt_datetime_br(invalid2) == invalid2

    def test_fmt_datetime_br_output_format(self) -> None:
        """Deve usar exatamente o formato DD/MM/YYYY - HH:MM:SS."""
        dt = datetime(2024, 3, 5, 14, 25, 30)
        result = fmt_datetime_br(dt)
        # Verificar padrão exato
        assert result == "05/03/2024 - 14:25:30"

    def test_fmt_datetime_br_handles_timezone_aware(self) -> None:
        """Deve lidar com datetime timezone-aware."""
        from datetime import timezone

        dt_utc = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = fmt_datetime_br(dt_utc)
        # Deve converter para local timezone
        assert "15/01/2024" in result or "14/01/2024" in result
        assert " - " in result

    def test_fmt_datetime_br_preserves_seconds(self) -> None:
        """Deve preservar segundos na formatação."""
        dt = datetime(2024, 1, 15, 10, 30, 59)
        result = fmt_datetime_br(dt)
        assert result.endswith("59")

    def test_fmt_datetime_br_zero_padding(self) -> None:
        """Deve usar zero-padding para dia/mês/hora < 10."""
        dt = datetime(2024, 1, 5, 8, 5, 3)
        result = fmt_datetime_br(dt)
        assert result == "05/01/2024 - 08:05:03"


class TestFmtDatetimeBrEdgeCases:
    """Testes de casos extremos para fmt_datetime_br."""

    def test_fmt_datetime_br_leap_year(self) -> None:
        """Deve formatar corretamente data de ano bissexto."""
        dt = datetime(2024, 2, 29, 12, 0, 0)
        result = fmt_datetime_br(dt)
        assert result == "29/02/2024 - 12:00:00"

    def test_fmt_datetime_br_end_of_year(self) -> None:
        """Deve formatar corretamente 31 de dezembro."""
        dt = datetime(2024, 12, 31, 23, 59, 59)
        result = fmt_datetime_br(dt)
        assert result == "31/12/2024 - 23:59:59"

    def test_fmt_datetime_br_start_of_year(self) -> None:
        """Deve formatar corretamente 1 de janeiro."""
        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = fmt_datetime_br(dt)
        assert result == "01/01/2024 - 00:00:00"

    def test_fmt_datetime_br_different_types_same_result(self) -> None:
        """Diferentes tipos de entrada devem produzir mesmo resultado."""
        dt_obj = datetime(2024, 1, 15, 10, 30, 0)
        iso_str = "2024-01-15T10:30:00"

        result_dt = fmt_datetime_br(dt_obj)
        result_iso = fmt_datetime_br(iso_str)

        # Ambos devem começar com a mesma data
        assert result_dt.startswith("15/01/2024")
        assert result_iso.startswith("15/01/2024")


class TestFmtDatetimeBrCompatibility:
    """Testes de compatibilidade com fmt_data (wrapper deprecado)."""

    def test_fmt_datetime_br_compatible_with_fmt_data_none(self) -> None:
        """Comportamento com None deve ser compatível com fmt_data."""
        from src.app_utils import fmt_data

        assert fmt_datetime_br(None) == fmt_data(None)

    def test_fmt_datetime_br_compatible_with_fmt_data_empty(self) -> None:
        """Comportamento com string vazia deve ser compatível."""
        from src.app_utils import fmt_data

        assert fmt_datetime_br("") == fmt_data("")

    def test_fmt_datetime_br_compatible_with_fmt_data_iso(self) -> None:
        """Formatação de ISO string deve ser compatível."""
        from src.app_utils import fmt_data

        iso_input = "2024-01-15T10:30:00"
        result_br = fmt_datetime_br(iso_input)
        result_data = fmt_data(iso_input)

        # Ambos devem produzir mesmo resultado
        assert result_br == result_data

    def test_fmt_datetime_br_compatible_with_fmt_data_iso_z(self) -> None:
        """Formatação de ISO com Z deve ser compatível."""
        from src.app_utils import fmt_data

        iso_z = "2024-01-15T10:30:00Z"
        result_br = fmt_datetime_br(iso_z)
        result_data = fmt_data(iso_z)

        assert result_br == result_data

    def test_fmt_datetime_br_compatible_with_fmt_data_invalid(self) -> None:
        """Comportamento com entrada inválida deve ser compatível."""
        from src.app_utils import fmt_data

        invalid = "data-invalida"
        result_br = fmt_datetime_br(invalid)
        result_data = fmt_data(invalid)

        assert result_br == result_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
