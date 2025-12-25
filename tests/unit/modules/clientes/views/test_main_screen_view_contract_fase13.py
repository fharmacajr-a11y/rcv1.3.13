"""Fase 13 – Garantias headless para integração da MainScreen com o controller."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen import MainScreenFrame


class DummyVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class DummyButton:
    def __init__(self) -> None:
        self.last_state: str | None = None
        self.configure_calls: list[dict[str, str]] = []

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(kwargs)
        state = kwargs.get("state")
        if state is not None:
            self.last_state = state

    def state(self, ops: list[str]) -> None:
        self.configure(state=ops[-1] if ops else "")


class DummySendButton(DummyButton):
    def __init__(self) -> None:
        super().__init__()
        self.state_calls: list[tuple[str, ...]] = []

    def state(self, ops: list[str]) -> None:
        self.state_calls.append(tuple(ops))


class DummyMenu:
    def __init__(self, last_index: int = 1) -> None:
        self._last_index = last_index
        self.entry_calls: list[tuple[int, str]] = []

    def index(self, which: str) -> int:
        return self._last_index

    def entryconfigure(self, idx: int, state: str) -> None:
        self.entry_calls.append((idx, state))


def _make_row(row_id: str = "1") -> ClienteRow:
    return ClienteRow(
        id=row_id,
        razao_social=f"Cliente {row_id}",
        cnpj="00.000.000/0000-00",
        nome=f"Contato {row_id}",
        whatsapp="55999999999",
        observacoes="",
        status="Ativo",
        ultima_alteracao="2024-01-01T10:00:00",
    )


def _make_headless_frame() -> MainScreenFrame:
    from src.modules.clientes.controllers.filter_sort_manager import FilterSortManager
    from src.modules.clientes.controllers.selection_manager import SelectionManager
    from src.modules.clientes.controllers.ui_state_manager import UiStateManager

    frame = object.__new__(MainScreenFrame)
    frame.var_ordem = DummyVar("Razão Social (A→Z)")
    frame.var_status = DummyVar("Todos")
    frame.var_busca = DummyVar("")
    frame._current_order_by = frame.var_ordem.get()
    frame._buscar_after = None
    sample_row = _make_row()
    frame._vm = SimpleNamespace(
        _clientes_raw=[sample_row],
        _build_row_from_cliente=lambda raw: raw if isinstance(raw, ClienteRow) else sample_row,
        refresh_from_service=Mock(),
        get_status_choices=Mock(return_value=["Todos"]),
    )
    # MS-24: Inicializar managers headless necessários
    frame._filter_sort_manager = FilterSortManager()
    frame._selection_manager = SelectionManager(all_clients=[])
    frame._ui_state_manager = UiStateManager()
    frame._get_selected_ids = lambda: set()
    frame._get_clients_for_controller = lambda: frame._vm._clientes_raw
    frame._current_rows = []
    frame.client_list = SimpleNamespace(selection=lambda: ())
    frame.btn_batch_delete = DummyButton()
    frame.btn_batch_restore = DummyButton()
    frame.btn_batch_export = DummyButton()
    frame.btn_editar = DummyButton()
    frame.btn_subpastas = DummyButton()
    frame.btn_novo = DummyButton()
    frame.btn_lixeira = DummyButton()
    frame.btn_select = DummyButton()
    frame.btn_excluir = DummyButton()
    frame._uploading_busy = False
    frame._pick_mode = False
    return frame


def test_carregar_refreshes_vm_and_uses_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _make_headless_frame()
    frame._populate_status_filter_options = Mock()  # type: ignore[method-assign]
    frame._refresh_with_controller = Mock()  # type: ignore[method-assign]
    frame._vm.refresh_from_service = Mock()

    frame.carregar()

    frame._vm.refresh_from_service.assert_called_once()
    frame._populate_status_filter_options.assert_called_once()  # type: ignore[attr-defined]
    frame._refresh_with_controller.assert_called_once()  # type: ignore[attr-defined]


def test_apply_filters_triggers_controller_refresh() -> None:
    frame = _make_headless_frame()
    frame._refresh_with_controller = Mock()  # type: ignore[method-assign]

    frame.apply_filters()

    frame._refresh_with_controller.assert_called_once()  # type: ignore[attr-defined]
