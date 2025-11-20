"""View principal do módulo Clientes.

Por enquanto este módulo apenas reexporta a tela legada
`MainScreenFrame` como `ClientesFrame`, mantendo 100% de
compatibilidade com o código existente.

A ideia é que, no futuro, qualquer ajuste visual do módulo
Clientes seja feito aqui, sem precisar mexer em `app_gui.py`
ou no roteador.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from src.modules.clientes.views import (
    DEFAULT_ORDER_LABEL as _DEFAULT_ORDER_LABEL,
    ORDER_CHOICES as _ORDER_CHOICES,
    MainScreenFrame,
)

# Reexporta as constantes usadas pelo roteador / App
DEFAULT_ORDER_LABEL: str = _DEFAULT_ORDER_LABEL
ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = _ORDER_CHOICES


class ClientesFrame(MainScreenFrame):
    """Alias tipado para a tela principal de clientes.

    Nesta etapa não adicionamos comportamento novo; herdamos
    diretamente de `MainScreenFrame` para evitar qualquer
    mudança funcional.
    """

    # Nenhuma customização por enquanto; o __init__ da classe base
    # já aceita todos os argumentos usados hoje.
    ...
