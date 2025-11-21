from __future__ import annotations

import re
from datetime import datetime, date, time
from typing import Any, Final

APP_DATETIME_FMT: Final[str] = "%Y-%m-%d %H:%M:%S"


def format_cnpj(raw: str | int | float | None) -> str:
    """Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX.

    Args:
        raw: CNPJ como string, int, float ou None. Aceita com ou sem formatação.

    Returns:
        CNPJ formatado se válido (14 dígitos), caso contrário retorna original ou vazio.
    """
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) != 14:
        return str(raw)
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"


def fmt_datetime(value: datetime | date | str | int | float | None) -> str:
    """Formata data/hora no padrão YYYY-MM-DD HH:MM:SS.

    Args:
        value: Data/hora como datetime, date, string ISO/BR, timestamp numérico, ou None.

    Returns:
        String formatada ou vazio se None/inválido.
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
        except Exception:
            for pat in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s, pat)
                    break
                except Exception:
                    pass
    if dt is None:
        return str(value)
    try:
        if dt.tzinfo is not None:
            dt = dt.astimezone()
    except Exception:
        pass
    return dt.strftime(APP_DATETIME_FMT)


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
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            for pat in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, pat)
                except Exception:
                    pass
    return None


def fmt_datetime_br(value: datetime | date | str | int | float | None) -> str:
    """Formata data/hora no padrão brasileiro DD/MM/YYYY - HH:MM:SS.

    Args:
        value: Data/hora como datetime, date, string ISO/BR, timestamp numérico, ou None.

    Returns:
        String formatada no padrão brasileiro ou vazio se None/inválido.
    """
    dt: datetime | None = _parse_any_dt(value)
    if not dt:
        return "" if value in (None, "") else str(value)
    try:
        if dt.tzinfo is not None:
            dt = dt.astimezone()
    except Exception:
        pass
    return dt.strftime(APP_DATETIME_FMT_BR)
