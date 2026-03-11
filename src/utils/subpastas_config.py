# utils/subpastas_config.py
"""Configuração de subpastas obrigatórias para o fluxo cloud (Supabase Storage)."""

from __future__ import annotations

MANDATORY_SUBPASTAS = ("SIFAP", "ANVISA", "FARMACIA_POPULAR", "AUDITORIA")


def get_mandatory_subpastas() -> tuple[str, ...]:
    """Return tuple of mandatory subfolder names."""
    return tuple(MANDATORY_SUBPASTAS)


def join_prefix(base: str, *parts: str) -> str:
    b = base.rstrip("/")
    mid = "/".join(p.strip("/") for p in parts if p)
    combined = f"{b}/{mid}".strip("/") if mid else b.strip("/")
    return (combined + "/") if combined else ""
