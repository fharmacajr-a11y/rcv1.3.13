# -*- coding: utf-8 -*-
"""Módulo UI de Clientes - Interface moderna integrada.

Este módulo contém a interface do usuário (UI) para o módulo de clientes.
Arquitetura consolidada com MVVM e separação clara UI/ViewModel/Service.
"""

from __future__ import annotations

from src.modules.clientes.ui.view import ClientesV2Frame

# Alias para compatibilidade futura
ClientesFrame = ClientesV2Frame

__all__ = ["ClientesV2Frame", "ClientesFrame"]
