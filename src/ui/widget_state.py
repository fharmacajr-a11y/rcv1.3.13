"""Helper para gerenciar estados de widgets de forma compatível entre CTk e TTK.

Resolve diferenças entre:
- CTk widgets: usam .configure(state="normal"/"disabled") 
- TTK widgets: usam .state(["!disabled"]/["disabled"])
- TK widgets: usam widget["state"] = "normal"/"disabled"
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def set_enabled(widget: Any, enabled: bool, *, readonly: bool = False) -> None:
    """Define o estado de um widget de forma compatível entre CTk, TTK e TK.
    
    Args:
        widget: Widget a ser configurado
        enabled: Se True, widget fica habilitado; se False, desabilitado
        readonly: Se True e enabled=True, widget fica readonly (somente TTK)
    """
    try:
        # Determinar estado target
        if not enabled:
            target_state = "disabled"
        elif readonly:
            target_state = "readonly"  # Só TTK suporta
        else:
            target_state = "normal"
            
        # Tentar método .configure() primeiro (CTk e TK)
        try:
            widget.configure(state=target_state)
            return
        except (AttributeError, TypeError):
            pass
            
        # Tentar método .state() do TTK
        try:
            if hasattr(widget, 'state') and callable(widget.state):
                if not enabled:
                    widget.state(["disabled"])
                elif readonly:
                    widget.state(["!disabled", "readonly"])
                else:
                    widget.state(["!disabled", "!readonly"])
                return
        except (AttributeError, TypeError):
            pass
            
        # Fallback: acesso direto via dict (TK antigo)
        try:
            widget["state"] = target_state
            return
        except (KeyError, TypeError):
            pass
            
        # Se tudo falhar, log debug
        logger.debug(f"Não foi possível definir state para widget {type(widget)}")
        
    except Exception as e:
        logger.debug(f"Erro ao definir state do widget {type(widget)}: {e}")


def set_disabled(widget: Any) -> None:
    """Desabilita um widget (atalho para set_enabled(widget, False))."""
    set_enabled(widget, False)


def set_normal(widget: Any) -> None:
    """Habilita um widget (atalho para set_enabled(widget, True))."""
    set_enabled(widget, True)


def set_readonly(widget: Any) -> None:
    """Define widget como readonly (atalho para set_enabled(widget, True, readonly=True))."""
    set_enabled(widget, True, readonly=True)