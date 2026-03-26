# utils/subpastas_config.py
"""Utilitários de path para o fluxo cloud (Supabase Storage)."""

from __future__ import annotations


def join_prefix(base: str, *parts: str) -> str:
    b = base.rstrip("/")
    mid = "/".join(p.strip("/") for p in parts if p)
    combined = f"{b}/{mid}".strip("/") if mid else b.strip("/")
    return (combined + "/") if combined else ""
