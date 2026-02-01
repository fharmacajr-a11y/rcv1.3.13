# -*- coding: utf-8 -*-
"""Global Theme Manager para CustomTkinter (Microfase 24).

Este módulo gerencia o tema global da aplicação usando CustomTkinter
como sistema principal de temas, substituindo o sistema legado de
múltiplos temas CTk.

REGRAS (SSoT):
- Importar customtkinter APENAS via src/ui/ctk_config.py
- Usar apenas modos: "light" | "dark"
- Usar apenas color themes built-in: "blue" | "dark-blue" | "green"
- NÃO criar temas custom (sem JSON)
"""

from __future__ import annotations

import json
import logging
import os
import tkinter as tk
from pathlib import Path
from typing import Final, Literal, Optional

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

log = logging.getLogger(__name__)

# ==================== TIPOS ====================

ThemeMode = Literal["light", "dark"]
ColorTheme = Literal["blue", "dark-blue", "green"]

# ==================== CONSTANTES ====================

DEFAULT_MODE: Final[ThemeMode] = "light"
DEFAULT_COLOR: Final[ColorTheme] = "blue"

# Arquivo de configuração
try:
    from src.config.paths import BASE_DIR

    CONFIG_FILE = BASE_DIR / "config_theme.json"
except Exception:
    CONFIG_FILE = Path(__file__).resolve().parents[2] / "config_theme.json"

# Modo cloud-only (não tocar no disco)
NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

# ==================== CACHE ====================

_cached_mode: Optional[ThemeMode] = None
_cached_color: Optional[ColorTheme] = None


# ==================== FUNÇÕES DE CONFIGURAÇÃO ====================


def load_theme_config() -> tuple[ThemeMode, ColorTheme]:
    """Carrega configuração de tema do arquivo ou cache.

    Returns:
        Tupla (mode, color_theme)
    """
    global _cached_mode, _cached_color

    # Modo cloud-only: usar cache ou defaults
    if NO_FS:
        return (
            _cached_mode or DEFAULT_MODE,
            _cached_color or DEFAULT_COLOR,
        )

    # Tentar carregar do arquivo
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                mode = data.get("appearance_mode", DEFAULT_MODE)
                color = data.get("color_theme", DEFAULT_COLOR)

                # Validar valores
                if mode not in ("light", "dark"):
                    mode = DEFAULT_MODE
                if color not in ("blue", "dark-blue", "green"):
                    color = DEFAULT_COLOR

                # Atualizar cache
                _cached_mode = mode
                _cached_color = color

                return (mode, color)
    except Exception:
        log.exception("Falha ao carregar tema do disco")

    # Fallback: usar cache ou defaults
    return (
        _cached_mode or DEFAULT_MODE,
        _cached_color or DEFAULT_COLOR,
    )


