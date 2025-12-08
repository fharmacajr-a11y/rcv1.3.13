from __future__ import annotations

import pytest

from tests.helpers.tk_skip import require_tk


@pytest.fixture
def tk_root():
    """Cria um root Tk minimalista para testes de widgets reais."""
    require_tk("Tkinter indisponível para testes headless de PDF")
    import tkinter as tk

    try:
        root = tk.Tk()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tkinter indisponível: {exc}")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass
