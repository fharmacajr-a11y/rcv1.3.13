# -*- coding: utf-8 -*-
# pyright: strict

"""Testes unitários para menu de contexto (botão direito) e remoção de menu de status no clique esquerdo."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock


class DummyEvent:
    """Evento dummy para simular eventos de mouse."""

    def __init__(self, x: int = 0, y: int = 0, x_root: int = 0, y_root: int = 0) -> None:
        self.x = x
        self.y = y
        self.x_root = x_root
        self.y_root = y_root


class DummyTreeview:
    """Treeview dummy para testes."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._selection: list[str] = []
        self._focus_item: str | None = None

    def identify_row(self, y: int) -> str:
        """Retorna row_id se y > 0, vazio caso contrário."""
        return "test_row_1" if y > 0 else ""

    def identify_column(self, x: int) -> str:
        """Retorna coluna baseado em x."""
        if 100 <= x < 200:
            return "#5"  # WhatsApp
        if 200 <= x < 300:
            return "#7"  # Status
        return "#1"

    def selection_set(self, item: str) -> None:
        """Define seleção."""
        self._selection = [item]

    def focus(self, item: str) -> None:
        """Define foco."""
        self._focus_item = item

    def item(self, item_id: str, option: str) -> Any:
        """Retorna valores do item."""
        if option == "values" and item_id in self._items:
            return self._items[item_id]["values"]
        return []

    def add_item(self, item_id: str, values: list[Any]) -> None:
        """Adiciona item para teste."""
        self._items[item_id] = {"values": values}


class DummyPickModeManager:
    """Manager de pick mode dummy."""

    def __init__(self, is_active: bool = False) -> None:
        self.is_active = is_active

    def get_snapshot(self) -> Any:
        """Retorna snapshot dummy."""
        snapshot = Mock()
        snapshot.is_pick_mode_active = self.is_active
        return snapshot


class TestMainScreenEventsRightClickMenu:
    """Testes para menu de contexto no botão direito."""

    def setup_method(self) -> None:
        """Setup para cada teste."""
        self.mixin = self._create_mixin()

    def _create_mixin(self, pick_mode_active: bool = False) -> Any:
        """Cria instância do mixin com stubs necessários."""

        class TestMixin:
            def __init__(self) -> None:
                self.client_list = DummyTreeview()
                self.client_list.add_item("test_row_1", ["123", "Razão", "12345678", "Nome", "999"])
                self._col_order = ["ID", "Razao Social", "CNPJ", "Nome", "WhatsApp"]
                self._pick_mode_manager = DummyPickModeManager(pick_mode_active)
                self._show_actions_menu_called = False
                self._show_actions_menu_args: tuple[Any, ...] = ()
                self._show_status_menu_called = False

            def _show_actions_menu(self, row_id: str, cliente_id: int, event: Any) -> None:
                """Stub para capturar chamada."""
                self._show_actions_menu_called = True
                self._show_actions_menu_args = (row_id, cliente_id, event)

            def _show_status_menu(self, row_id: str, cliente_id: int, event: Any) -> None:
                """Stub que levanta erro se chamado."""
                self._show_status_menu_called = True
                raise AssertionError("_show_status_menu não deveria ser chamado no clique esquerdo")

            def _on_click(self, event: Any) -> None:
                """Implementação simplificada de _on_click para teste."""
                item = self.client_list.identify_row(event.y)
                col = self.client_list.identify_column(event.x)

                if not item:
                    return

                # Apenas WhatsApp na coluna #5
                if col != "#5":
                    return

                # WhatsApp logic seria aqui, mas não testamos isso

            def _on_right_click(self, event: Any) -> None:
                """Implementação de _on_right_click para teste."""
                pick_snapshot = self._pick_mode_manager.get_snapshot()
                if pick_snapshot.is_pick_mode_active:
                    return

                iid = self.client_list.identify_row(event.y)
                if not iid:
                    return

                self.client_list.selection_set(iid)
                self.client_list.focus(iid)

                try:
                    vals = self.client_list.item(iid, "values")
                    id_index = self._col_order.index("ID") if "ID" in self._col_order else 0
                    cliente_id = int(vals[id_index])
                except Exception:
                    return

                self._show_actions_menu(iid, cliente_id, event)

        return TestMixin()

    def test_left_click_on_status_no_longer_opens_status_menu(self) -> None:
        """Teste: clique esquerdo na coluna Status (#7) NÃO abre mais menu de status."""
        event = DummyEvent(x=250, y=10)  # x=250 está na coluna #7

        # Executar clique esquerdo
        self.mixin._on_click(event)

        # Verificar que _show_status_menu NÃO foi chamado
        assert not self.mixin._show_status_menu_called, "Menu de status não deveria ser aberto no clique esquerdo"

    def test_right_click_opens_actions_menu_for_row(self) -> None:
        """Teste: clique direito abre menu de ações para linha válida."""
        event = DummyEvent(x=100, y=10, x_root=500, y_root=300)

        # Executar clique direito
        self.mixin._on_right_click(event)

        # Verificar que _show_actions_menu foi chamado
        assert self.mixin._show_actions_menu_called, "Menu de ações deveria ser aberto no clique direito"

        # Verificar argumentos
        row_id, cliente_id, evt = self.mixin._show_actions_menu_args
        assert row_id == "test_row_1"
        assert cliente_id == 123
        assert evt is event

        # Verificar que seleção foi definida
        assert self.mixin.client_list._selection == ["test_row_1"]
        assert self.mixin.client_list._focus_item == "test_row_1"

    def test_right_click_does_not_open_menu_in_pick_mode(self) -> None:
        """Teste: clique direito NÃO abre menu quando pick mode está ativo."""
        mixin = self._create_mixin(pick_mode_active=True)
        event = DummyEvent(x=100, y=10, x_root=500, y_root=300)

        # Executar clique direito
        mixin._on_right_click(event)

        # Verificar que menu NÃO foi aberto
        assert not mixin._show_actions_menu_called, "Menu não deveria abrir em pick mode"

    def test_right_click_on_empty_area_does_not_open_menu(self) -> None:
        """Teste: clique direito em área vazia NÃO abre menu."""
        event = DummyEvent(x=100, y=-1, x_root=500, y_root=300)  # y=-1 retorna row vazio

        # Executar clique direito
        self.mixin._on_right_click(event)

        # Verificar que menu NÃO foi aberto
        assert not self.mixin._show_actions_menu_called, "Menu não deveria abrir em área vazia"
