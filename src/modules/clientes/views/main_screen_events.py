# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false, reportUntypedBaseClass=false, reportPrivateUsage=false

"""Main screen events - Handlers de eventos da main screen.

Responsável por handlers de eventos da main screen (treeview, toolbar, status).
"""

from __future__ import annotations

import logging
import tkinter as tk
import urllib.parse
import webbrowser
from typing import TYPE_CHECKING, Any

from src.modules.clientes.components.helpers import _build_status_menu
from src.modules.clientes.controllers.event_router import EventContext
from src.modules.clientes.controllers.selection_manager import SelectionSnapshot
from src.modules.clientes.views.main_screen_helpers import normalize_order_label
from src.utils.phone_utils import normalize_br_whatsapp

if TYPE_CHECKING:
    pass

log = logging.getLogger("app_gui")

__all__ = ["MainScreenEventsMixin"]


class MainScreenEventsMixin:
    """Mixin para handlers de eventos da main screen."""

    def _rebind_double_click_handler(self) -> None:
        """Garante que o duplo clique sempre passa pelo EventRouter (MS-22)."""
        try:
            self.client_list.bind("<Double-1>", self._on_double_click)  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao reconfigurar bind de duplo clique: %s", exc)

    def _on_double_click(self, _event: Any) -> None:
        """Roteia duplo clique para editar ou confirmar seleção."""
        router = getattr(self, "_event_router", None)
        if router is None:
            self._invoke_safe(getattr(self, "on_edit", None))  # pyright: ignore[reportAttributeAccessIssue]
            return

        try:
            ctx = self._build_event_context()  # pyright: ignore[reportAttributeAccessIssue]
            result = router.route_double_click(ctx)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao rotear duplo clique: %s", exc)
            self._invoke_safe(getattr(self, "on_edit", None))  # pyright: ignore[reportAttributeAccessIssue]
            return

        if result.action == "open_editor":
            self._invoke_safe(getattr(self, "on_edit", None))  # pyright: ignore[reportAttributeAccessIssue]
        elif result.action == "confirm_pick":
            pick_controller = getattr(self, "_pick_controller", None)
            if pick_controller is not None:
                try:
                    pick_controller.confirm_pick()
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao confirmar pick via duplo clique: %s", exc)

    def _on_click(self, event: Any) -> None:
        """Abre WhatsApp na col #5 e menu de Status na col #7."""

        item = self.client_list.identify_row(event.y)  # pyright: ignore[reportAttributeAccessIssue]

        col = self.client_list.identify_column(event.x)  # pyright: ignore[reportAttributeAccessIssue]

        if not item:
            return

        # Menu de Status ao clicar na coluna #7

        if col == "#7":
            try:
                vals = self.client_list.item(item, "values")  # pyright: ignore[reportAttributeAccessIssue]

                id_index = self._col_order.index("ID") if "ID" in self._col_order else 0  # pyright: ignore[reportAttributeAccessIssue]

                cliente_id = int(vals[id_index])

            except Exception:
                return

            self._show_status_menu(item, cliente_id, event)  # pyright: ignore[reportAttributeAccessIssue]

            return

        # WhatsApp permanece na coluna #5

        if col != "#5":
            return

        try:
            cell = self.client_list.item(item, "values")[4] or ""  # pyright: ignore[reportAttributeAccessIssue]

        except Exception:
            cell = ""

        # Usa normalize_br_whatsapp para obter formato e164

        wa = normalize_br_whatsapp(str(cell))

        if not wa["e164"]:
            return

        msg = "Olá, tudo bem?"

        webbrowser.open_new_tab(f"https://wa.me/{wa['e164']}?text={urllib.parse.quote(msg)}")

    def _on_tree_delete_key(self, _event: Any = None) -> None:
        """Handler da tecla Delete na lista principal."""
        router = getattr(self, "_event_router", None)
        if router is None or not hasattr(self, "_build_event_context"):
            if hasattr(self, "on_delete_selected_clients"):
                self.on_delete_selected_clients()  # pyright: ignore[reportAttributeAccessIssue]
            return

        try:
            result = router.route_delete_key(self._build_event_context())  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao rotear tecla Delete: %s", exc)
            if hasattr(self, "on_delete_selected_clients"):
                self.on_delete_selected_clients()  # pyright: ignore[reportAttributeAccessIssue]
            return

        if result.action == "delete_selection" and hasattr(self, "on_delete_selected_clients"):
            self.on_delete_selected_clients()  # pyright: ignore[reportAttributeAccessIssue]

    def _on_order_changed(self, _value: Any | None = None) -> None:
        """Dispara recarga apenas quando a ordenação efetivamente muda."""
        new_value = normalize_order_label(self.var_ordem.get())  # pyright: ignore[reportAttributeAccessIssue]
        if new_value == getattr(self, "_current_order_by", None):
            return
        self._current_order_by = new_value  # pyright: ignore[reportAttributeAccessIssue]
        self.var_ordem.set(new_value)  # pyright: ignore[reportAttributeAccessIssue]
        self.carregar()  # pyright: ignore[reportAttributeAccessIssue]

    def _on_status_menu(self, event: Any) -> None:
        tv = getattr(self, "tree", self.client_list)  # pyright: ignore[reportAttributeAccessIssue]

        row_id = tv.identify_row(event.y)

        if not row_id:
            return

        tv.selection_set(row_id)

        tv.focus(row_id)

        try:
            values = tv.item(row_id, "values")

            idx = self._col_order.index("ID") if "ID" in self._col_order else 0  # pyright: ignore[reportAttributeAccessIssue]

            cliente_id = int(values[idx])

        except Exception:
            return

        self._show_status_menu(row_id, cliente_id, event)  # pyright: ignore[reportAttributeAccessIssue]

    def _on_status_pick(self, label: str) -> None:
        self._set_status(label)  # pyright: ignore[reportAttributeAccessIssue]

    def _set_status(self, label: str) -> None:
        target_id = self._status_menu_cliente  # pyright: ignore[reportAttributeAccessIssue]

        if target_id is None:
            try:
                selection = self.client_list.selection()  # pyright: ignore[reportAttributeAccessIssue]

                if not selection:
                    self._status_menu_cliente = None  # pyright: ignore[reportAttributeAccessIssue]

                    self._status_menu_row = None  # pyright: ignore[reportAttributeAccessIssue]

                    return

                values = self.client_list.item(selection[0], "values")  # pyright: ignore[reportAttributeAccessIssue]

                idx = self._col_order.index("ID") if "ID" in self._col_order else 0  # pyright: ignore[reportAttributeAccessIssue]

                target_id = int(values[idx])

            except Exception:
                self._status_menu_cliente = None  # pyright: ignore[reportAttributeAccessIssue]

                self._status_menu_row = None  # pyright: ignore[reportAttributeAccessIssue]

                return

        try:
            self._apply_status_for(int(target_id), label)  # pyright: ignore[reportAttributeAccessIssue]

        finally:
            self._status_menu_cliente = None  # pyright: ignore[reportAttributeAccessIssue]

            self._status_menu_row = None  # pyright: ignore[reportAttributeAccessIssue]

    def _build_selection_snapshot(self) -> SelectionSnapshot:
        """Constrói um snapshot da seleção atual via SelectionManager.

        Returns:
            SelectionSnapshot com IDs selecionados e todos os clientes.
        """
        try:
            tree_ids = self.client_list.selection()  # pyright: ignore[reportAttributeAccessIssue]
        except Exception:
            tree_ids = ()

        return self._selection_manager.build_snapshot(tree_ids)  # pyright: ignore[reportAttributeAccessIssue]

    def _get_selected_ids(self) -> set[str]:
        """Retorna o conjunto de IDs de clientes atualmente selecionados.

        Returns:
            Set de IDs (strings) dos itens selecionados. Set vazio se nenhuma seleção.
        """
        snapshot = self._build_selection_snapshot()
        return self._selection_manager.get_selected_ids_as_set(snapshot)  # pyright: ignore[reportAttributeAccessIssue]

    def _build_event_context(self) -> EventContext:
        """Monta o contexto necessário para o roteamento de eventos."""
        selection_snapshot = self._build_selection_snapshot()
        pick_snapshot = self._pick_mode_manager.get_snapshot()  # pyright: ignore[reportAttributeAccessIssue]
        return EventContext(selection=selection_snapshot, pick_mode=pick_snapshot)

    def _ensure_status_menu(self) -> tk.Menu:
        menu = self.status_menu  # pyright: ignore[reportAttributeAccessIssue]

        if menu is None:
            menu = tk.Menu(self, tearoff=0)  # pyright: ignore[reportArgumentType]

            self.status_menu = menu  # pyright: ignore[reportAttributeAccessIssue]

        menu.configure(postcommand=lambda: _build_status_menu(menu, self._on_status_pick))

        return menu

    def _show_status_menu(self, row_id: str, cliente_id: int, event: Any) -> None:
        menu = self._ensure_status_menu()

        self.client_list.selection_set(row_id)  # pyright: ignore[reportAttributeAccessIssue]

        self.client_list.focus(row_id)  # pyright: ignore[reportAttributeAccessIssue]

        self._status_menu_row = row_id  # pyright: ignore[reportAttributeAccessIssue]

        self._status_menu_cliente = cliente_id  # pyright: ignore[reportAttributeAccessIssue]

        try:
            menu.tk_popup(event.x_root, event.y_root)

        finally:
            menu.grab_release()

            if self._status_menu_row == row_id:  # pyright: ignore[reportAttributeAccessIssue]
                self._status_menu_row = None  # pyright: ignore[reportAttributeAccessIssue]

            if self._status_menu_cliente == cliente_id:  # pyright: ignore[reportAttributeAccessIssue]
                self._status_menu_cliente = None  # pyright: ignore[reportAttributeAccessIssue]
