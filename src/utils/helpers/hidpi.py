# utils/helpers/hidpi.py
"""
Configuração de suporte HiDPI para monitores de alta resolução.

Baseado na documentação oficial do ttkbootstrap:
https://ttkbootstrap.readthedocs.io/en/latest/api/utility/enable_high_dpi_awareness/
"""

from __future__ import annotations

import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk


def configure_hidpi_support(root: tk.Tk | None = None, scaling: float | None = None) -> None:
    """
    Configura suporte HiDPI para monitores de alta resolução (4K, etc).

    Args:
        root: Instância do Tk (obrigatório no Linux, None no Windows antes de criar Tk)
        scaling: Fator de escala manual (recomendado: 1.6-2.0 para 4K).
                 Se None, usa detecção automática do ttkbootstrap.

    Notas:
        - Windows: Chamar ANTES de criar o Tk(), sem parâmetros
        - Linux: Chamar DEPOIS de criar o Tk(), com root e scaling
        - macOS: Suporte nativo, não requer configuração manual
    """
    try:
        from ttkbootstrap.utility import enable_high_dpi_awareness
    except ImportError:
        # ttkbootstrap não disponível ou versão antiga
        return

    system = platform.system()

    if system == "Windows":
        # Windows: chamar sem parâmetros ANTES de criar Tk
        if root is None:
            try:
                enable_high_dpi_awareness()
            except Exception:
                pass  # Silencioso se já foi configurado
        # Se root foi passado no Windows, ignora (já tarde demais)

    elif system == "Linux":
        # Linux: chamar DEPOIS de criar Tk, com root e scaling
        if root is not None:
            try:
                # Scaling recomendado: 1.6-2.0 para monitores 4K
                # Referência: https://ttkbootstrap.readthedocs.io/en/latest/api/utility/enable_high_dpi_awareness/
                scale_factor = scaling or _detect_linux_scaling(root)
                enable_high_dpi_awareness(root, scale_factor)  # pyright: ignore[reportCallIssue]
            except Exception:
                pass  # Silencioso se falhar

    # macOS tem suporte nativo HiDPI, não requer configuração


def _detect_linux_scaling(root: tk.Tk) -> float:
    """
    Detecta o fator de escala apropriado para Linux baseado na resolução.

    Args:
        root: Instância do Tk para obter informações de tela

    Returns:
        Fator de escala (1.0 = 96 DPI, 1.5 = 144 DPI, 2.0 = 192 DPI)
    """
    try:
        # Obtém DPI da tela
        dpi = root.winfo_fpixels("1i")  # pixels por polegada

        # Calcula fator de escala baseado em DPI padrão (96)
        # 96 DPI = 1.0, 144 DPI = 1.5, 192 DPI = 2.0
        scale = dpi / 96.0

        # Limita entre 1.0 e 3.0
        scale = max(1.0, min(3.0, scale))

        # Arredonda para 0.1
        scale = round(scale, 1)

        return scale
    except Exception:
        # Fallback para 1.0 (sem escala)
        return 1.0


__all__ = ["configure_hidpi_support"]
