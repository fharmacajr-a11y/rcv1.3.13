# utils/helpers/cloud_guardrails.py
"""
(Opcional) Guardrails que impedem operações locais quando CLOUD_ONLY=True.
"""

from __future__ import annotations

from tkinter import messagebox

from src.config.paths import CLOUD_ONLY


def check_cloud_only_block(operation_name: str = "Esta função") -> bool:
    """
    Verifica se estamos em modo Cloud-Only e bloqueia operações locais.

    Args:
        operation_name: Nome da operação para exibir na mensagem

    Returns:
        True se a operação deve ser bloqueada (Cloud-Only ativo),
        False se pode prosseguir (modo local)
    """
    if CLOUD_ONLY:
        messagebox.showinfo(
            "Atenção",
            f"{operation_name} indisponível no modo Cloud-Only.\n\nUse as funcionalidades baseadas em nuvem (Supabase) disponíveis na interface.",
        )
        return True
    return False


__all__ = ["check_cloud_only_block"]
