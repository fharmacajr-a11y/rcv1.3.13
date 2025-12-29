"""Teste de regressão para show_notification_toast (Winotify).

Garante que o toast não quebra quando winotify está presente.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def test_show_notification_toast_does_not_crash_when_winotify_is_present() -> None:
    """Testa que show_notification_toast não quebra quando winotify está presente."""
    # Criar um módulo fake winotify (para não depender do Windows/notificação real)
    fake = types.ModuleType("winotify")

    class DummyNotification:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def set_audio(self, *args: object, **kwargs: object) -> None:
            pass

        def show(self) -> None:
            pass

    fake.Notification = DummyNotification
    fake.audio = types.SimpleNamespace(Default=object())

    # Injetar no sys.modules
    old = sys.modules.get("winotify")
    sys.modules["winotify"] = fake
    try:
        from src.modules.main_window.views.main_window_handlers import show_notification_toast

        show_notification_toast(MagicMock(), 1)
    finally:
        # Restaurar estado do sys.modules
        if old is not None:
            sys.modules["winotify"] = old
        else:
            sys.modules.pop("winotify", None)