def save_theme_config(mode: ThemeMode, color: ColorTheme) -> None:
    """Salva configuração de tema no arquivo.

    Args:
        mode: Modo de aparência ("light" ou "dark")
        color: Tema de cor ("blue", "dark-blue" ou "green")
    """
    global _cached_mode, _cached_color

    # Atualizar cache
    _cached_mode = mode
    _cached_color = color

    # Modo cloud-only: não persistir
    if NO_FS:
        return

    # Persistir no arquivo
    try:
        data = {
            "appearance_mode": mode,
            "color_theme": color,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        log.exception("Falha ao salvar tema no disco")


def apply_global_theme(mode: ThemeMode, color: ColorTheme) -> None:
    """Aplica tema global CustomTkinter.

    Args:
        mode: Modo de aparência ("light" ou "dark")
        color: Tema de cor ("blue", "dark-blue" ou "green")
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        log.debug("CustomTkinter não disponível, pulando apply_global_theme")
        return

    try:
        # Mapear para valores aceitos pelo CustomTkinter (capitalizados)
        ctk_mode_map = {"light": "Light", "dark": "Dark"}
        ctk_mode = ctk_mode_map.get(mode, "Light")

        # Aplicar appearance mode
        ctk.set_appearance_mode(ctk_mode)
        log.info(f"CustomTkinter appearance mode aplicado: {ctk_mode} (from {mode})")
    except Exception:
        log.exception("Falha ao aplicar appearance mode")

    try:
        # Aplicar color theme
        # NOTA: set_default_color_theme deve ser chamado apenas no startup
        # ou antes de criar widgets. Para mudanças em runtime, seria necessário
        # recriar os widgets.
        ctk.set_default_color_theme(color)
        log.info(f"CustomTkinter color theme aplicado: {color}")
    except Exception:
        log.exception("Falha ao aplicar color theme")

    # MICROFASE 31: Removido ttk_compat (ZERO widgets legados)


def toggle_appearance_mode() -> ThemeMode:
    """Alterna entre light e dark mode.

    Returns:
        Novo modo de aparência
    """
    current_mode, current_color = load_theme_config()

    # Ciclo: light -> dark -> light
    mode_cycle = {"light": "dark", "dark": "light"}
    new_mode: ThemeMode = mode_cycle[current_mode]

    # Salvar configuração
    save_theme_config(new_mode, current_color)

    # Aplicar apenas appearance mode (color theme não muda)
    if HAS_CUSTOMTKINTER and ctk is not None:
        try:
            ctk_mode_map = {"light": "Light", "dark": "Dark"}
            ctk.set_appearance_mode(ctk_mode_map[new_mode])
            log.info(f"Modo de aparência alternado para: {new_mode}")

            # Notificar TtkTreeviewManager explicitamente
            try:
                from src.ui.ttk_treeview_manager import get_treeview_manager

                manager = get_treeview_manager()
                manager.apply_all(ctk_mode_map[new_mode])
                log.debug(f"[GlobalThemeManager] TtkTreeviewManager notificado: {new_mode}")
            except Exception as exc:
                log.debug(f"[GlobalThemeManager] Erro ao notificar TtkTreeviewManager: {exc}")

        except Exception:
            log.exception("Falha ao alternar appearance mode")

    # MICROFASE 31: Removido ttk_compat (ZERO widgets legados)

    return new_mode


def set_color_theme(color: ColorTheme) -> None:
    """Define color theme CustomTkinter.

    IMPORTANTE: Color theme deve ser definido no startup.
    Mudanças em runtime podem não refletir em widgets já criados.

    Args:
        color: Tema de cor ("blue", "dark-blue" ou "green")
    """
    current_mode, _ = load_theme_config()
    save_theme_config(current_mode, color)

    if HAS_CUSTOMTKINTER and ctk is not None:
        try:
            ctk.set_default_color_theme(color)
            log.info(f"Color theme definido: {color}")
        except Exception:
            log.exception("Falha ao definir color theme")


# ==================== RESOLUÇÃO DE MODO EFETIVO ====================


def resolve_effective_mode(mode: ThemeMode) -> Literal["light", "dark"]:
    """Resolve o modo efetivo (light ou dark) a partir do modo configurado.

    Args:
        mode: Modo configurado ("light" ou "dark")

    Returns:
        Modo efetivo: "light" ou "dark"
    """
    return mode  # type: ignore[return-value]


# ==================== CLASSE THEMEMANAGER ====================


class GlobalThemeManager:
    """Gerenciador global de temas CustomTkinter."""

    def __init__(self) -> None:
        """Inicializa o gerenciador de temas."""
        self._initialized = False
        self._master_ref: Optional[tk.Misc] = None  # type: ignore[name-defined]

    def set_master(self, master: tk.Misc) -> None:  # type: ignore[name-defined]
        """Define a janela master para aplicar temas CTk.

        Args:
            master: Janela principal (App/ctk.CTk)
        """
        self._master_ref = master
        log.debug("Master definido no GlobalThemeManager")

        # MICROFASE 31: Removido ttk_compat (ZERO widgets legados)

    def initialize(self) -> None:
        """Inicializa o tema no startup da aplicação.

        Deve ser chamado ANTES de criar qualquer widget CustomTkinter.

        IMPORTANTE: NÃO aplica temas legados aqui - apenas CustomTkinter.
        Temas legados serão aplicados quando set_master() for chamado.
        """
        if self._initialized:
            log.debug("GlobalThemeManager já inicializado")
            return

        mode, color = load_theme_config()
        apply_global_theme(mode, color)
        self._initialized = True
        log.info(f"GlobalThemeManager inicializado (apenas CTk): mode={mode}, color={color}")

    def get_current_mode(self) -> ThemeMode:
        """Retorna o modo de aparência atual."""
        mode, _ = load_theme_config()
        return mode

    def get_effective_mode(self) -> Literal["light", "dark"]:
        """Retorna o modo efetivo ('light' ou 'dark')."""
        mode = self.get_current_mode()
        return resolve_effective_mode(mode)

    def get_current_color(self) -> ColorTheme:
        """Retorna o color theme atual."""
        _, color = load_theme_config()
        return color

    def toggle_mode(self) -> ThemeMode:
        """Alterna entre light e dark mode.

        Returns:
            Novo modo de aparência
        """
        return toggle_appearance_mode()

    def set_mode(self, mode: ThemeMode) -> None:
        """Define modo de aparência.

        Args:
            mode: "light" ou "dark"
        """
        _, color = load_theme_config()
        save_theme_config(mode, color)

        if HAS_CUSTOMTKINTER and ctk is not None:
            try:
                ctk_mode_map = {"light": "Light", "dark": "Dark"}
                ctk.set_appearance_mode(ctk_mode_map[mode])
                log.info(f"Modo de aparência definido: {mode}")

                # Notificar TtkTreeviewManager explicitamente
                try:
                    from src.ui.ttk_treeview_manager import get_treeview_manager

                    manager = get_treeview_manager()
                    manager.apply_all(ctk_mode_map[mode])
                    log.debug(f"[GlobalThemeManager] TtkTreeviewManager notificado: {mode}")
                except Exception as exc:
                    log.debug(f"[GlobalThemeManager] Erro ao notificar TtkTreeviewManager: {exc}")

            except Exception:
                log.exception("Falha ao definir appearance mode")

        # MICROFASE 31: Removido ttk_compat (ZERO widgets legados)

    def set_color(self, color: ColorTheme) -> None:
        """Define color theme.

        IMPORTANTE: Deve ser chamado no startup, antes de criar widgets.

        Args:
            color: "blue", "dark-blue" ou "green"
        """
        set_color_theme(color)


# ==================== SINGLETON ====================

# Singleton global
theme_manager = GlobalThemeManager()

__all__ = [
    "ThemeMode",
    "ColorTheme",
    "GlobalThemeManager",
    "theme_manager",
    "apply_global_theme",
    "load_theme_config",
    "save_theme_config",
    "toggle_appearance_mode",
    "set_color_theme",
    "resolve_effective_mode",
]
