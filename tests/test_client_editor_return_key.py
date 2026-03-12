# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes para _on_return_key do EditorActionsMixin.

Garante que:
  - Enter em qualquer CTkTextbox retorna "break" SEM chamar _on_save_clicked.
  - Enter fora de textbox chama _on_save_clicked e retorna "break".

Estratégia: extrair _on_return_key via AST (sem importar Tk/CTk).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from conftest import extract_functions_from_source

# ---------------------------------------------------------------------------
# Localização do arquivo-fonte
# ---------------------------------------------------------------------------

_SRC_FILE = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "modules"
    / "clientes"
    / "ui"
    / "views"
    / "_editor_actions_mixin.py"
)

_fns = extract_functions_from_source(
    _SRC_FILE,
    "_on_return_key",
    class_name="EditorActionsMixin",
    extra_namespace={"log": logging.getLogger("test_return_key")},
)
_on_return_key = _fns["_on_return_key"]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

STATE_NO_SHIFT = 0x0000  # nenhum modificador


@dataclass
class _FakeTextbox:
    """Simula um CTkTextbox com ._textbox interno (tk.Text)."""

    _textbox: MagicMock = field(default_factory=MagicMock)

    def insert(self, index: str, text: str) -> None:
        self._textbox.insert(index, text)


def _make_event(state: int = STATE_NO_SHIFT) -> MagicMock:
    ev = MagicMock()
    ev.state = state
    return ev


def _make_self(focused_widget: Any) -> MagicMock:
    """Cria um mock de EditorDialogProto com os atributos necessários."""
    obs = _FakeTextbox()
    contatos = _FakeTextbox()
    bloco = _FakeTextbox()

    self_mock = MagicMock()
    self_mock.obs_text = obs
    self_mock.contatos_text = contatos
    self_mock.bloco_notas_text = bloco
    self_mock.focus_get.return_value = focused_widget
    return self_mock


# ---------------------------------------------------------------------------
# 1. Enter simples em CTkTextbox → não salva
# ---------------------------------------------------------------------------


class TestEnterOnTextboxDoesNotSave:
    """Enter simples dentro de qualquer textbox deve impedir o save."""

    def test_enter_on_obs_text_wrapper_no_save(self) -> None:
        """Enter com foco no obs_text (widget wrapper) → não salva."""
        self_mock = _make_self(focused_widget=None)  # ajustado abaixo
        obs = self_mock.obs_text
        self_mock.focus_get.return_value = obs

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        assert result == "break"
        self_mock._on_save_clicked.assert_not_called()

    def test_enter_on_obs_internal_textbox_no_save(self) -> None:
        """Enter com foco no obs_text._textbox (tk.Text interno) → não salva."""
        self_mock = _make_self(focused_widget=None)
        obs_internal = self_mock.obs_text._textbox
        self_mock.focus_get.return_value = obs_internal

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        assert result == "break"
        self_mock._on_save_clicked.assert_not_called()

    def test_enter_on_contatos_text_no_save(self) -> None:
        """Enter com foco em contatos_text → não salva."""
        self_mock = _make_self(focused_widget=None)
        self_mock.focus_get.return_value = self_mock.contatos_text

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        assert result == "break"
        self_mock._on_save_clicked.assert_not_called()

    def test_enter_on_contatos_internal_no_save(self) -> None:
        """Enter com foco em contatos_text._textbox → não salva."""
        self_mock = _make_self(focused_widget=None)
        self_mock.focus_get.return_value = self_mock.contatos_text._textbox

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        assert result == "break"
        self_mock._on_save_clicked.assert_not_called()

    def test_enter_on_bloco_notas_no_save(self) -> None:
        """Enter com foco em bloco_notas_text → não salva."""
        self_mock = _make_self(focused_widget=None)
        self_mock.focus_get.return_value = self_mock.bloco_notas_text

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        assert result == "break"
        self_mock._on_save_clicked.assert_not_called()

    def test_enter_on_bloco_notas_internal_no_save(self) -> None:
        """Enter com foco em bloco_notas_text._textbox → não salva."""
        self_mock = _make_self(focused_widget=None)
        self_mock.focus_get.return_value = self_mock.bloco_notas_text._textbox

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        assert result == "break"
        self_mock._on_save_clicked.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Enter simples em CTkTextbox → NÃO insere \n manualmente
# ---------------------------------------------------------------------------


class TestEnterOnTextboxNoManualNewline:
    """Enter simples não deve inserir \\n manualmente (o tk.Text já fez isso)."""

    def test_enter_on_obs_does_not_insert_newline(self) -> None:
        self_mock = _make_self(focused_widget=None)
        obs_internal = self_mock.obs_text._textbox
        self_mock.focus_get.return_value = obs_internal

        _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        obs_internal.insert.assert_not_called()

    def test_enter_on_contatos_does_not_insert_newline(self) -> None:
        self_mock = _make_self(focused_widget=None)
        contatos_internal = self_mock.contatos_text._textbox
        self_mock.focus_get.return_value = contatos_internal

        _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        contatos_internal.insert.assert_not_called()

    def test_enter_on_bloco_does_not_insert_newline(self) -> None:
        self_mock = _make_self(focused_widget=None)
        bloco_internal = self_mock.bloco_notas_text._textbox
        self_mock.focus_get.return_value = bloco_internal

        _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        bloco_internal.insert.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Enter/KP_Enter fora de textbox → salva
# ---------------------------------------------------------------------------


class TestEnterOutsideTextboxSaves:
    """Enter/KP_Enter com foco fora de textbox deve chamar _on_save_clicked."""

    def test_enter_on_entry_widget_saves(self) -> None:
        """Enter em CTkEntry → salva."""
        entry_widget = MagicMock()
        self_mock = _make_self(focused_widget=entry_widget)

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        self_mock._on_save_clicked.assert_called_once()
        assert result == "break"

    def test_enter_with_no_focus_saves(self) -> None:
        """Enter sem foco (focus_get retorna None) → salva."""
        self_mock = _make_self(focused_widget=None)

        result = _on_return_key(self_mock, _make_event(STATE_NO_SHIFT))

        self_mock._on_save_clicked.assert_called_once()
        assert result == "break"


# ---------------------------------------------------------------------------
# 4. Retorno sempre é "break"
# ---------------------------------------------------------------------------


class TestAlwaysReturnsBreak:
    """_on_return_key deve SEMPRE retornar 'break' para bloquear propagação."""

    def test_returns_break_on_obs(self) -> None:
        self_mock = _make_self(focused_widget=None)
        self_mock.focus_get.return_value = self_mock.obs_text
        assert _on_return_key(self_mock, _make_event()) == "break"

    def test_returns_break_on_entry(self) -> None:
        entry = MagicMock()
        self_mock = _make_self(focused_widget=entry)
        assert _on_return_key(self_mock, _make_event()) == "break"
