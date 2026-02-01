"""Módulo Clientes - serviços compartilhados (service, viewmodel, export).

A UI principal está em src.modules.clientes.ui (ClientesFrame).
Domain logic está em src.modules.clientes.core.*
"""

from __future__ import annotations

from .service import (
    ClienteCNPJDuplicadoError,
    checar_duplicatas_para_form,
    excluir_clientes_definitivamente,
    mover_cliente_para_lixeira,
    restaurar_clientes_da_lixeira,
    salvar_cliente_a_partir_do_form,
    listar_clientes_na_lixeira,
)

__all__ = [
    "ClienteCNPJDuplicadoError",
    "checar_duplicatas_para_form",
    "mover_cliente_para_lixeira",
    "restaurar_clientes_da_lixeira",
    "excluir_clientes_definitivamente",
    "listar_clientes_na_lixeira",
    "salvar_cliente_a_partir_do_form",
]
