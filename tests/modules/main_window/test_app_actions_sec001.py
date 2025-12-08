"""Testes de regressão SEC-001 para AppActions.abrir_lixeira."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest

from src.modules.main_window.app_actions import AppActions
from src.modules.lixeira.views import lixeira as lixeira_views


def test_abrir_lixeira_calls_new_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa que abrir_lixeira usa diretamente o módulo novo."""
    dummy_app = SimpleNamespace()
    invoked: dict[str, Any] = {}

    def fake_open(app: Any) -> None:
        invoked["app"] = app

    monkeypatch.setattr(lixeira_views, "abrir_lixeira", fake_open)

    actions = AppActions(dummy_app)
    actions.abrir_lixeira()

    assert invoked["app"] is dummy_app


def test_abrir_lixeira_logs_error_on_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Testa que erros ao abrir a lixeira são logados corretamente."""
    from unittest.mock import patch

    dummy_app = SimpleNamespace()

    def fake_open_error(app: Any) -> None:
        raise RuntimeError("Erro simulado ao abrir lixeira")

    with patch("src.modules.lixeira.views.lixeira.abrir_lixeira", side_effect=fake_open_error):
        caplog.set_level(logging.ERROR, logger="src.modules.main_window.app_actions")
        actions = AppActions(dummy_app)
        actions.abrir_lixeira()

    # Deve ter logado o erro
    error_messages = [record.message for record in caplog.records]
    assert any("Erro ao abrir a tela da Lixeira" in msg for msg in error_messages)
