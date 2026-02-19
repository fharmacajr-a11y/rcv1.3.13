# -*- coding: utf-8 -*-
"""Configuração central de CustomTkinter para todo o projeto.

Define a disponibilidade de CustomTkinter de forma centralizada,
evitando duplicação de imports e lógica de fallback em múltiplos módulos.

Política do projeto (Microfase 22):
- CustomTkinter é dependência obrigatória para UI moderna
- Testes devem usar skip se CTk não estiver disponível (CI/CD com CTk)
- CTkTreeview (vendor) é mantido para hierarquias
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

# Detectar disponibilidade do CustomTkinter
_has_ctk = False
_ctk_module = None
_appearance_tracker = None

try:
    import customtkinter

    _has_ctk = True
    _ctk_module = customtkinter
    # Import AppearanceModeTracker for centralized export
    _appearance_tracker = customtkinter.AppearanceModeTracker
except ImportError:
    # Mock básico para testes quando CustomTkinter não disponível
    class MockCTk:
        CTkFrame = object
        CTkButton = object
        CTkLabel = object
        CTkEntry = object
        CTkTextbox = object
        CTkToplevel = object
        CTkCheckBox = object
        CTkComboBox = object
        CTkSegmentedButton = object
        CTkProgressBar = object
        CTkScrollableFrame = object

    _ctk_module = MockCTk()
    _appearance_tracker = None

# Constante global exportada (Final para evitar reatribuição)
HAS_CUSTOMTKINTER: Final[bool] = _has_ctk

# Módulo customtkinter (ou Mock se não disponível)
ctk = _ctk_module

# AppearanceModeTracker para uso centralizado
AppearanceModeTracker = _appearance_tracker

if TYPE_CHECKING:
    import customtkinter as ctk  # Para type hints


__all__ = ["HAS_CUSTOMTKINTER", "ctk", "AppearanceModeTracker"]
