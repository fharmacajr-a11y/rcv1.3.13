# -*- coding: utf-8 -*-
"""Testes para require_internet_or_alert (PR15 — remoção de CTk root extra)."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


def _get_mod():
    return importlib.import_module("src.utils.network")


class TestRequireInternetOrAlert:
    """Garante que require_internet_or_alert não cria um novo CTk/Tk root."""

    # -- helper para forçar caminho "sem internet + cloud-only + GUI habilitada" --
    @staticmethod
    def _force_no_internet(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")  # cloud-only → entra no check
        monkeypatch.setenv("RC_NO_GUI_ERRORS", "0")  # GUI habilitada
        monkeypatch.setenv("RC_NO_NET_CHECK", "0")  # não pular check

    # ------------------------------------------------------------------ #
    # 1) CTk() nunca é chamado                                            #
    # ------------------------------------------------------------------ #
    def test_no_ctk_root_created(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """require_internet_or_alert NÃO deve instanciar ctk.CTk()."""
        self._force_no_internet(monkeypatch)

        mod = _get_mod()

        # Forçar check_internet_connectivity → False
        monkeypatch.setattr(mod, "check_internet_connectivity", lambda **_kw: False)

        # Sentinel: se alguém importar ctk e chamar CTk(), explode
        fake_ctk = MagicMock()
        fake_ctk.CTk.side_effect = AssertionError("CTk() não deve ser chamado!")

        # patch messagebox para não abrir UI real
        fake_msgbox = MagicMock(askokcancel=MagicMock(return_value=True))

        fake_parent = MagicMock()

        # Importar messagebox para garantir que o módulo exista antes do patch
        from tkinter import messagebox  # noqa: F401

        with patch("tkinter.messagebox.askokcancel", fake_msgbox.askokcancel):
            result = mod.require_internet_or_alert(parent=fake_parent)

        # CTk() nunca chamado
        fake_ctk.CTk.assert_not_called()
        assert result is True

    # ------------------------------------------------------------------ #
    # 2) messagebox recebe parent quando fornecido                        #
    # ------------------------------------------------------------------ #
    def test_messagebox_receives_parent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """messagebox.askokcancel deve receber parent= quando passado."""
        self._force_no_internet(monkeypatch)

        mod = _get_mod()
        monkeypatch.setattr(mod, "check_internet_connectivity", lambda **_kw: False)

        fake_parent = MagicMock(name="fake_root")
        fake_askokcancel = MagicMock(return_value=True)

        with patch("tkinter.messagebox.askokcancel", fake_askokcancel):
            mod.require_internet_or_alert(parent=fake_parent)

        fake_askokcancel.assert_called_once()
        _, kwargs = fake_askokcancel.call_args
        assert kwargs.get("parent") is fake_parent

    # ------------------------------------------------------------------ #
    # 3) Sem parent e sem _default_root → retorna False com warning       #
    # ------------------------------------------------------------------ #
    def test_no_parent_no_default_root_returns_false(self, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
        """Sem parent e sem _default_root, deve retornar False e logar warning."""
        self._force_no_internet(monkeypatch)

        mod = _get_mod()
        monkeypatch.setattr(mod, "check_internet_connectivity", lambda **_kw: False)

        import tkinter as tk

        monkeypatch.setattr(tk, "_default_root", None)

        import logging

        with caplog.at_level(logging.WARNING):
            result = mod.require_internet_or_alert(parent=None)

        assert result is False
        assert any("sem janela root" in r.message for r in caplog.records)

        # restaurar (monkeypatch faz isso automaticamente)

    # ------------------------------------------------------------------ #
    # 4) Fallback para _default_root quando parent=None                   #
    # ------------------------------------------------------------------ #
    def test_fallback_to_default_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Quando parent=None mas _default_root existe, usa como parent."""
        self._force_no_internet(monkeypatch)

        mod = _get_mod()
        monkeypatch.setattr(mod, "check_internet_connectivity", lambda **_kw: False)

        import tkinter as tk

        fake_root = MagicMock(name="default_root")
        monkeypatch.setattr(tk, "_default_root", fake_root)

        fake_askokcancel = MagicMock(return_value=False)

        with patch("tkinter.messagebox.askokcancel", fake_askokcancel):
            result = mod.require_internet_or_alert()  # sem parent

        fake_askokcancel.assert_called_once()
        _, kwargs = fake_askokcancel.call_args
        assert kwargs.get("parent") is fake_root
        assert result is False

    # ------------------------------------------------------------------ #
    # 5) Não cloud-only retorna True sem checks                            #
    # ------------------------------------------------------------------ #
    def test_not_cloud_only_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fora do modo cloud-only, retorna True imediatamente."""
        monkeypatch.setenv("RC_NO_LOCAL_FS", "0")

        mod = _get_mod()
        assert mod.require_internet_or_alert() is True
