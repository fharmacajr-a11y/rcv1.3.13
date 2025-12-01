"""Helper para skip consistente de testes que dependem de Tkinter funcional."""

from __future__ import annotations

import pytest


def require_tk(reason: str = "Tkinter não está disponível para testes") -> None:
    """
    Verifica se Tkinter está disponível e funcional.

    Se Tkinter não puder ser usado (TclError, access violation, etc.),
    marca o teste como SKIPPED com uma mensagem clara.

    Args:
        reason: Mensagem customizada para o skip (opcional)

    Raises:
        pytest.skip.Exception: Se Tkinter não estiver disponível

    Usage:
        def test_my_gui_feature():
            require_tk("Tkinter indisponível para testes de GUI")
            # restante do teste...
    """
    try:
        import tkinter as tk

        # Tenta criar e destruir um Tk para validar ambiente
        root = tk.Tk()
        root.withdraw()  # Oculta janela antes de destruir
        root.destroy()
    except Exception as exc:  # noqa: BLE001
        # Qualquer erro (TclError, OSError, access violation, etc.)
        pytest.skip(f"{reason}: {exc}")


__all__ = ["require_tk"]
