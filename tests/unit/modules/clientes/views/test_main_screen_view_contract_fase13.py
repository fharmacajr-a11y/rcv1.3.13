"""Fase 13 – Garantias headless para integração da MainScreen com o controller."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views import main_screen
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
    frame.btn_enviar = DummySendButton()
    frame.menu_enviar = DummyMenu()
    frame.btn_novo = DummyButton()
    frame.btn_lixeira = DummyButton()
    frame.btn_select = DummyButton()
    frame.btn_excluir = DummyButton()
    frame._uploading_busy = False
    frame._pick_mode = False
    return frame


@pytest.mark.skip(reason="MS-16: _build_main_screen_state foi substituído por construção direta de FilterSortInput")
def test_build_main_screen_state_collects_ui_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _make_headless_frame()
    frame._vm._clientes_raw = [_make_row("10")]
    frame._vm._build_row_from_cliente = lambda raw: raw
    frame.var_ordem.set(" Razão Social (A→Z) ")
    frame.var_status.set(" Ativos ")
    frame.var_busca.set(" Cliente X ")
    frame._get_selected_ids = lambda: {"10"}

    captured: dict[str, object] = {}

    def fake_builder(**kwargs):
        captured.update(kwargs)
        return "STATE"

    monkeypatch.setattr(main_screen, "build_main_screen_state", fake_builder)

    result = frame._build_main_screen_state()

    assert result == "STATE"
    assert captured["clients"] == frame._vm._clientes_raw
    assert captured["raw_order_label"] == " Razão Social (A→Z) "
    assert captured["raw_filter_label"] == " Ativos "
    assert captured["raw_search_text"] == " Cliente X "
    assert captured["selected_ids"] == {"10"}


@pytest.mark.skip(
    reason="MS-16: _build_main_screen_state e compute_main_screen_state foram substituídos por FilterSortManager"
)
def test_refresh_with_controller_delegates_to_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _make_headless_frame()
    sentinel_state = object()
    sentinel_computed = object()
    frame._build_main_screen_state = Mock(return_value=sentinel_state)  # type: ignore[method-assign]
    frame._update_ui_from_computed = Mock()  # type: ignore[method-assign]

    def fake_compute(state):
        assert state is sentinel_state
        return sentinel_computed

    monkeypatch.setattr(main_screen, "compute_main_screen_state", fake_compute)

    frame._refresh_with_controller()

    frame._build_main_screen_state.assert_called_once()  # type: ignore[attr-defined]
    frame._update_ui_from_computed.assert_called_once_with(sentinel_computed)  # type: ignore[attr-defined]


def test_update_ui_from_computed_updates_rows_and_helpers() -> None:
    frame = _make_headless_frame()
    frame._render_clientes = Mock()  # type: ignore[method-assign]
    frame._update_batch_buttons_from_computed = Mock()  # type: ignore[method-assign]
    frame._update_main_buttons_state = Mock()  # type: ignore[method-assign]
    visible = [_make_row("1"), _make_row("2")]
    computed = SimpleNamespace(
        visible_clients=visible,
        can_batch_delete=True,
        can_batch_restore=False,
        can_batch_export=True,
    )

    frame._update_ui_from_computed(computed)

    assert frame._current_rows == visible
    frame._render_clientes.assert_called_once_with(visible)  # type: ignore[attr-defined]
    frame._update_batch_buttons_from_computed.assert_called_once_with(computed)  # type: ignore[attr-defined]
    frame._update_main_buttons_state.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.skip(
    reason="MS-16: build_main_screen_state e compute_main_screen_state foram substituídos por FilterSortManager"
)
def test_update_batch_buttons_on_selection_change_uses_current_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _make_headless_frame()
    frame._current_rows = [_make_row("30")]
    frame.var_ordem.set(" Nome ")
    frame.var_status.set("Todos")
    frame.var_busca.set("ABC")
    frame._get_selected_ids = lambda: {"30"}

    captured_state: dict[str, object] = {}

    def fake_builder(**kwargs):
        captured_state.update(kwargs)
        return "STATE"

    computed = SimpleNamespace(
        visible_clients=[], can_batch_delete=False, can_batch_restore=False, can_batch_export=False
    )

    monkeypatch.setattr(main_screen, "build_main_screen_state", fake_builder)
    monkeypatch.setattr(main_screen, "compute_main_screen_state", lambda state: computed)
    frame._update_batch_buttons_from_computed = Mock()  # type: ignore[method-assign]

    frame._update_batch_buttons_on_selection_change()

    assert captured_state["clients"] == frame._current_rows
    frame._update_batch_buttons_from_computed.assert_called_once_with(computed)  # type: ignore[attr-defined]


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


@pytest.mark.skip(reason="MS-18: calculate_button_states foi substituído por UiStateManager.compute_button_states")
def test_update_main_buttons_state_uses_calculate_button_states(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _make_headless_frame()
    frame.client_list = SimpleNamespace(selection=lambda: ("row",))
    frame._uploading_busy = True
    frame._pick_mode = False
    frame._update_batch_buttons_on_selection_change = Mock()  # type: ignore[method-assign]

    monkeypatch.setattr(main_screen, "get_supabase_state", lambda: ("online", "Conectado"))

    captured_args: dict[str, object] = {}

    def fake_calculate(**kwargs):
        captured_args.update(kwargs)
        return {
            "editar": True,
            "subpastas": False,
            "enviar": False,
            "novo": True,
            "lixeira": False,
            "select": True,
        }

    monkeypatch.setattr(main_screen, "calculate_button_states", fake_calculate)

    frame._update_main_buttons_state()

    assert captured_args == {
        "has_selection": True,
        "is_online": True,
        "is_uploading": True,
        "is_pick_mode": False,
    }
    assert frame.btn_editar.last_state == "normal"
    assert frame.btn_subpastas.last_state == "disabled"
    assert frame.btn_enviar.state_calls[-1] == ("disabled",)
    assert frame.btn_novo.last_state == "normal"
    assert frame.btn_lixeira.last_state == "disabled"
    assert frame.btn_excluir.last_state == "normal"
    frame._update_batch_buttons_on_selection_change.assert_called_once()  # type: ignore[attr-defined]
