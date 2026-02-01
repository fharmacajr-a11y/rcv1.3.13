from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from src.modules.clientes.core.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_controller import MainScreenComputedLike
from src.modules.clientes.views.main_screen_state import MainScreenStateLike


@dataclass
class FakeMainScreenState(MainScreenStateLike):
    """Fake simples para cenarios de teste."""

    clients: Sequence[ClienteRow]
    order_label: str = "Razao Social (A->Z)"
    filter_label: str = "Todos"
    search_text: str = ""
    selected_ids: Collection[str] = ()
    is_online: bool = True
    is_trash_screen: bool = False


@dataclass
class FakeMainScreenComputed(MainScreenComputedLike):
    """Fake simples para dados computados da Main Screen."""

    visible_clients: Sequence[ClienteRow]
    can_batch_delete: bool = False
    can_batch_restore: bool = False
    can_batch_export: bool = False
    selection_count: int = 0
    has_selection: bool = False
