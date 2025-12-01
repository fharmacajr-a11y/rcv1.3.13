from __future__ import annotations

from src.core import keybindings


class DummyRoot:
    def __init__(self) -> None:
        self.bindings = {}

    def bind_all(self, sequence, func):
        self.bindings[sequence] = func


def test_bind_global_shortcuts_registers_all_keys(monkeypatch):
    root = DummyRoot()
    calls = {
        name: 0
        for name in ("quit", "refresh", "new", "edit", "delete", "upload", "lixeira", "subpastas", "hub", "find")
    }

    def make_handler(name):
        return lambda: calls.__setitem__(name, calls[name] + 1)

    handlers = {name: make_handler(name) for name in calls}

    keybindings.bind_global_shortcuts(root, handlers)

    expected_keys = {
        "<Control-q>",
        "<F5>",
        "<Control-n>",
        "<Control-e>",
        "<Delete>",
        "<Control-u>",
        "<Control-l>",
        "<Control-s>",
        "<Alt-Home>",
        "<Control-f>",
    }
    assert set(root.bindings.keys()) == expected_keys

    # Disparar cada binding para garantir que o handler correspondente é chamado
    for seq, func in root.bindings.items():
        func()

    assert all(count == 1 for count in calls.values())


def test_wrap_handles_none_and_exceptions(monkeypatch, caplog):
    caplog.set_level("WARNING")
    wrapped_none = keybindings._wrap(None)
    assert wrapped_none() == "break"

    def boom():
        raise RuntimeError("fail")

    wrapped_boom = keybindings._wrap(boom)
    assert wrapped_boom() == "break"
    assert any("Atalho falhou" in record.message for record in caplog.records)
