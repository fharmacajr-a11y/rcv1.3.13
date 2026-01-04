from __future__ import annotations

import logging
import re
from datetime import date, datetime, time
from typing import Any, Final

logger = logging.getLogger(__name__)

APP_DATETIME_FMT: Final[str] = "%Y-%m-%d %H:%M:%S"


def format_cnpj(raw: str | int | float | None) -> str:
    """Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX.

    **Implementação canônica** de formatação de CNPJ no projeto.
    Todas as outras funções format_cnpj devem delegar para esta.

    Regras:
    - Se raw for falsy (None, "", 0), retorna "".
    - Converte raw para string, extrai apenas dígitos com regex.
    - Se após a limpeza não houver exatamente 14 dígitos, retorna o valor original como string.
    - Se houver 14 dígitos, aplica a máscara XX.XXX.XXX/XXXX-XX e retorna.

    Args:
        raw: CNPJ como string, int, float ou None. Aceita com ou sem formatação.

    Returns:
        CNPJ formatado se possuir 14 dígitos, caso contrário retorna original ou string vazia.

    Examples:
        >>> format_cnpj("12345678000190")
        '12.345.678/0001-90'
        >>> format_cnpj(12345678000190)
        '12.345.678/0001-90'
        >>> format_cnpj("12.345.678/0001-90")
        '12.345.678/0001-90'
        >>> format_cnpj(None)
        ''
        >>> format_cnpj("123")
        '123'
    """
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) != 14:
        return str(raw)
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"


def format_datetime(value: datetime | date | time | str | int | float | None) -> str:
    """Formata data/hora no padrão YYYY-MM-DD HH:MM:SS.

    **Implementação canônica** de formatação de data/hora em padrão ISO-like no projeto.
    Esta é a função recomendada para formatação de datetime em formato internacional.

    Regras:
    - Se value for None ou "", retorna "".
    - Aceita datetime, date, time, strings em formatos conhecidos (ISO, BR), timestamps numéricos.
    - Se timezone-aware, converte para timezone local.
    - Em caso de valor inválido não parseável, retorna str(value).

    Args:
        value: Data/hora como datetime, date, time, string ISO/BR, timestamp numérico, ou None.

    Returns:
        String formatada no padrão "YYYY-MM-DD HH:MM:SS" ou vazio se None/inválido.

    Examples:
        >>> format_datetime(datetime(2025, 12, 7, 15, 30, 45))
        '2025-12-07 15:30:45'
        >>> format_datetime("2025-12-07T15:30:45")
        '2025-12-07 15:30:45'
        >>> format_datetime(None)
        ''
        >>> format_datetime("invalid")
        'invalid'
    """
    if value is None or value == "":
        return ""
    dt: datetime | None = None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time())
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value)
    elif isinstance(value, str):
        s: str = value.strip()
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao interpretar data/hora ISO: %s", exc)
            for pat in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s, pat)
                    break
                except Exception as inner_exc:  # noqa: BLE001
                    logger.debug("Falha ao interpretar data/hora (%s): %s", pat, inner_exc)
    if dt is None:
        return str(value)
    try:
        if dt.tzinfo is not None:
            dt = dt.astimezone()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao ajustar timezone em format_datetime: %s", exc)
    return dt.strftime(APP_DATETIME_FMT)


def fmt_datetime(value: datetime | date | time | str | int | float | None) -> str:
    """[DEPRECATED] Use format_datetime.

    Mantido como wrapper temporário por compatibilidade com código legado.
    Esta função será removida em versão futura.

    Args:
        value: Data/hora como datetime, date, time, string ISO/BR, timestamp numérico, ou None.

    Returns:
        String formatada ou vazio se None/inválido.
    """
    return format_datetime(value)


APP_DATETIME_FMT_BR: Final[str] = "%d/%m/%Y - %H:%M:%S"


def _parse_any_dt(value: Any) -> datetime | None:
    """Parse various date/time formats to datetime object."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time())
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        s = value.strip()
        # Retorna None se após strip não sobrar nada
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao interpretar data/hora ISO em _parse_any_dt: %s", exc)
            for pat in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, pat)
                except Exception as inner_exc:  # noqa: BLE001
                    logger.debug("Falha ao interpretar data/hora (%s) em _parse_any_dt: %s", pat, inner_exc)
    return None


def fmt_datetime_br(value: datetime | date | time | str | int | float | None) -> str:
    """Formata data/hora no padrão brasileiro DD/MM/YYYY - HH:MM:SS.

    Args:
        value: Data/hora como datetime, date, time, string ISO/BR, timestamp numérico, ou None.

    Returns:
        String formatada no padrão brasileiro ou vazio se None/inválido/whitespace.
    """
    # Trata whitespace explicitamente como vazio
    if isinstance(value, str) and not value.strip():
        return ""

    dt: datetime | None = _parse_any_dt(value)
    if not dt:
        return "" if value in (None, "") else str(value)
    try:
        if dt.tzinfo is not None:
            dt = dt.astimezone()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao ajustar timezone em fmt_datetime_br: %s", exc)
    return dt.strftime(APP_DATETIME_FMT_BR)
