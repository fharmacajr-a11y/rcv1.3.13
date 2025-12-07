"""MainScreen - Tela principal de gestão de clientes."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Any

# Constantes para ordenação
DEFAULT_ORDER_LABEL = "ID"
ORDER_CHOICES = [
    ("ID", "id"),
    ("Nome", "nome"),
    ("Razão Social", "razao"),
]


@dataclass
class MainScreenState:
    """Estado da tela principal.

    Attributes:
        is_online: Indica se o aplicativo está online
        order_by: Campo de ordenação atual
        order_direction: Direção da ordenação (ASC/DESC)
    """

    is_online: bool = False
    order_by: str = "id"
    order_direction: str = "ASC"


def build_main_screen_state(
    order_by: str = "id",
    order_direction: str = "ASC",
    is_online: bool = False,
) -> MainScreenState:
    """Constrói o estado da tela principal.

    Args:
        order_by: Campo para ordenação (padrão: "id")
        order_direction: Direção da ordenação (padrão: "ASC")
        is_online: Status de conectividade (padrão: False)

    Returns:
        MainScreenState: Objeto de estado configurado
    """
    return MainScreenState(
        is_online=is_online,
        order_by=order_by,
        order_direction=order_direction,
    )


class MainScreenFrame(tk.Frame):
    """Frame principal da tela de clientes."""

    def __init__(self, parent: tk.Widget, is_online: bool = False, order_by: str = "id", order_direction: str = "ASC", **kwargs: Any) -> None:
        """Inicializa o frame principal.

        Args:
            parent: Widget pai
            is_online: Status de conectividade (padrão: False)
            order_by: Campo para ordenação (padrão: "id")
            order_direction: Direção da ordenação (padrão: "ASC")
            **kwargs: Argumentos adicionais para o Frame
        """
        super().__init__(parent, **kwargs)
        self.state = build_main_screen_state(
            order_by=order_by,
            order_direction=order_direction,
            is_online=is_online,
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do usuário."""
        # TODO: Implementar UI completa
        label = tk.Label(self, text="Tela de Clientes")
        label.pack(pady=20)

    def update_state(
        self,
        is_online: bool | None = None,
        order_by: str | None = None,
        order_direction: str | None = None,
    ) -> None:
        """Atualiza o estado.

        Args:
            is_online: Novo status de conectividade (opcional)
            order_by: Novo campo de ordenação (opcional)
            order_direction: Nova direção de ordenação (opcional)
        """
        self.state = build_main_screen_state(
            order_by=order_by if order_by is not None else self.state.order_by,
            order_direction=order_direction if order_direction is not None else self.state.order_direction,
            is_online=is_online if is_online is not None else self.state.is_online,
        )
