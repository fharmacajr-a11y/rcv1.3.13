# core/db_manager/__init__.py
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.db_manager import db_manager as db_manager

from .db_manager import (
    DEFAULT_PAGE_LIMIT,
    delete_cliente,
    find_cliente_by_cnpj_norm,
    get_cliente,
    get_cliente_by_id,
    init_db,
    init_or_upgrade,
    insert_cliente,
    list_clientes,
    list_clientes_by_org,
    list_clientes_deletados,
    purge_clientes,
    restore_clientes,
    soft_delete_clientes,
    update_cliente,
    update_status_only,
)

__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "db_manager",
    "init_db",
    "init_or_upgrade",
    "list_clientes",
    "list_clientes_by_org",
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


def __getattr__(name: str):
    """Lazy import de submodules para evitar circular imports."""
    if name == "db_manager":
        return importlib.import_module("src.core.db_manager.db_manager")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
