# core/db_manager/__init__.py

from .db_manager import (
    delete_cliente,
    find_cliente_by_cnpj_norm,
    get_cliente,
    get_cliente_by_id,
    init_db,
    init_or_upgrade,
    insert_cliente,
    list_clientes,
    list_clientes_deletados,
    purge_clientes,
    restore_clientes,
    soft_delete_clientes,
    update_cliente,
    update_status_only,
)

__all__ = [
    "init_db",
    "init_or_upgrade",
    "list_clientes",
    "list_clientes_deletados",
    "get_cliente",
    "get_cliente_by_id",
    "insert_cliente",
    "update_cliente",
    "delete_cliente",
    "find_cliente_by_cnpj_norm",
    "soft_delete_clientes",
    "restore_clientes",
    "purge_clientes",
    "update_status_only",
]
