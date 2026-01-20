# -*- coding: utf-8 -*-
"""Guard rails para detectar múltiplas roots Tk (MICROFASE 24.1).

Este módulo fornece utilitários para prevenir e detectar a criação
de múltiplas janelas root Tk, que causam a janela "tk" indesejada.

MODO ESTRITO:
- Ativar via RC_STRICT_TK_ROOT=1
- Chama tkinter.NoDefaultRoot() para forçar erro em vez de criar root implícita
- Log de warning se detectar múltiplas toplevels

USO:
    from src.ui.tk_root_guard import enable_strict_mode, check_multiple_roots
    
    # No startup (após importar tkinter, antes de criar widgets):
    enable_strict_mode()
    
    # Durante runtime (opcional, para debug):
    check_multiple_roots(app)
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Optional

log = logging.getLogger(__name__)

_STRICT_MODE_ENABLED = False


def enable_strict_mode() -> None:
    """Ativa modo estrito: NoDefaultRoot para forçar erro ao usar root implícita.
    
    Deve ser chamado APÓS importar tkinter mas ANTES de criar qualquer widget.
    Se RC_STRICT_TK_ROOT=1, ativa automaticamente.
    
    Exemplo:
        >>> import tkinter as tk
        >>> from src.ui.tk_root_guard import enable_strict_mode
        >>> enable_strict_mode()
        >>> # Agora qualquer tentativa de usar default root vai gerar erro
    """
    global _STRICT_MODE_ENABLED
    
    if _STRICT_MODE_ENABLED:
        log.debug("Modo estrito já ativado")
        return
    
    try:
        # NoDefaultRoot() desabilita a criação automática de root
        tk.NoDefaultRoot()
        _STRICT_MODE_ENABLED = True
        log.info("Modo estrito ativado: NoDefaultRoot() chamado")
    except Exception as exc:
        log.warning("Falha ao ativar modo estrito: %s", exc)


def check_multiple_roots(root: Optional[tk.Tk] = None) -> int:
    """Verifica se há múltiplas janelas toplevel e log warning.
    
    Args:
        root: Janela principal esperada. Se None, tenta usar _default_root.
    
    Returns:
        Número de toplevels encontradas
        
    Exemplo:
        >>> from src.ui.tk_root_guard import check_multiple_roots
        >>> count = check_multiple_roots(app)
        >>> if count > 1:
        >>>     print(f"AVISO: {count} toplevels detectadas!")
    """
    if root is None:
        try:
            root = tk._default_root  # type: ignore[attr-defined]
        except Exception:
            log.debug("Não foi possível obter _default_root")
            return 0
    
    if root is None:
        log.debug("Root é None, não é possível verificar toplevels")
        return 0
    
    try:
        # Obter todas as toplevels
        toplevels = [root]
        for child in root.winfo_children():
            if isinstance(child, (tk.Toplevel, tk.Tk)):
                toplevels.append(child)
        
        count = len(toplevels)
        
        if count > 1:
            log.warning(
                "Múltiplas toplevels detectadas: %d janelas! "
                "Isso pode causar janela 'tk' indesejada.",
                count
            )
            # Log detalhes em debug
            if log.isEnabledFor(logging.DEBUG):
                for i, toplevel in enumerate(toplevels):
                    try:
                        title = toplevel.title()
                        log.debug("  Toplevel #%d: %s (class=%s)", i, title, toplevel.__class__.__name__)
                    except Exception:
                        log.debug("  Toplevel #%d: <erro ao obter título>", i)
        else:
            log.debug("Apenas 1 toplevel detectada (esperado)")
        
        return count
        
    except Exception as exc:
        log.debug("Falha ao verificar toplevels: %s", exc)
        return 0


def auto_enable_if_env() -> None:
    """Auto-habilita modo estrito se RC_STRICT_TK_ROOT=1."""
    if os.getenv("RC_STRICT_TK_ROOT") == "1":
        enable_strict_mode()


__all__ = [
    "enable_strict_mode",
    "check_multiple_roots",
    "auto_enable_if_env",
]
