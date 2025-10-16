# core/db_manager/__init__.py

from .db_manager import (
    init_db, init_or_upgrade,
    list_clientes, list_clientes_deletados,
    get_cliente, get_cliente_by_id,
    insert_cliente, update_cliente, delete_cliente,
    soft_delete_clientes, restore_clientes, purge_clientes,
)

__all__ = [
    "init_db", "init_or_upgrade",
    "list_clientes", "list_clientes_deletados",
    "get_cliente", "get_cliente_by_id",
    "insert_cliente", "update_cliente", "delete_cliente",
    "soft_delete_clientes", "restore_clientes", "purge_clientes",
]
