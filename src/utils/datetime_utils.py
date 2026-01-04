"""Utilitários para manipulação de data/hora."""

from __future__ import annotations

import datetime


def now_iso_z() -> str:
    """Retorna a data/hora atual em formato ISO 8601 com sufixo 'Z' (UTC).

    Formato retornado: YYYY-MM-DDTHH:MM:SSZ
    Exemplo: 2025-11-19T14:30:45Z

    Returns:
        String ISO 8601 UTC sem microsegundos, terminando em 'Z'.
    """
    dt = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    iso = dt.isoformat(timespec="seconds")
    # Normaliza para o formato aceito pelo Postgres/Supabase (sem "+00:00Z")
    return iso.replace("+00:00", "Z")
