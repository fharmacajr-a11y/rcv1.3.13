"""Testes headless do controller da janela principal (Fase 12)."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.modules.main_window import controller


class DummyNav:
    def __init__(self, current_value=None) -> None:
        self._current = current_value

    def current(self):
        return self._current


def test_create_frame_hub_reuses_instance_and_calls_hooks(monkeypatch):
    fake_place = Mock()
    fake_forget = Mock()
    fake_lift = Mock()
    monkeypatch.setattr(controller, "_place_or_pack", fake_place)
    monkeypatch.setattr(controller, "_forget_widget", fake_forget)
    monkeypatch.setattr(controller, "_lift_widget", fake_lift)

    fake_current = object()
    app = SimpleNamespace(
        nav=SimpleNamespace(current=lambda: fake_current),
        _content_container="container",
        _hub_screen_instance=None,
    )

    class FakeHubFrame:
        def __init__(self, master, **options):
            self.master = master
            self.options = options
            self.on_show_calls = 0

        def on_show(self):
            self.on_show_calls += 1

    monkeypatch.setattr(controller, "HubFrame", FakeHubFrame)

    frame = controller.create_frame(app, controller.HubFrame, {"foo": "bar"})
    assert isinstance(frame, FakeHubFrame)
    assert frame.options["foo"] == "bar"
    fake_place.assert_called_once_with(frame)
    fake_forget.assert_called_once_with(fake_current)
    fake_lift.assert_called_once_with(frame)
    assert frame.on_show_calls == 1
    assert app._hub_screen_instance is frame

    # Segunda chamada reutiliza a instância e evita um novo place/forget desnecessário
    app.nav = SimpleNamespace(current=lambda: frame)
    fake_forget.reset_mock()
    result = controller.create_frame(app, controller.HubFrame, None)
    assert result is frame
    fake_place.assert_called_once()
    fake_forget.assert_not_called()
    assert frame.on_show_calls == 2


def test_create_frame_regular_class_instantiates_and_packs(monkeypatch):
    forgotten = []

    def fake_forget(widget):
        forgotten.append(widget)

    monkeypatch.setattr(controller, "_forget_widget", fake_forget)

    current_widget = object()
    app = SimpleNamespace(
        nav=SimpleNamespace(current=lambda: current_widget),
        _content_container="container",
    )

    class DummyFrame:
        def __init__(self, parent, **options):
            self.parent = parent
            self.options = options
            self.pack_kwargs = None

        def pack(self, **kwargs):
            self.pack_kwargs = kwargs

    frame = controller.create_frame(app, DummyFrame, {"answer": 42})
    assert frame.parent == "container"
    assert frame.options["answer"] == 42
    assert frame.pack_kwargs == {"fill": "both", "expand": True}
    assert forgotten == [current_widget]


def test_create_frame_supports_callable_factories():
    nav = SimpleNamespace(current=lambda: None)
    app = SimpleNamespace(nav=nav, _content_container="container")

    created = []

    class Dummy:
        def __init__(self):
            self.pack_called = False

        def pack(self, **kwargs):
            self.pack_called = True

    def factory(container):
        assert container == "container"
        inst = Dummy()
        created.append(inst)
        return inst

    frame = controller.create_frame(app, factory, None)
    assert frame is created[0]
    assert frame.pack_called


def test_create_frame_returns_none_when_instantiation_fails():
    nav = SimpleNamespace(current=lambda: None)
    app = SimpleNamespace(nav=nav, _content_container="container")

    class Exploding:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    assert controller.create_frame(app, Exploding, None) is None


def test_show_main_configures_frame_and_sets_flags(monkeypatch):
    class FakeClientesFrame:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.kwargs = kwargs
            self.carregar_calls = 0

        def carregar(self):
            self.carregar_calls += 1

    clientes_module = types.SimpleNamespace(
        ClientesFrame=FakeClientesFrame,
        DEFAULT_ORDER_LABEL="ordem",
        ORDER_CHOICES=["nome", "cnpj"],
    )
    monkeypatch.setitem(sys.modules, "src.modules.clientes", clientes_module)

    captured = {}

    app = SimpleNamespace(
        _content_container="container",
        novo_cliente=lambda: None,
        editar_cliente=lambda: None,
        _excluir_cliente=lambda: None,
        enviar_para_supabase=lambda: None,
        open_client_storage_subfolders=lambda: None,
        ver_subpastas=lambda: None,
        abrir_obrigacoes_cliente=lambda: None,
        abrir_lixeira=lambda: None,
        enviar_pasta_supabase=lambda: None,
        _main_frame_ref=None,
        _main_loaded=False,
    )

    def fake_show_frame(frame_cls, **kwargs):
        captured["frame_cls"] = frame_cls
        captured["kwargs"] = kwargs
        return frame_cls(app._content_container, **kwargs)

    app.show_frame = fake_show_frame

    frame = controller._show_main(app)
    assert captured["frame_cls"] is FakeClientesFrame
    assert captured["kwargs"]["order_choices"] == ["nome", "cnpj"]
    assert captured["kwargs"]["default_order_label"] == "ordem"
    assert captured["kwargs"]["on_new"] is app.novo_cliente
    assert captured["kwargs"]["on_open_lixeira"] is app.abrir_lixeira
    assert frame.carregar_calls == 1
    assert app._main_frame_ref is frame
    assert app._main_loaded is True


def test_show_passwords_creates_and_reuses_cached_frame(monkeypatch):
    class FakePasswordsFrame:
        def __init__(self, parent, main_window):
            self.parent = parent
            self.main_window = main_window
            self.lift_calls = 0
            self.on_show_calls = 0
            self.update_calls = 0

        def lift(self):
            self.lift_calls += 1

        def on_show(self):
            self.on_show_calls += 1

        def update_idletasks(self):
            self.update_calls += 1

    passwords_module = types.SimpleNamespace(PasswordsFrame=FakePasswordsFrame)
    monkeypatch.setitem(sys.modules, "src.modules.passwords", passwords_module)

    placed = []
    forgotten = []
    monkeypatch.setattr(controller, "_place_or_pack", lambda frame: placed.append(frame))
    monkeypatch.setattr(controller, "_forget_widget", lambda frame: forgotten.append(frame))

    nav = DummyNav()
    app = SimpleNamespace(
        _content_container="container",
        nav=nav,
        _passwords_screen_instance=None,
        _update_topbar_state=Mock(),
    )

    frame = controller._show_passwords(app)
    assert frame.parent == "container"
    assert frame.main_window is app
    assert placed == [frame]
    assert forgotten == []
    assert frame.lift_calls == 1
    assert frame.on_show_calls == 1
    assert frame.update_calls == 1
    assert nav._current is frame
    app._update_topbar_state.assert_called_with(frame)

    # Força o caminho de forget ao simular um frame atual diferente
    previous = object()
    nav._current = previous
    second = controller._show_passwords(app)
    assert second is frame
    assert forgotten == [previous]
    assert frame.lift_calls == 2
    assert placed == [frame]


def test_show_hub_wires_navigation_callbacks(monkeypatch):
    nav_calls = []
    monkeypatch.setattr(
        controller,
        "navigate_to",
        lambda app, target, **kwargs: nav_calls.append((target, kwargs)),
    )

    class FakeHubFrame:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs
            self.on_show_calls = 0

        def on_show(self):
            self.on_show_calls += 1

    monkeypatch.setattr(controller, "HubFrame", FakeHubFrame)

    app = SimpleNamespace(
        _content_container="container",
        show_frame=lambda frame_cls, **kwargs: frame_cls(None, **kwargs),
        refresh_clients_count_async=Mock(),
    )

    frame = controller._show_hub(app)
    app.refresh_clients_count_async.assert_called_once()
    assert frame.on_show_calls == 1
    callbacks = frame.kwargs
    callbacks["open_clientes"]()
    callbacks["open_cashflow"]()
    callbacks["open_auditoria"]()
    callbacks["open_sites"]()
    callbacks["open_senhas"]()
    callbacks["open_anvisa"]()
    assert nav_calls[0][0] == "main"
    assert nav_calls[1][0] == "cashflow"
    assert nav_calls[3][0] == "sites"
    # Callback de placeholder passa o título
    assert nav_calls[-1] == ("placeholder", {"title": "Anvisa"})


def test_open_clients_picker_delegates_to_start_client_pick_mode(monkeypatch):
    recorded = {}

    def fake_start(app, **kwargs):
        recorded["app"] = app
        recorded.update(kwargs)

    monkeypatch.setattr(controller, "start_client_pick_mode", fake_start)
    nav_calls = []
    monkeypatch.setattr(controller, "navigate_to", lambda app, target, **kwargs: nav_calls.append(target))

    app = SimpleNamespace()
    on_pick = object()

    controller._open_clients_picker(app, on_pick)

    assert recorded["app"] is app
    assert recorded["on_client_picked"] is on_pick
    assert "cliente" in recorded["banner_text"].lower()
    assert callable(recorded["return_to"])

    recorded["return_to"]()
    assert nav_calls == ["passwords"]


def test_open_clients_picker_respects_custom_banner(monkeypatch):
    recorded = {}

    def fake_start(app, **kwargs):
        recorded.update(kwargs)

    monkeypatch.setattr(controller, "start_client_pick_mode", fake_start)

    controller._open_clients_picker(SimpleNamespace(), lambda: None, banner_text="Custom pick text")

    assert recorded["banner_text"] == "Custom pick text"


def test_open_clients_picker_warns_when_frame_missing(monkeypatch):
    monkeypatch.setattr(controller, "navigate_to", lambda *args, **kwargs: None)
    warning = Mock()
    monkeypatch.setattr(controller.messagebox, "showwarning", warning)
    controller._open_clients_picker(SimpleNamespace(_main_frame_ref=None), lambda: None)
    warning.assert_called_once()


def test_start_client_pick_mode_starts_frame_with_banner(monkeypatch):
    nav_calls = []
    monkeypatch.setattr(controller, "navigate_to", lambda app, target, **kwargs: nav_calls.append(target))

    frame = Mock()
    app = SimpleNamespace(_main_frame_ref=frame)
    on_pick = Mock()
    return_to = Mock()

    controller.start_client_pick_mode(app, on_client_picked=on_pick, banner_text="Contexto X", return_to=return_to)

    assert nav_calls == ["main"]
    frame.start_pick.assert_called_once_with(on_pick=on_pick, return_to=return_to, banner_text="Contexto X")


def test_show_placeholder_passes_back_navigation(monkeypatch):
    class FakePlaceholder:
        pass

    placeholder_module = types.SimpleNamespace(ComingSoonScreen=FakePlaceholder)
    monkeypatch.setitem(sys.modules, "src.ui.placeholders", placeholder_module)

    nav_calls = []
    monkeypatch.setattr(controller, "navigate_to", lambda app, target, **kwargs: nav_calls.append(target))

    captured = {}

    def fake_show_frame(frame_cls, **kwargs):
        captured["frame_cls"] = frame_cls
        captured["kwargs"] = kwargs
        return object()

    app = SimpleNamespace(show_frame=fake_show_frame)
    controller._show_placeholder(app, title="Teste")
    assert captured["frame_cls"] is FakePlaceholder
    assert captured["kwargs"]["title"] == "Teste"
    captured["kwargs"]["on_back"]()
    assert nav_calls == ["hub"]


def test_show_auditoria_configures_back_button(monkeypatch):
    class FakeAuditoriaFrame:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

    auditoria_module = types.SimpleNamespace(AuditoriaFrame=FakeAuditoriaFrame)
    monkeypatch.setitem(sys.modules, "src.modules.auditoria", auditoria_module)

    nav_calls = []
    monkeypatch.setattr(controller, "navigate_to", lambda app, target, **kwargs: nav_calls.append(target))

    captured = {}

    def fake_show_frame(frame_cls, **kwargs):
        captured["frame_cls"] = frame_cls
        captured["kwargs"] = kwargs
        return frame_cls(None, **kwargs)

    app = SimpleNamespace(show_frame=fake_show_frame)
    controller._show_auditoria(app)
    assert captured["frame_cls"] is FakeAuditoriaFrame
    captured["kwargs"]["go_back"]()
    assert nav_calls == ["hub"]


def test_show_cashflow_and_sites_delegate_to_show_frame(monkeypatch):
    class FakeCashflow:
        pass

    monkeypatch.setitem(sys.modules, "src.modules.cashflow", types.SimpleNamespace(CashflowFrame=FakeCashflow))

    class FakeSites:
        pass

    monkeypatch.setitem(sys.modules, "src.modules.sites", types.SimpleNamespace(SitesScreen=FakeSites))

    app = SimpleNamespace(show_frame=Mock())
    controller._show_cashflow(app)
    app.show_frame.assert_called_with(FakeCashflow, app=app)
    app.show_frame.reset_mock()
    controller._show_sites(app)
    app.show_frame.assert_called_with(FakeSites)


def test_navigate_to_dispatches_and_validates_target(monkeypatch):
    monkeypatch.setattr(controller, "_show_hub", lambda *args, **kwargs: "hub-ok")
    result = controller.navigate_to(object(), "hub", x=1)
    assert result == "hub-ok"

    with pytest.raises(ValueError):
        controller.navigate_to(object(), "unknown")


def test_show_placeholder_is_registered_in_navigate_to(monkeypatch):
    monkeypatch.setattr(controller, "_show_placeholder", lambda app, **kwargs: kwargs["title"])
    result = controller.navigate_to(object(), "placeholder", title="Next")
    assert result == "Next"


def test_tk_report_logs_exception(monkeypatch):
    fake_log = Mock()
    monkeypatch.setattr(controller, "log", fake_log)
    controller.tk_report("exc", "val", "tb")
    fake_log.exception.assert_called_once()
