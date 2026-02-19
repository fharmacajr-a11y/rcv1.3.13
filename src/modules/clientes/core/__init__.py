"""Core compartilhado do módulo Clientes.

Contém business logic, viewmodels e serviços reutilizáveis por:
- clientes/ui/ (UI moderna)
- outros módulos (lixeira, hub, forms, etc.)

Exports públicos:
- ClienteRow: Dataclass para representação de cliente na UI
- ClientesViewModel: ViewModel principal do módulo (MVVM)
- ClientesViewModelError: Exceção base do viewmodel
"""

from __future__ import annotations

from .viewmodel import ClienteRow, ClientesViewModel, ClientesViewModelError

__all__ = [
    "ClienteRow",
    "ClientesViewModel",
    "ClientesViewModelError",
]
