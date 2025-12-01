from __future__ import annotations

from src.ui.topbar import TopBar


def test_chatgpt_button_calls_callback(tk_root_session):
    called = []

    def fake_open_chatgpt():
        called.append(True)

    bar = TopBar(tk_root_session, on_chatgpt=fake_open_chatgpt)

    bar._handle_chatgpt()

    assert called == [True]
    try:
        bar.destroy()
    except Exception:
        pass
