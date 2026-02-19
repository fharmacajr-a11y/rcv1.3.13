"""Service fino para o módulo Fluxo de Caixa.

Este arquivo expõe uma API estável para operações de fluxo de caixa,
a partir do código legado em `src.features.cashflow.repository`.
"""

from __future__ import annotations

from src.features.cashflow import repository

# Reexports finos – mantêm a assinatura original do repositório legado
list_entries = repository.list_entries
totals = repository.totals
create_entry = repository.create_entry
update_entry = repository.update_entry
delete_entry = repository.delete_entry

__all__ = [
    "list_entries",
    "totals",
    "create_entry",
    "update_entry",
    "delete_entry",
]
