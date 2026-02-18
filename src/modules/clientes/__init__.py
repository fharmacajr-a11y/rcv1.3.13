"""Módulo Clientes - serviços compartilhados (service, viewmodel, export).

A UI principal está em src.modules.clientes.ui (ClientesFrame).
Domain logic está em src.modules.clientes.core.*
"""

from __future__ import annotations

# Importar diretamente de core para evitar warnings internos
from .core.service import (
    ClienteCNPJDuplicadoError,
    checar_duplicatas_para_form,
    excluir_clientes_definitivamente,
    mover_cliente_para_lixeira,
    restaurar_clientes_da_lixeira,
    salvar_cliente_a_partir_do_form,
    listar_clientes_na_lixeira,
)


# Lazy import de UI para evitar collection errors quando não há GUI
def _get_clientes_frame():
    """Lazy import de ClientesFrame para evitar problemas de collection."""
    from .ui.view import ClientesV2Frame

    return ClientesV2Frame


# Alias para compatibilidade com código legacy
class _ClientesFrameProxy:
    """Proxy para lazy loading de ClientesFrame."""

    def __new__(cls):
        return _get_clientes_frame()


ClientesFrame = _ClientesFrameProxy

__all__ = [
    "ClienteCNPJDuplicadoError",
    "checar_duplicatas_para_form",
    "mover_cliente_para_lixeira",
    "restaurar_clientes_da_lixeira",
    "excluir_clientes_definitivamente",
    "listar_clientes_na_lixeira",
    "salvar_cliente_a_partir_do_form",
    "ClientesFrame",
]
