from __future__ import annotations

from src.ui.topbar import TopBar


def test_sites_button_calls_callback(tk_root_session):
    called = []

    def fake_open_sites():
        called.append(True)

    bar = TopBar(tk_root_session, on_sites=fake_open_sites)

    bar._handle_sites()

    assert called == [True]
    try:
        bar.destroy()
    except Exception:
        pass
