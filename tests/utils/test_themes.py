# -*- coding: utf-8 -*-
"""Testes do sistema de temas CustomTkinter (src.ui.theme_manager).

Substitui os testes legados de ttkbootstrap.
Valida que GlobalThemeManager chama corretamente:
  - customtkinter.set_appearance_mode(...)
  - customtkinter.set_default_color_theme(...)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


# ==================== Fixtures ====================


@pytest.fixture()
def _isolate_theme_manager(monkeypatch, tmp_path):
    """Isola o theme_manager para cada teste: cache limpo + arquivo temporário."""
    import src.ui.theme_manager as tm

    # Limpar cache global
    monkeypatch.setattr(tm, "_cached_mode", None)
    monkeypatch.setattr(tm, "_cached_color", None)
    # Usar arquivo temporário
    monkeypatch.setattr(tm, "CONFIG_FILE", tmp_path / "config_theme.json")
    monkeypatch.setattr(tm, "NO_FS", False)
    # Resetar estado do singleton
    monkeypatch.setattr(tm.theme_manager, "_initialized", False)
    monkeypatch.setattr(tm.theme_manager, "_master_ref", None)

    return tm


@pytest.fixture()
def tm(_isolate_theme_manager):
    """Atalho para o módulo theme_manager isolado."""
    return _isolate_theme_manager


# ==================== load / save ====================


def test_load_theme_config_returns_defaults_when_no_file(tm):
    mode, color = tm.load_theme_config()
    assert mode == "light"
    assert color == "blue"


def test_load_theme_config_reads_from_disk(tm):
    data = {"appearance_mode": "dark", "color_theme": "green"}
    tm.CONFIG_FILE.write_text(json.dumps(data), encoding="utf-8")

    mode, color = tm.load_theme_config()
    assert mode == "dark"
    assert color == "green"


def test_load_theme_config_validates_invalid_values(tm):
    data = {"appearance_mode": "cosmic", "color_theme": "rainbow"}
    tm.CONFIG_FILE.write_text(json.dumps(data), encoding="utf-8")

    mode, color = tm.load_theme_config()
    assert mode == "light"  # fallback
    assert color == "blue"  # fallback


def test_load_theme_config_no_fs_uses_cache(tm, monkeypatch):
    monkeypatch.setattr(tm, "NO_FS", True)
    monkeypatch.setattr(tm, "_cached_mode", "dark")
    monkeypatch.setattr(tm, "_cached_color", "green")

    mode, color = tm.load_theme_config()
    assert mode == "dark"
    assert color == "green"


def test_save_theme_config_persists_to_disk(tm):
    tm.save_theme_config("dark", "dark-blue")

    data = json.loads(tm.CONFIG_FILE.read_text(encoding="utf-8"))
    assert data["appearance_mode"] == "dark"
    assert data["color_theme"] == "dark-blue"


def test_save_theme_config_updates_cache(tm):
    tm.save_theme_config("dark", "green")
    assert tm._cached_mode == "dark"
    assert tm._cached_color == "green"


def test_save_theme_config_no_fs_only_cache(tm, monkeypatch):
    monkeypatch.setattr(tm, "NO_FS", True)

    tm.save_theme_config("dark", "green")

    assert tm._cached_mode == "dark"
    assert tm._cached_color == "green"
    assert not tm.CONFIG_FILE.exists()


# ==================== apply_global_theme ====================


def test_apply_global_theme_calls_ctk(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.apply_global_theme("dark", "green")

    mock_ctk.set_appearance_mode.assert_called_once_with("Dark")
    mock_ctk.set_default_color_theme.assert_called_once_with("green")


def test_apply_global_theme_noop_without_ctk(tm, monkeypatch):
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", False)
    monkeypatch.setattr(tm, "ctk", None)

    # Não deve lançar erro
    tm.apply_global_theme("dark", "blue")


# ==================== toggle_appearance_mode ====================


def test_toggle_appearance_mode_light_to_dark(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.save_theme_config("light", "blue")
    new_mode = tm.toggle_appearance_mode()

    assert new_mode == "dark"
    mock_ctk.set_appearance_mode.assert_called_with("Dark")


def test_toggle_appearance_mode_dark_to_light(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.save_theme_config("dark", "blue")
    new_mode = tm.toggle_appearance_mode()

    assert new_mode == "light"
    mock_ctk.set_appearance_mode.assert_called_with("Light")


def test_toggle_persists_new_mode(tm, monkeypatch):
    monkeypatch.setattr(tm, "ctk", MagicMock())
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.save_theme_config("light", "green")
    tm.toggle_appearance_mode()

    mode, color = tm.load_theme_config()
    assert mode == "dark"
    assert color == "green"  # color não muda


# ==================== set_color_theme ====================


def test_set_color_theme_calls_ctk(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.save_theme_config("light", "blue")
    tm.set_color_theme("dark-blue")

    mock_ctk.set_default_color_theme.assert_called_with("dark-blue")
    _, color = tm.load_theme_config()
    assert color == "dark-blue"


# ==================== GlobalThemeManager ====================


def test_manager_initialize_applies_theme(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.save_theme_config("dark", "green")
    mgr = tm.GlobalThemeManager()
    mgr.initialize()

    mock_ctk.set_appearance_mode.assert_called_with("Dark")
    mock_ctk.set_default_color_theme.assert_called_with("green")
    assert mgr._initialized is True


def test_manager_initialize_idempotent(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    mgr = tm.GlobalThemeManager()
    mgr.initialize()
    mgr.initialize()  # segunda vez

    assert mock_ctk.set_appearance_mode.call_count == 1


def test_manager_get_current_mode(tm):
    tm.save_theme_config("dark", "blue")
    assert tm.theme_manager.get_current_mode() == "dark"


def test_manager_get_effective_mode(tm):
    tm.save_theme_config("light", "blue")
    assert tm.theme_manager.get_effective_mode() == "light"


def test_manager_toggle_mode(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.save_theme_config("light", "blue")
    result = tm.theme_manager.toggle_mode()

    assert result == "dark"


def test_manager_set_mode(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.theme_manager.set_mode("dark")

    mock_ctk.set_appearance_mode.assert_called_with("Dark")
    assert tm.theme_manager.get_current_mode() == "dark"


def test_manager_set_color(tm, monkeypatch):
    mock_ctk = MagicMock()
    monkeypatch.setattr(tm, "ctk", mock_ctk)
    monkeypatch.setattr(tm, "HAS_CUSTOMTKINTER", True)

    tm.theme_manager.set_color("green")

    mock_ctk.set_default_color_theme.assert_called_with("green")
    assert tm.theme_manager.get_current_color() == "green"


def test_manager_set_master(tm):
    fake_app = MagicMock()
    tm.theme_manager.set_master(fake_app)
    assert tm.theme_manager._master_ref is fake_app
