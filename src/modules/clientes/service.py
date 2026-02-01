"""Shim de retrocompatibilidade.

Este modulo foi movido para src.modules.clientes.core.service.
Importacoes antigas ainda funcionam por compatibilidade, mas novas
implementacoes devem usar src.modules.clientes.core.service.
"""

from __future__ import annotations

import warnings

# Aviso de deprecacao (emitido UMA vez por sessao)
warnings.warn(
    "src.modules.clientes.service foi movido para src.modules.clientes.core.service. " "Atualize seus imports.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exporta tudo do core
from .core.service import (
    ClienteCNPJDuplicadoError,
    ClienteServiceError,
    RowData,
    FormValues,
    checar_duplicatas_info,
    checar_duplicatas_para_form,
    count_clients,
    excluir_cliente_simples,
    excluir_clientes_definitivamente,
    extrair_dados_cartao_cnpj_em_pasta,
    fetch_cliente_by_id,
    get_cliente_by_id,
    listar_clientes_na_lixeira,
    mover_cliente_para_lixeira,
    restaurar_clientes_da_lixeira,
    salvar_cliente,
    salvar_cliente_a_partir_do_form,
    update_cliente_status_and_observacoes,
)

__all__ = [
    "ClienteCNPJDuplicadoError",
    "ClienteServiceError",
    "RowData",
    "FormValues",
    "checar_duplicatas_info",
    "checar_duplicatas_para_form",
    "count_clients",
    "excluir_cliente_simples",
    "excluir_clientes_definitivamente",
    "extrair_dados_cartao_cnpj_em_pasta",
    "fetch_cliente_by_id",
    "get_cliente_by_id",
    "listar_clientes_na_lixeira",
    "mover_cliente_para_lixeira",
    "restaurar_clientes_da_lixeira",
    "salvar_cliente",
    "salvar_cliente_a_partir_do_form",
    "update_cliente_status_and_observacoes",
]
