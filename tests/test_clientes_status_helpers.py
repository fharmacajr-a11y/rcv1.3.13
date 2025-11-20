from __future__ import annotations

import importlib

import pytest

from src.modules.clientes.components import helpers as status_helpers


@pytest.fixture
def reloaded_helpers(monkeypatch):
    """Reload helpers after clearing env vars so defaults are tested."""
    monkeypatch.delenv("RC_STATUS_CHOICES", raising=False)
    monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)
    module = importlib.reload(status_helpers)
    try:
        yield module
    finally:
        importlib.reload(status_helpers)


def test_status_choices_default_contains_novo_cliente(reloaded_helpers):
    assert reloaded_helpers.STATUS_CHOICES, "STATUS_CHOICES should not be empty"
    assert "Novo cliente" in reloaded_helpers.STATUS_CHOICES
    assert "Análise da Caixa" in reloaded_helpers.STATUS_CHOICES
    assert "Follow-up amanhã" in reloaded_helpers.STATUS_CHOICES


def test_status_prefix_regex_strips_prefix(reloaded_helpers):
    text = "[Aguardando documento] restante do texto"
    stripped = reloaded_helpers.STATUS_PREFIX_RE.sub("", text, count=1).strip()
    assert stripped == "restante do texto"
