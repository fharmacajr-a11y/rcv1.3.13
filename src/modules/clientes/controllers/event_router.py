# -*- coding: utf-8 -*-
# pyright: strict

"""Event Router - Decisoes headless para eventos da MainScreen (MS-22).

Este modulo centraliza regras de roteamento de eventos (duplo clique,
tecla Delete, etc.) sem dependencias de Tkinter. A MainScreenFrame deve
apenas coletar o contexto atual (selecao, estado do pick mode) e despachar
as acoes retornadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot
from src.modules.clientes.controllers.selection_manager import SelectionSnapshot

EventAction = Literal["noop", "open_editor", "confirm_pick", "delete_selection"]


@dataclass(frozen=True)
class EventContext:
    """Snapshot simples com informacoes necessarias para roteamento."""

    selection: SelectionSnapshot
    pick_mode: PickModeSnapshot | None = None


@dataclass(frozen=True)
class EventRoutingResult:
    """Resultado do roteamento, indicando a acao de alto nivel a executar."""

    action: EventAction


class EventRouter:
    """Coordena decisoes de eventos da MainScreen sem tocar em UI/Tkinter."""

    @staticmethod
    def _is_pick_mode_active(ctx: EventContext) -> bool:
        snapshot = ctx.pick_mode
        return bool(snapshot is not None and snapshot.is_pick_mode_active)

    def route_double_click(self, ctx: EventContext) -> EventRoutingResult:
        """Decide acao para duplo clique na lista de clientes."""
        if self._is_pick_mode_active(ctx):
            return EventRoutingResult(action="confirm_pick")
        return EventRoutingResult(action="open_editor")

    def route_delete_key(self, ctx: EventContext) -> EventRoutingResult:
        """Decide acao para a tecla Delete na lista principal."""
        if self._is_pick_mode_active(ctx):
            return EventRoutingResult(action="noop")
        return EventRoutingResult(action="delete_selection")
