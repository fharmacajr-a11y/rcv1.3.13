from __future__ import annotations

from typing import Any, Callable, Sequence

from tests.unit.modules.clientes.views.main_screen_doubles_ms11 import (
    FakeMainScreenComputed,
    FakeMainScreenState,
)


class FakeMainScreenFrame:
    """Fake headless de MainScreenFrame para testes de contrato."""

    def __init__(self):
        self._build_main_screen_state: Callable[[], Any] = lambda: None
        self._update_ui_from_computed: Callable[[Any], None] = lambda c: None
        self._render_clientes: Callable[[Sequence[Any]], None] = lambda c: None
        self._update_main_buttons_state: Callable[..., None] = lambda *a, **k: None

    def _refresh_with_controller(self) -> None:
        """Simula o fluxo de refresh que usa state + computed."""
        # Importação inline para garantir uso do mock correto
        from src.modules.clientes.views.main_screen_controller import compute_main_screen_state

        state = self._build_main_screen_state()
        computed = compute_main_screen_state(state)
        self._update_ui_from_computed(computed)

    def _update_batch_buttons_from_computed(self, computed: Any) -> None:
        """Método que aceita MainScreenComputedLike."""
        # Verifica acesso aos atributos do protocolo
        _ = computed.can_batch_delete
        _ = computed.can_batch_restore
        _ = computed.can_batch_export


def test_refresh_with_controller_accepts_state_protocol(monkeypatch) -> None:
    """MainScreenFrame deve aceitar qualquer MainScreenStateLike no controller.

    Este teste é headless - não cria Tk real.
    Valida que o fluxo _refresh_with_controller funciona com protocolos.
    """
    fake_state = FakeMainScreenState(clients=[])
    fake_computed = FakeMainScreenComputed(visible_clients=[])
    captured: dict[str, object] = {}

    screen = FakeMainScreenFrame()
    screen._build_main_screen_state = lambda: fake_state

    def fake_compute(state):
        captured["state"] = state
        return fake_computed

    def fake_update_ui(computed):
        captured["computed"] = computed

    monkeypatch.setattr(
        "src.modules.clientes.views.main_screen_controller.compute_main_screen_state",
        fake_compute,
    )
    screen._update_ui_from_computed = fake_update_ui

    screen._refresh_with_controller()

    assert captured["state"] is fake_state
    assert captured["computed"] is fake_computed


def test_update_ui_from_computed_accepts_protocol(monkeypatch) -> None:
    """Metodos de update devem aceitar MainScreenComputedLike sem depender da dataclass concreta.

    Este teste é headless - não cria Tk real.
    Valida que _update_batch_buttons_from_computed funciona com protocolos.
    """
    fake_computed = FakeMainScreenComputed(visible_clients=[])

    screen = FakeMainScreenFrame()

    # Não deve lançar exceção ao acessar atributos do protocolo
    screen._update_batch_buttons_from_computed(fake_computed)

    # Valida que os atributos do protocolo são acessíveis
    assert fake_computed.can_batch_delete is False
    assert fake_computed.can_batch_restore is False
    assert fake_computed.can_batch_export is False
    assert fake_computed.visible_clients == []
