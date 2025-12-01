from __future__ import annotations

import tkinter as tk
from typing import Any

import pytest

from src.modules.chatgpt.views.chatgpt_window import ChatGPTWindow
from src.modules.chatgpt.views import chatgpt_window


def _create_root_or_skip() -> tk.Tk:
    try:
        return tk.Tk()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tkinter indisponivel para testes: {exc}")


class ImmediateThread:
    def __init__(self, target: Any = None, daemon: bool | None = None, **_: Any) -> None:
        self._target = target
        self.daemon = daemon

    def start(self) -> None:
        if self._target:
            self._target()


def test_chatgpt_window_calls_send_fn_and_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _create_root_or_skip()
    try:
        calls: list[list[dict[str, str]]] = []

        def fake_send_fn(messages: list[dict[str, str]]) -> str:
            calls.append(list(messages))
            return "Oi, sou um teste."

        monkeypatch.setattr(chatgpt_window.threading, "Thread", ImmediateThread)

        win = ChatGPTWindow(root, send_fn=fake_send_fn)

        win._input_var.set("Teste")
        win._on_send_clicked()

        win.update()
        win.update_idletasks()

        assert calls
        assert calls[0][-1]["role"] == "user"
        assert calls[0][-1]["content"] == "Teste"

        history_text = win._history.get("1.0", "end")
        assert "Voce: Teste" in history_text
        assert "ChatGPT: Oi, sou um teste." in history_text
    finally:
        root.destroy()
