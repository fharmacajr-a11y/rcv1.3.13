"""Serviços de negócio do módulo ANVISA.

Camada de serviço headless (sem dependências de UI) que contém lógica de negócio
extraída das views, seguindo padrão MVC.
"""

from __future__ import annotations

from .anvisa_service import AnvisaService

__all__ = ["AnvisaService"]
