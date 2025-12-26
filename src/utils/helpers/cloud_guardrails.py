# utils/helpers/cloud_guardrails.py
"""Guardrails opcionais que impedem operações locais quando CLOUD_ONLY=True."""

from __future__ import annotations

from tkinter import messagebox

from src.config.paths import CLOUD_ONLY


def check_cloud_only_block(operation_name: str = "Esta função") -> bool:
    """Bloqueia operações locais quando CLOUD_ONLY está ativo, exibindo alerta ao usuário."""
    if CLOUD_ONLY:
        messagebox.showinfo(
            "Atenção",
            (
                f"{operation_name} indisponível no modo Cloud-Only.\n\n"
                "Use as funcionalidades baseadas em nuvem (Supabase) disponíveis na interface."
            ),
        )
        return True
    return False


__all__ = ["check_cloud_only_block"]
