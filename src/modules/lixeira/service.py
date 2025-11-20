"""Service fino para o módulo Lixeira.

Este arquivo expõe uma API estável para operações de Lixeira,
a partir do código legado em `src.core.services.lixeira_service`.
"""

from __future__ import annotations

from src.core.services import lixeira_service

# Reexports finos – mantêm a assinatura original
restore_clients = lixeira_service.restore_clients
hard_delete_clients = lixeira_service.hard_delete_clients

__all__ = [
    "restore_clients",
    "hard_delete_clients",
]
