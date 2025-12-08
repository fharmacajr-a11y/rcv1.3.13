"""
Testes para src/helpers/formatters.py (TEST-001 Fase 10, atualizado Fase 11).

Cobertura:
- format_cnpj (formatação de CNPJ)
- format_datetime (formatação de data/hora padrão ISO - CANÔNICA desde FASE 11)
- fmt_datetime (wrapper deprecado para format_datetime)
- fmt_datetime_br (formatação de data/hora padrão brasileiro)
- _parse_any_dt (parser interno de datas - testado indiretamente)
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

import pytest

from src.helpers.formatters import format_cnpj, format_datetime, fmt_datetime, fmt_datetime_br


# --- Testes para format_cnpj ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Happy path - CNPJ válido sem formatação
        ("12345678000190", "12.345.678/0001-90"),
        ("00000000000191", "00.000.000/0001-91"),
        ("99999999999999", "99.999.999/9999-99"),
        # CNPJ já formatado - mantém formato
        ("12.345.678/0001-90", "12.345.678/0001-90"),
        # CNPJ com espaços/caracteres extras - remove e formata
        ("  12345678000190  ", "12.345.678/0001-90"),
        ("12.345.678/0001-90  ", "12.345.678/0001-90"),
        # CNPJ com tamanho incorreto - retorna original
        ("123456780001", "123456780001"),  # 12 dígitos (falta 2)
        ("1234567800019000", "1234567800019000"),  # 16 dígitos (sobra 2)
        ("123", "123"),  # muito curto
        # Edge cases - None e vazio
        ("", ""),
        # CNPJ com letras/caracteres especiais - remove e formata se 14 dígitos
        ("12.345.678/0001-90", "12.345.678/0001-90"),
        ("12ABC345DEF678GHI0001JKL90", "12.345.678/0001-90"),  # 14 dígitos no meio do lixo
    ],
)
def test_format_cnpj(raw: str, expected: str) -> None:
    """Testa formatação de CNPJ com vários inputs."""
    assert format_cnpj(raw) == expected


def test_format_cnpj_none() -> None:
    """Testa format_cnpj com None (edge case)."""
    # A função espera str, mas pode receber None em runtime
    # Verificar comportamento defensivo
    assert format_cnpj(None) == ""  # type: ignore[arg-type]


def test_format_cnpj_numeric_types() -> None:
    """Testa format_cnpj com tipos numéricos (conversão para str)."""
    # Se passar int/float, deve converter para str
    assert format_cnpj(12345678000190) == "12.345.678/0001-90"  # type: ignore[arg-type]


def test_format_cnpj_idempotent() -> None:
    """Testa idempotência: aplicar format_cnpj duas vezes deve dar o mesmo resultado."""
    raw = "12345678000190"
    formatted_once = format_cnpj(raw)
    formatted_twice = format_cnpj(formatted_once)
    assert formatted_once == formatted_twice == "12.345.678/0001-90"


# --- Testes para format_datetime (CANÔNICA desde FASE 11) ---


@pytest.mark.parametrize(
    "value,expected",
    [
        # None e vazio
        (None, ""),
        ("", ""),
        # datetime object
        (datetime(2025, 11, 21, 14, 30, 45), "2025-11-21 14:30:45"),
        (datetime(2000, 1, 1, 0, 0, 0), "2000-01-01 00:00:00"),
        # date object (converte para datetime com time 00:00:00)
        (date(2025, 11, 21), "2025-11-21 00:00:00"),
        (date(1999, 12, 31), "1999-12-31 00:00:00"),
        # String ISO
        ("2025-11-21T14:30:45", "2025-11-21 14:30:45"),
        ("2025-11-21", "2025-11-21 00:00:00"),
        # String formato padrão
        ("2025-11-21 14:30:45", "2025-11-21 14:30:45"),
        # String formato brasileiro com hora
        ("21/11/2025 14:30:45", "2025-11-21 14:30:45"),
        # String com espaços
        ("  2025-11-21 14:30:45  ", "2025-11-21 14:30:45"),
        # Timestamp (int/float)
        (1700000000, "2023-11-14 22:13:20"),  # Exemplo fixo
        (1700000000.5, "2023-11-14 22:13:20"),  # Float ignora fração
    ],
)
def test_format_datetime(value: Any, expected: str) -> None:
    """Testa formatação de datetime com vários tipos de input."""
    result = format_datetime(value)
    # Para timestamps, a conversão pode variar com timezone local
    # Vamos aceitar que o formato está correto
    if isinstance(value, (int, float)) and value != 0:
        assert len(result) == 19  # Formato "YYYY-MM-DD HH:MM:SS"
        assert result[4] == "-" and result[7] == "-" and result[10] == " "
        assert result[13] == ":" and result[16] == ":"
    else:
        assert result == expected


def test_format_datetime_invalid_string() -> None:
    """Testa format_datetime com string inválida (retorna a string original)."""
    invalid = "not-a-date"
    result = format_datetime(invalid)
    assert result == invalid


def test_format_datetime_timezone_aware() -> None:
    """Testa format_datetime com datetime timezone-aware (converte para local)."""
    dt_utc = datetime(2025, 11, 21, 12, 0, 0, tzinfo=timezone.utc)
    result = format_datetime(dt_utc)
    # Resultado depende do timezone local, mas deve ter formato correto
    assert len(result) == 19
    assert result[4] == "-" and result[10] == " "


def test_format_datetime_edge_case_zero_timestamp() -> None:
    """Testa format_datetime com timestamp zero (epoch)."""
    result = format_datetime(0)
    # Epoch: 1970-01-01 00:00:00 UTC (pode variar com timezone local)
    assert "1970-01-01" in result or "1969-12-31" in result  # Dependendo do TZ


def test_format_datetime_utc_string_converts_to_local() -> None:
    """Testa format_datetime com string UTC (Z) que converte para timezone local."""
    # UTC string é convertido para timezone local
    result = format_datetime("2025-11-21T14:30:45Z")
    # Deve ter formato correto, mas hora pode variar com timezone
    assert len(result) == 19
    assert result.startswith("2025-11-21")
    assert result[10] == " "


def test_format_datetime_br_date_without_time_not_parsed() -> None:
    """Testa format_datetime com formato brasileiro só data (não é parseado)."""
    # O parser não reconhece "DD/MM/YYYY" sem hora, retorna original
    result = format_datetime("21/11/2025")
    # Função retorna a string original quando não consegue parsear
    assert result == "21/11/2025"


# --- Testes para fmt_datetime (WRAPPER DEPRECADO) ---


def test_fmt_datetime_wrapper_delegates_to_format_datetime() -> None:
    """Testa que fmt_datetime delega corretamente para format_datetime."""
    dt = datetime(2025, 12, 7, 15, 30, 45)

    # Ambas devem retornar o mesmo resultado
    assert fmt_datetime(dt) == format_datetime(dt)
    assert fmt_datetime(None) == format_datetime(None)
    assert fmt_datetime("2025-12-07T15:30:45") == format_datetime("2025-12-07T15:30:45")


# --- Testes para fmt_datetime_br ---


@pytest.mark.parametrize(
    "value,expected",
    [
        # None e vazio
        (None, ""),
        ("", ""),
        # datetime object
        (datetime(2025, 11, 21, 14, 30, 45), "21/11/2025 - 14:30:45"),
        (datetime(2000, 1, 1, 0, 0, 0), "01/01/2000 - 00:00:00"),
        # date object
        (date(2025, 11, 21), "21/11/2025 - 00:00:00"),
        # String ISO
        ("2025-11-21T14:30:45", "21/11/2025 - 14:30:45"),
        ("2025-11-21", "21/11/2025 - 00:00:00"),
        # String formato padrão
        ("2025-11-21 14:30:45", "21/11/2025 - 14:30:45"),
        # String formato brasileiro
        ("21/11/2025 14:30:45", "21/11/2025 - 14:30:45"),
        ("21/11/2025", "21/11/2025 - 00:00:00"),
        # String com espaços
        ("  2025-11-21 14:30:45  ", "21/11/2025 - 14:30:45"),
    ],
)
def test_fmt_datetime_br(value: Any, expected: str) -> None:
    """Testa formatação de datetime no padrão brasileiro."""
    result = fmt_datetime_br(value)
    # Para timestamps, a conversão pode variar com timezone local
    if isinstance(value, (int, float)) and value != 0:
        # Apenas verifica formato
        assert " - " in result
        assert result.count("/") == 2
        assert result.count(":") == 2
    else:
        assert result == expected


def test_fmt_datetime_br_invalid_string() -> None:
    """Testa fmt_datetime_br com string inválida (retorna a string original)."""
    invalid = "not-a-date"
    result = fmt_datetime_br(invalid)
    assert result == invalid


def test_fmt_datetime_br_timestamp() -> None:
    """Testa fmt_datetime_br com timestamp."""
    # Timestamp fixo: 2023-11-14 22:13:20 UTC (aproximadamente)
    result = fmt_datetime_br(1700000000)
    # Resultado depende do timezone local
    assert " - " in result
    assert result.count("/") == 2
    assert "2023" in result


def test_fmt_datetime_br_timezone_aware() -> None:
    """Testa fmt_datetime_br com datetime timezone-aware."""
    dt_utc = datetime(2025, 11, 21, 12, 0, 0, tzinfo=timezone.utc)
    result = fmt_datetime_br(dt_utc)
    # Resultado depende do timezone local, mas deve ter formato correto
    assert " - " in result
    assert result.count("/") == 2


# --- Testes de integração/idempotência ---


def test_fmt_datetime_br_idempotent() -> None:
    """Testa que aplicar fmt_datetime_br no resultado não quebra."""
    dt = datetime(2025, 11, 21, 14, 30, 45)
    formatted = fmt_datetime_br(dt)
    # Aplicar novamente na string formatada
    formatted_again = fmt_datetime_br(formatted)
    # Deve reconhecer o formato brasileiro e retornar o mesmo
    assert formatted == formatted_again == "21/11/2025 - 14:30:45"


def test_format_datetime_idempotent() -> None:
    """Testa que aplicar format_datetime no resultado não quebra."""
    dt = datetime(2025, 11, 21, 14, 30, 45)
    formatted = format_datetime(dt)
    # Aplicar novamente na string formatada
    formatted_again = format_datetime(formatted)
    # Deve reconhecer o formato padrão e retornar o mesmo
    assert formatted == formatted_again == "2025-11-21 14:30:45"


# --- Testes de edge cases adicionais ---


def test_format_cnpj_empty_string() -> None:
    """Testa format_cnpj com string vazia."""
    assert format_cnpj("") == ""


def test_format_cnpj_whitespace_only() -> None:
    """Testa format_cnpj com apenas espaços."""
    assert format_cnpj("   ") == "   "  # Não tem 14 dígitos, retorna original


def test_format_datetime_date_only_string() -> None:
    """Testa format_datetime com string de data sem hora."""
    assert format_datetime("2025-11-21") == "2025-11-21 00:00:00"


def test_fmt_datetime_br_date_only_string() -> None:
    """Testa fmt_datetime_br com string de data sem hora."""
    assert fmt_datetime_br("21/11/2025") == "21/11/2025 - 00:00:00"


def test_format_datetime_with_time_object() -> None:
    """Testa format_datetime com objeto time (não suportado, deve retornar string do objeto)."""
    t = time(14, 30, 45)
    result = format_datetime(t)
    # time object não é convertido, retorna str(t)
    assert "14:30:45" in result


def test_fmt_datetime_br_with_time_object() -> None:
    """Testa fmt_datetime_br com objeto time (não suportado, deve retornar string do objeto)."""
    t = time(14, 30, 45)
    result = fmt_datetime_br(t)
    # time object não é convertido, retorna str(t)
    assert "14:30:45" in result


def test_format_cnpj_special_characters_only() -> None:
    """Testa format_cnpj com apenas caracteres especiais (sem dígitos)."""
    assert format_cnpj(".//-") == ".//-"  # Sem dígitos, retorna original


def test_format_cnpj_mixed_valid_length() -> None:
    """Testa format_cnpj com exatamente 14 dígitos misturados com lixo."""
    # "ABC12DEF345GHI678IJK000LMN190OPQ" tem 14 dígitos: 12345678000190
    raw = "ABC12DEF345GHI678IJK000LMN190OPQ"
    expected = "12.345.678/0001-90"
    assert format_cnpj(raw) == expected
