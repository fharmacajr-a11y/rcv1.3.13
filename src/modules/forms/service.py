"""Service fino para o módulo Forms/Cadastros.

Este arquivo expõe uma API estável para operações de cadastro,
a partir de serviços legados em `src.core.services`.
"""

from __future__ import annotations

from src.core.services import clientes_service

salvar_cliente = clientes_service.salvar_cliente
checar_duplicatas_info = clientes_service.checar_duplicatas_info

__all__ = [
    "salvar_cliente",
    "checar_duplicatas_info",
]
