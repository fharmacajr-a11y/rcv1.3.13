from __future__ import annotations

from src.ui.ctk_config import ctk

# -*- coding: utf-8 -*-
"""Toolbar customizada com widgets CustomTkinter para o módulo Clientes.

Esta toolbar usa CustomTkinter para uma aparência moderna e suporte
nativo a temas Light/Dark.
"""

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Callable, Iterable, Optional

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

if TYPE_CHECKING:
    from src.modules.clientes.appearance import ClientesThemeManager

log = logging.getLogger(__name__)

__all__ = ["ClientesToolbarCtk", "HAS_CUSTOMTKINTER"]


class ClientesToolbarCtk(ctk.CTkFrame if HAS_CUSTOMTKINTER else tk.Frame):  # type: ignore[misc]
    """Toolbar moderna com CustomTkinter para busca, filtros e ações."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        order_choices: Iterable[str],
        default_order: str,
        status_choices: Iterable[str],
        on_search_changed: Callable[[str], None],
        on_clear_search: Callable[[], None],
        on_order_changed: Callable[[str], None],
        on_status_changed: Callable[[Optional[str]], None],
        on_open_trash: Optional[Callable[[], None]] = None,
        theme_manager: Optional[ClientesThemeManager] = None,
    ) -> None:
        """Inicializa toolbar com widgets CustomTkinter.

        Args:
            master: Widget pai
            order_choices: Opções de ordenação
            default_order: Ordenação padrão
            status_choices: Opções de status
            on_search_changed: Callback quando texto de busca muda
            on_clear_search: Callback para limpar busca
            on_order_changed: Callback quando ordenação muda
            on_status_changed: Callback quando status muda
            on_open_trash: Callback para abrir lixeira
            theme_manager: Gerenciador de tema (para cores dinâmicas)
        """
        super().__init__(master)

        self._theme_manager = theme_manager
        self._on_search_changed = on_search_changed
        self._on_clear_search = on_clear_search
        self._on_order_changed = on_order_changed
        self._on_status_changed = on_status_changed
        self._on_open_trash = on_open_trash

        # Variáveis Tkinter (compatíveis com código legado)
        self.var_busca = tk.StringVar(master=self)
        self.var_ordem = tk.StringVar(master=self, value=default_order)
        self.var_status = tk.StringVar(master=self, value="Todos")

        # Obtém cores do tema
        palette = theme_manager.get_palette() if theme_manager else self._get_default_palette()

        # Configura cores por tupla (light, dark) para CustomTkinter
        toolbar_bg = (palette.get("toolbar_bg", "#F5F5F5"), palette.get("toolbar_bg", "#2A2A2A"))
        text_color = (palette.get("input_text", "#000000"), palette.get("input_text", "#E0E0E0"))
        input_bg = (palette.get("input_bg", "#FFFFFF"), palette.get("input_bg", "#333333"))
        input_border = (palette.get("input_border", "#C8C8C8"), palette.get("input_border", "#505050"))
        input_placeholder = (palette.get("input_placeholder", "#999999"), palette.get("input_placeholder", "#808080"))
        dropdown_bg = (palette.get("dropdown_bg", "#E8E8E8"), palette.get("dropdown_bg", "#3D3D3D"))
        dropdown_hover = (palette.get("dropdown_hover", "#D0D0D0"), palette.get("dropdown_hover", "#4A4A4A"))
        button_accent = (palette.get("accent", "#0078D7"), palette.get("accent", "#0078D7"))
        button_accent_hover = (palette.get("accent_hover", "#0056B3"), palette.get("accent_hover", "#005A9E"))
        button_neutral = (palette.get("neutral_btn", "#E0E0E0"), palette.get("neutral_btn", "#3D3D3D"))
        button_neutral_hover = (palette.get("neutral_hover", "#C0C0C0"), palette.get("neutral_hover", "#2D2D2D"))
        button_danger = (palette.get("danger", "#F44336"), palette.get("danger", "#D32F2F"))
        button_danger_hover = (palette.get("danger_hover", "#D32F2F"), palette.get("danger_hover", "#B71C1C"))

        if not HAS_CUSTOMTKINTER:
            # Fallback para tk.Frame se CustomTkinter não disponível
            log.warning("CustomTkinter não disponível, usando toolbar legada")
            self._build_fallback_toolbar(order_choices, default_order, status_choices)
            return

        # Container principal
        self.configure(fg_color=toolbar_bg, corner_radius=0)

        # Label "Pesquisar"
        label_search = ctk.CTkLabel(  # type: ignore[union-attr]
            self,
            text="Pesquisar:",
            text_color=text_color,
            font=("Segoe UI", 11),
        )
        label_search.pack(side="left", padx=(10, 5), pady=10)

        # Constante para corner_radius consistente (Fix Microfase 19.2)
        SEARCH_CORNER_RADIUS = 6

        # Wrapper CTkFrame com borda (solução robusta contra borda dupla)
        search_wrapper = ctk.CTkFrame(  # type: ignore[union-attr]
            self,
            fg_color=toolbar_bg,
            border_width=1,
            border_color=input_border,
            corner_radius=SEARCH_CORNER_RADIUS,
        )
        search_wrapper.pack(side="left", padx=5, pady=10)

        # Entry de busca SEM borda (wrapper faz papel de borda)
        self.entry_busca = ctk.CTkEntry(  # type: ignore[union-attr]
            search_wrapper,
            textvariable=self.var_busca,
            width=300,
            height=32,
            fg_color=input_bg,
            bg_color=toolbar_bg,  # Casado com wrapper para cantos arredondados
            text_color=text_color,
            border_width=0,  # ZERO: wrapper tem borda
            corner_radius=SEARCH_CORNER_RADIUS,  # Mesmo valor do wrapper
            placeholder_text_color=input_placeholder,
            placeholder_text="Digite para pesquisar...",
        )
        # Padding interno ZERO para entry (wrapper controla tamanho)
        self.entry_busca.pack(padx=1, pady=1, fill="both", expand=True)
        self.entry_busca.bind("<Return>", lambda e: self._trigger_search())
        self.entry_busca.bind("<KeyRelease>", lambda e: self._trigger_search())

        # Botão Buscar
        btn_search = ctk.CTkButton(  # type: ignore[union-attr]
            self,
            text="🔍 Buscar",
            width=100,
            height=32,
            fg_color=button_accent,
            hover_color=button_accent_hover,
            text_color=("#FFFFFF", "#FFFFFF"),
            corner_radius=6,
            command=self._trigger_search,
        )
        btn_search.pack(side="left", padx=5, pady=10)

        # Botão Limpar
        btn_clear = ctk.CTkButton(  # type: ignore[union-attr]
            self,
            text="✖ Limpar",
            width=100,
            height=32,
            fg_color=button_neutral,
            hover_color=button_neutral_hover,
            text_color=text_color,
            corner_radius=6,
            command=self._clear_search,
        )
        btn_clear.pack(side="left", padx=5, pady=10)

        # Separador visual
        sep1 = ctk.CTkFrame(self, width=2, height=32, fg_color=("#D0D0D0", "#404040"))  # type: ignore[union-attr]
        sep1.pack(side="left", padx=10, pady=10)

        # Label "Ordenar por"
        label_order = ctk.CTkLabel(  # type: ignore[union-attr]
            self,
            text="Ordenar:",
            text_color=text_color,
            font=("Segoe UI", 11),
        )
        label_order.pack(side="left", padx=(5, 5), pady=10)

        # OptionMenu de ordenação
        self.order_combobox = ctk.CTkOptionMenu(  # type: ignore[union-attr]
            self,
            variable=self.var_ordem,
            values=list(order_choices),
            width=180,
            height=32,
            fg_color=dropdown_bg,
            button_color=button_accent,
            button_hover_color=button_accent_hover,
            text_color=text_color,
            dropdown_fg_color=dropdown_bg,
            dropdown_hover_color=dropdown_hover,
            dropdown_text_color=text_color,
            command=lambda _: self._trigger_order_change(),
        )
        self.order_combobox.pack(side="left", padx=5, pady=10)

        # Label "Status"
        label_status = ctk.CTkLabel(  # type: ignore[union-attr]
            self,
            text="Status:",
            text_color=text_color,
            font=("Segoe UI", 11),
        )
        label_status.pack(side="left", padx=(10, 5), pady=10)

        # OptionMenu de status
        self.status_combobox = ctk.CTkOptionMenu(  # type: ignore[union-attr]
            self,
            variable=self.var_status,
            values=list(status_choices),
            width=150,
            height=32,
            fg_color=dropdown_bg,
            button_color=button_accent,
            button_hover_color=button_accent_hover,
            text_color=text_color,
            dropdown_fg_color=dropdown_bg,
            dropdown_hover_color=dropdown_hover,
            dropdown_text_color=text_color,
            command=lambda _: self._trigger_status_change(),
        )
        self.status_combobox.pack(side="left", padx=5, pady=10)

        # Separador visual
        sep2 = ctk.CTkFrame(self, width=2, height=32, fg_color=("#D0D0D0", "#404040"))  # type: ignore[union-attr]
        sep2.pack(side="left", padx=10, pady=10)

        # Botão Lixeira
        if on_open_trash:
            self.lixeira_button = ctk.CTkButton(  # type: ignore[union-attr]
                self,
                text="🗑️ Lixeira",
                width=110,
                height=32,
                fg_color=button_danger,
                hover_color=button_danger_hover,
                text_color=("#FFFFFF", "#FFFFFF"),
                corner_radius=6,
                command=on_open_trash,
            )
            self.lixeira_button.pack(side="left", padx=5, pady=10)
        else:
            self.lixeira_button = None

        # Placeholder para compatibilidade
        self.obrigacoes_button = None
        self.frame = self  # Alias para compatibilidade

        log.info("Toolbar CustomTkinter criada com sucesso")

    def _get_default_palette(self) -> dict[str, str]:
        """Retorna paleta padrão caso theme_manager não esteja disponível."""
        return {
            "bg": "#F0F0F0",
            "fg": "#000000",
            "entry_bg": "#FFFFFF",
            "entry_fg": "#000000",
            "accent": "#0078D7",
        }

    def _trigger_search(self) -> None:
        """Dispara callback de busca."""
        if self._on_search_changed:
            self._on_search_changed(self.var_busca.get())

    def _clear_search(self) -> None:
        """Limpa campo de busca e dispara callback."""
        self.var_busca.set("")
        if self._on_clear_search:
            self._on_clear_search()

    def _trigger_order_change(self) -> None:
        """Dispara callback de mudança de ordenação."""
        if self._on_order_changed:
            self._on_order_changed(self.var_ordem.get())

    def _trigger_status_change(self) -> None:
        """Dispara callback de mudança de status."""
        if self._on_status_changed:
            self._on_status_changed(self.var_status.get())

    def _build_fallback_toolbar(
        self,
        order_choices: Iterable[str],
        default_order: str,
        status_choices: Iterable[str],
    ) -> None:
        """Constrói toolbar legada quando CustomTkinter não está disponível."""
        # Importa versão antiga
        from src.ui.components import create_search_controls

        controls = create_search_controls(
            self,
            order_choices=list(order_choices),
            default_order=default_order,
            on_search=lambda _event=None: self._on_search_changed(self.var_busca.get())
            if self._on_search_changed
            else None,
            on_clear=lambda: self._on_clear_search() if self._on_clear_search else None,
            on_order_change=lambda: self._on_order_changed(self.var_ordem.get())
            if self._on_order_changed
            else None,
            on_status_change=lambda _event=None: self._on_status_changed(self.var_status.get())
            if self._on_status_changed
            else None,
            on_lixeira=self._on_open_trash,
            on_obrigacoes=None,
            status_choices=status_choices,
        )
        controls.frame.pack(fill="x", padx=0, pady=0)

        # Expor widgets
        self.entry_busca = controls.entry
        self.order_combobox = controls.order_combobox
        self.status_combobox = controls.status_combobox
        self.lixeira_button = controls.lixeira_button
        self.obrigacoes_button = controls.obrigacoes_button
        self.frame = controls.frame

    def refresh_colors(self, theme_manager: ClientesThemeManager) -> None:
        """Atualiza cores da toolbar quando tema muda.

        Args:
            theme_manager: Gerenciador de tema atualizado
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            return

        try:
            palette = theme_manager.get_palette()

            # Cores principais (ajustadas conforme nova paleta)
            toolbar_bg = (palette.get("toolbar_bg", "#F5F5F5"), palette.get("toolbar_bg", "#252525"))
            text_color = (palette.get("input_text", "#1C1C1C"), palette.get("input_text", "#DCE4EE"))
            input_bg = (palette.get("input_bg", "#FFFFFF"), palette.get("input_bg", "#333333"))
            input_border = (palette.get("input_border", "#C8C8C8"), palette.get("input_border", "#505050"))
            dropdown_bg = (palette.get("dropdown_bg", "#DCDCDC"), palette.get("dropdown_bg", "#3D3D3D"))

            # Atualiza frame principal
            self.configure(fg_color=toolbar_bg)

            # Atualiza Entry de busca (com bg_color para prevenir borda dupla)
            if hasattr(self, "entry_busca") and self.entry_busca:
                self.entry_busca.configure(
                    fg_color=input_bg,
                    bg_color=toolbar_bg,
                    text_color=text_color,
                    border_color=input_border,
                )

            # Atualiza OptionMenus
            if hasattr(self, "order_combobox") and self.order_combobox:
                self.order_combobox.configure(
                    fg_color=dropdown_bg,
                    text_color=text_color,
                    dropdown_fg_color=dropdown_bg,
                    dropdown_text_color=text_color,
                )

            if hasattr(self, "status_combobox") and self.status_combobox:
                self.status_combobox.configure(
                    fg_color=dropdown_bg,
                    text_color=text_color,
                    dropdown_fg_color=dropdown_bg,
                    dropdown_text_color=text_color,
                )

            log.debug("Cores da toolbar atualizadas dinamicamente")
        except Exception:
            log.exception("Erro ao atualizar cores da toolbar")
