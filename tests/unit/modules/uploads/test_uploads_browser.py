from __future__ import annotations

from typing import Callable

import pytest

from src.modules.uploads.views import browser


@pytest.fixture
def make_window(
    monkeypatch: pytest.MonkeyPatch, tk_root_session: object
) -> Callable[..., browser.UploadsBrowserWindow]:
    """
    Cria UploadsBrowserWindow sem carregar estado inicial (evita chamadas de rede nos testes).
    """

    monkeypatch.setattr(browser.UploadsBrowserWindow, "_populate_initial_state", lambda self: None)
    monkeypatch.setattr(browser, "show_centered", lambda *args, **kwargs: None)

    def _factory(**kwargs):
        win = browser.UploadsBrowserWindow(
            tk_root_session,
            client_id=1,
            razao="Acme Corp",
            cnpj="12345678000199",
            bucket="bucket-test",
            base_prefix="org/1",
            **kwargs,
        )
        return win

    yield _factory
