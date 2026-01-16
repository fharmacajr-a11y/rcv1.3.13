# -*- coding: utf-8 -*-
"""Configuração central de CustomTkinter para todo o projeto.

Define a disponibilidade de CustomTkinter de forma centralizada,
evitando duplicação de imports e lógica de fallback em múltiplos módulos.

Política do projeto (Microfase 22):
- CustomTkinter é dependência obrigatória para UI moderna
- Testes devem usar skip se CTk não estiver disponível (CI/CD com CTk)
- ttk.Treeview e ttk.Scrollbar são mantidos (CTk não possui Treeview)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

# Detectar disponibilidade do CustomTkinter
_has_ctk = False
_ctk_module = None

try:
    import customtkinter

    _has_ctk = True
    _ctk_module = customtkinter
except ImportError:
    pass

# Constante global exportada (Final para evitar reatribuição)
HAS_CUSTOMTKINTER: Final[bool] = _has_ctk

# Módulo customtkinter (ou None se não disponível)
ctk = _ctk_module

if TYPE_CHECKING:
    import customtkinter as ctk  # Para type hints


__all__ = ["HAS_CUSTOMTKINTER", "ctk"]
