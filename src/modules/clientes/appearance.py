from __future__ import annotations

from src.ui.ctk_config import ctk

# -*- coding: utf-8 -*-
"""Theme Manager isolado do módulo Clientes.

Gerencia modo Light/Dark usando CustomTkinter como controlador,
sem afetar outros módulos do app.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Final, Literal, Optional, Union

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

log = logging.getLogger(__name__)

AppearanceMode = Literal["light", "dark"]

# Paletas de cores
LIGHT_PALETTE = {
    "bg": "#FAFAFA",  # Fundo geral levemente cinza (não branco puro)
    "fg": "#1C1C1C",
    "entry_bg": "#F5F5F5",
    "entry_fg": "#1C1C1C",
    "entry_border": "#D0D0D0",
    "combo_bg": "#FFFFFF",
    "combo_fg": "#1C1C1C",
    "combo_border": "#D0D0D0",
    "tree_bg": "#FFFFFF",
    "tree_fg": "#1C1C1C",
    "tree_field_bg": "#FFFFFF",
    "tree_selected_bg": "#0078D7",
    "tree_selected_fg": "#FFFFFF",
    "tree_heading_bg": "#E0E0E0",
    "tree_heading_fg": "#1C1C1C",
    "tree_heading_bg_active": "#C8C8C8",  # Hover no heading (mais escuro)
    "tree_even_row": "#FFFFFF",
    "tree_odd_row": "#E8E8E8",  # Zebra visível
    "accent": "#0078D7",
    "button_bg": "#F0F0F0",
    "button_fg": "#1C1C1C",
    # Cores específicas da toolbar CustomTkinter
    "toolbar_bg": "#F5F5F5",
    "input_bg": "#FFFFFF",
    "input_border": "#C8C8C8",
    "input_text": "#1C1C1C",
    "input_placeholder": "#999999",
    "dropdown_bg": "#DCDCDC",  # Mais escuro para melhor contraste
    "dropdown_hover": "#C0C0C0",  # Mais escuro no hover
    "dropdown_text": "#1C1C1C",
    "accent_hover": "#0056B3",
    "danger": "#F44336",
    "danger_hover": "#D32F2F",
    "neutral_btn": "#DCDCDC",  # Mais escuro
    "neutral_hover": "#BEBEBE",  # Mais escuro
    "control_bg": "#DCDCDC",  # Nova: cor de fundo para controles no claro
    "control_hover": "#C0C0C0",  # Nova: hover para controles
}

DARK_PALETTE = {
    "bg": "#1E1E1E",  # Fundo geral escuro
    "fg": "#DCE4EE",  # Texto claro mais suave
    "entry_bg": "#2D2D2D",
    "entry_fg": "#DCE4EE",
    "entry_border": "#404040",
    "combo_bg": "#2D2D2D",
    "combo_fg": "#DCE4EE",
    "combo_border": "#404040",
    "tree_bg": "#1E1E1E",
    "tree_fg": "#DCE4EE",
    "tree_field_bg": "#252525",
    "tree_selected_bg": "#0078D7",
    "tree_selected_fg": "#FFFFFF",
    "tree_heading_bg": "#2D2D30",
    "tree_heading_fg": "#DCE4EE",
    "tree_heading_bg_active": "#3E3E42",  # Hover no heading (mais claro)
    "tree_even_row": "#252525",
    "tree_odd_row": "#303030",  # Zebra visível
    "accent": "#0078D7",
    "button_bg": "#2D2D2D",
    "button_fg": "#DCE4EE",
    # Cores específicas da toolbar CustomTkinter
    "toolbar_bg": "#252525",  # Mesmo tom do bg geral
    "input_bg": "#333333",
    "input_border": "#505050",
    "input_text": "#DCE4EE",
    "input_placeholder": "#808080",
    "dropdown_bg": "#3D3D3D",
    "dropdown_hover": "#4A4A4A",
    "dropdown_text": "#DCE4EE",
    "accent_hover": "#005A9E",
    "danger": "#D32F2F",
    "danger_hover": "#B71C1C",
    "neutral_btn": "#3D3D3D",
    "neutral_hover": "#2D2D2D",
    "control_bg": "#3D3D3D",  # Nova: cor de fundo para controles no escuro
    "control_hover": "#4A4A4A",  # Nova: hover para controles
}


def _get_prefs_path() -> str:
    """Retorna caminho do arquivo de preferências de aparência."""
    # Windows
    appdata = os.getenv("APPDATA")
    if appdata and os.path.isdir(appdata):
        base = os.path.join(appdata, "RegularizeConsultoria")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "clientes_appearance.json")
    # Unix-like
    home = os.path.expanduser("~")
    base = os.path.join(home, ".regularizeconsultoria")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "clientes_appearance.json")


class ClientesThemeManager:
    """Gerenciador de tema (Light/Dark) do módulo Clientes."""

    def __init__(self) -> None:
        self._current_mode: AppearanceMode = "light"
        self._prefs_path = _get_prefs_path()

    def load_mode(self) -> AppearanceMode:
        """Carrega modo salvo do disco."""
        try:
            if os.path.exists(self._prefs_path):
                with open(self._prefs_path, encoding="utf-8") as f:
                    data = json.load(f)
                    mode = data.get("mode", "light")
                    if mode in ("light", "dark"):
                        self._current_mode = mode
                        log.debug(f"Modo carregado: {mode}")
                        return self._current_mode
        except Exception:
            log.exception("Erro ao carregar preferências de aparência")
        return self._current_mode

    def save_mode(self, mode: AppearanceMode) -> None:
        """Salva modo no disco."""
        try:
            with open(self._prefs_path, "w", encoding="utf-8") as f:
                json.dump({"mode": mode}, f, indent=2)
            self._current_mode = mode
            log.debug(f"Modo salvo: {mode}")
        except Exception:
            log.exception("Erro ao salvar preferências de aparência")

    def get_palette(self, mode: Optional[AppearanceMode] = None) -> dict[str, str]:
        """Retorna paleta de cores para o modo especificado."""
        if mode is None:
            mode = self._current_mode
        return DARK_PALETTE if mode == "dark" else LIGHT_PALETTE

    def apply(self, mode: AppearanceMode, style: Any = None) -> None:
        """Aplica o modo especificado aos estilos do módulo Clientes.

        Args:
            mode: "light" ou "dark"
            style: Instância de estilo para configurar (opcional, legado)
        """
        self._current_mode = mode

        # NÃO configurar CustomTkinter diretamente (viola SSoT)
        # O GlobalThemeManager já gerencia o tema global
        # Este método apenas salva preferência LOCAL do módulo

        # Obtém paleta
        palette = self.get_palette(mode)

        # Configura estilos legados específicos do módulo Clientes
        if style is not None:
            try:
                # Style da Treeview de clientes
                style.configure(
                    "Clientes.Treeview",
                    background=palette["tree_field_bg"],
                    fieldbackground=palette["tree_field_bg"],
                    foreground=palette["tree_fg"],
                    borderwidth=0,
                    relief="flat",
                )
                style.map(
                    "Clientes.Treeview",
                    background=[("selected", palette["tree_selected_bg"])],
                    foreground=[("selected", palette["tree_selected_fg"])],
                )

                # Style dos headings
                style.configure(
                    "Clientes.Treeview.Heading",
                    background=palette["tree_heading_bg"],
                    foreground=palette["tree_heading_fg"],
                    relief="flat",
                    borderwidth=1,
                    padding=(8, 6),  # Padding uniforme: horizontal=8px, vertical=6px
                )
                style.map(
                    "Clientes.Treeview.Heading",
                    background=[("active", palette["tree_heading_bg"])],
                )

                # Style do Entry de busca
                style.configure(
                    "Search.TEntry",
                    fieldbackground=palette["entry_bg"],
                    foreground=palette["entry_fg"],
                    bordercolor=palette["entry_border"],
                    lightcolor=palette["entry_border"],
                    darkcolor=palette["entry_border"],
                    insertcolor=palette["entry_fg"],
                )

                # Style do Combobox de filtro
                style.configure(
                    "Filtro.TCombobox",
                    fieldbackground=palette["combo_bg"],
                    foreground=palette["combo_fg"],
                    bordercolor=palette["combo_border"],
                    arrowcolor=palette["combo_fg"],
                    insertcolor=palette["combo_fg"],
                )
                style.map(
                    "Filtro.TCombobox",
                    fieldbackground=[("readonly", palette["combo_bg"])],
                    foreground=[("readonly", palette["combo_fg"])],
                    bordercolor=[("readonly", palette["combo_border"])],
                )

                log.debug(f"Estilos aplicados para modo {mode}")
            except Exception:
                log.exception("Erro ao aplicar estilos legados")

    def toggle(self, style: Any = None) -> AppearanceMode:
        """Alterna entre Light e Dark."""
        new_mode: AppearanceMode = "dark" if self._current_mode == "light" else "light"
        self.apply(new_mode, style)
        self.save_mode(new_mode)
        log.info(f"Tema alternado para: {new_mode}")
        return new_mode

    @property
    def current_mode(self) -> AppearanceMode:
        """Retorna o modo atual."""
        return self._current_mode


__all__ = ["ClientesThemeManager", "AppearanceMode", "HAS_CUSTOMTKINTER"]
