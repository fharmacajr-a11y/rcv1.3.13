from __future__ import annotations

from src.ui.ctk_config import ctk

# -*- coding: utf-8 -*-
"""ActionBar customizada com widgets CustomTkinter para o módulo Clientes.

Esta ActionBar usa CustomTkinter para uma aparência moderna e suporte
nativo a temas Light/Dark nos botões de ação inferior (Novo, Editar, Arquivos, Excluir).
"""

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Callable, Optional

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
# Tipagem estrutural para widgets (Microfase 9)
from .._typing_widgets import SupportsCgetConfigure

if TYPE_CHECKING:
    from src.modules.clientes.appearance import ClientesThemeManager

log = logging.getLogger(__name__)

__all__ = ["ClientesActionBarCtk", "HAS_CUSTOMTKINTER"]


class ClientesActionBarCtk(ctk.CTkFrame if HAS_CUSTOMTKINTER else tk.Frame):  # type: ignore[misc]
    """ActionBar moderna com CustomTkinter para ações CRUD na barra inferior."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_novo: Callable[[], None],
        on_editar: Callable[[], None],
        on_subpastas: Callable[[], None],
        on_excluir: Optional[Callable[[], None]] = None,
        theme_manager: Optional[ClientesThemeManager] = None,
    ) -> None:
        """Inicializa actionbar com widgets CustomTkinter.

        Args:
            master: Widget pai
            on_novo: Callback para criar novo cliente
            on_editar: Callback para editar cliente selecionado
            on_subpastas: Callback para abrir arquivos do cliente
            on_excluir: Callback para excluir cliente selecionado (opcional)
            theme_manager: Gerenciador de tema (para cores dinâmicas)
        """
        super().__init__(master)

        self._theme_manager = theme_manager
        self._on_novo = on_novo
        self._on_editar = on_editar
        self._on_subpastas = on_subpastas
        self._on_excluir = on_excluir

        # Estado interno para pick mode
        self._uploading_busy = False
        self._pick_prev_states: dict[SupportsCgetConfigure, str] = {}  # Protocol: cget/configure (Microfase 9)

        # Obtém cores do tema
        palette = theme_manager.get_palette() if theme_manager else self._get_default_palette()

        # Configura cores por tupla (light, dark) para CustomTkinter
        # IMPORTANTE: usar toolbar_bg para evitar "fundo branco" vazando
        frame_bg = (palette.get("toolbar_bg", "#F5F5F5"), palette.get("toolbar_bg", "#252525"))
        text_color = (palette.get("input_text", "#1C1C1C"), palette.get("input_text", "#DCE4EE"))
        text_disabled = (palette.get("input_placeholder", "#999999"), palette.get("input_placeholder", "#808080"))
        
        # Cores semânticas dos botões
        success_color = ("#28A745", "#1E7E34")  # Verde para "Novo Cliente"
        success_hover = ("#218838", "#155724")
        secondary_color = (palette.get("neutral_btn", "#E0E0E0"), palette.get("neutral_btn", "#3D3D3D"))
        secondary_hover = (palette.get("neutral_hover", "#C0C0C0"), palette.get("neutral_hover", "#2D2D2D"))
        info_color = (palette.get("accent", "#0078D7"), palette.get("accent", "#0078D7"))
        info_hover = (palette.get("accent_hover", "#0056B3"), palette.get("accent_hover", "#005A9E"))
        danger_color = (palette.get("danger", "#F44336"), palette.get("danger", "#D32F2F"))
        danger_hover = (palette.get("danger_hover", "#D32F2F"), palette.get("danger_hover", "#B71C1C"))

        if not HAS_CUSTOMTKINTER:
            # Fallback para tk.Frame se CustomTkinter não disponível
            log.warning("CustomTkinter não disponível, usando actionbar legada")
            self._build_fallback_actionbar()
            return

        # Container principal
        self.configure(fg_color=frame_bg, corner_radius=0)

        # Constantes para padronização (todos botões com mesma altura/corner/pady)
        BTN_HEIGHT = 36
        BTN_CORNER = 6
        BTN_PADX = 8  # Uniforme entre botões
        BTN_PADY = 10  # Uniforme vertical
        BTN_FONT = ("Segoe UI", 11)

        # Botão Novo Cliente (primário - verde)
        self.btn_novo = ctk.CTkButton(  # type: ignore[union-attr]
            self,
            text="Novo Cliente",
            width=120,
            height=BTN_HEIGHT,
            fg_color=success_color,
            hover_color=success_hover,
            text_color=("#FFFFFF", "#FFFFFF"),
            text_color_disabled=text_disabled,
            corner_radius=BTN_CORNER,
            font=BTN_FONT,
            command=self._on_novo,
        )
        self.btn_novo.grid(row=0, column=0, padx=BTN_PADX, pady=BTN_PADY, sticky="w")

        # Botão Editar (secundário - cinza)
        self.btn_editar = ctk.CTkButton(  # type: ignore[union-attr]
            self,
            text="Editar",
            width=100,
            height=BTN_HEIGHT,
            fg_color=secondary_color,
            hover_color=secondary_hover,
            text_color=text_color,
            text_color_disabled=text_disabled,
            corner_radius=BTN_CORNER,
            font=BTN_FONT,
            command=self._on_editar,
        )
        self.btn_editar.grid(row=0, column=1, padx=BTN_PADX, pady=BTN_PADY, sticky="w")

        # Botão Arquivos (info - azul)
        self.btn_subpastas = ctk.CTkButton(  # type: ignore[union-attr]
            self,
            text="Arquivos",
            width=100,
            height=BTN_HEIGHT,
            fg_color=info_color,
            hover_color=info_hover,
            text_color=("#FFFFFF", "#FFFFFF"),
            text_color_disabled=text_disabled,
            corner_radius=BTN_CORNER,
            font=BTN_FONT,
            command=self._on_subpastas,
        )
        self.btn_subpastas.grid(row=0, column=2, padx=BTN_PADX, pady=BTN_PADY, sticky="w")

        # Botão Excluir (danger - vermelho)
        if on_excluir:
            self.btn_excluir = ctk.CTkButton(  # type: ignore[union-attr]
                self,
                text="Excluir",
                width=100,
                height=BTN_HEIGHT,
                fg_color=danger_color,
                hover_color=danger_hover,
                text_color=("#FFFFFF", "#FFFFFF"),
                text_color_disabled=text_disabled,
                corner_radius=BTN_CORNER,
                font=BTN_FONT,
                command=self._on_excluir,
            )
            self.btn_excluir.grid(row=0, column=3, padx=BTN_PADX, pady=BTN_PADY, sticky="w")
        else:
            self.btn_excluir = None

        # Placeholders para compatibilidade com código legado
        self.btn_obrigacoes = None
        self.btn_batch_delete = None
        self.btn_batch_restore = None
        self.btn_batch_export = None
        self.frame = self  # Alias para compatibilidade

        # Estado inicial: botões dependentes de seleção desabilitados
        self.update_state(has_selection=False)

        log.info("ActionBar CustomTkinter criada com sucesso")

    def _get_default_palette(self) -> dict[str, str]:
        """Retorna paleta padrão caso theme_manager não esteja disponível."""
        return {
            "bg": "#FFFFFF",
            "input_text": "#000000",
            "input_placeholder": "#999999",
            "accent": "#0078D7",
            "accent_hover": "#0056B3",
            "neutral_btn": "#E0E0E0",
            "neutral_hover": "#C0C0C0",
            "danger": "#F44336",
            "danger_hover": "#D32F2F",
        }

    def update_state(self, has_selection: bool) -> None:
        """Habilita/desabilita botões com base na seleção da Treeview.

        Args:
            has_selection: Se True, habilita Editar/Arquivos/Excluir. Se False, desabilita.
        """
        if not HAS_CUSTOMTKINTER:
            return

        try:
            state = "normal" if has_selection else "disabled"
            
            # Novo Cliente sempre habilitado
            if hasattr(self, "btn_novo") and self.btn_novo:
                self.btn_novo.configure(state="normal")
            
            # Editar, Arquivos e Excluir dependem de seleção
            if hasattr(self, "btn_editar") and self.btn_editar:
                self.btn_editar.configure(state=state)
            
            if hasattr(self, "btn_subpastas") and self.btn_subpastas:
                self.btn_subpastas.configure(state=state)
            
            if hasattr(self, "btn_excluir") and self.btn_excluir:
                self.btn_excluir.configure(state=state)

            log.debug(f"Estado dos botões atualizado: has_selection={has_selection}")
        except Exception:
            log.exception("Erro ao atualizar estado dos botões")

    def refresh_colors(self, theme_manager: ClientesThemeManager) -> None:
        """Atualiza cores da actionbar quando tema muda.

        Args:
            theme_manager: Gerenciador de tema atualizado
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            return

        try:
            palette = theme_manager.get_palette()

            # Cores principais (usar toolbar_bg para consistência)
            frame_bg = (palette.get("toolbar_bg", "#F5F5F5"), palette.get("toolbar_bg", "#252525"))
            text_color = (palette.get("input_text", "#1C1C1C"), palette.get("input_text", "#DCE4EE"))
            secondary_color = (palette.get("neutral_btn", "#DCDCDC"), palette.get("neutral_btn", "#3D3D3D"))
            secondary_hover = (palette.get("neutral_hover", "#BEBEBE"), palette.get("neutral_hover", "#2D2D2D"))

            # Atualiza frame principal
            self.configure(fg_color=frame_bg)

            # Atualiza botão Editar (secundário muda com tema)
            if hasattr(self, "btn_editar") and self.btn_editar:
                self.btn_editar.configure(
                    fg_color=secondary_color,
                    hover_color=secondary_hover,
                    text_color=text_color,
                )

            log.debug("Cores da actionbar atualizadas dinamicamente")
        except Exception:
            log.exception("Erro ao atualizar cores da actionbar")

    def _build_fallback_actionbar(self) -> None:
        """Constrói actionbar legada quando CustomTkinter não está disponível."""
        # Importa versão antiga
        from src.ui.components import create_footer_buttons

        buttons = create_footer_buttons(
            self,
            on_novo=self._on_novo,
            on_editar=self._on_editar,
            on_subpastas=self._on_subpastas,
            on_excluir=self._on_excluir,
            on_obrigacoes=None,
            on_batch_delete=None,
            on_batch_restore=None,
            on_batch_export=None,
        )
        buttons.frame.pack(fill="x", padx=0, pady=0)

        # Expor widgets
        self.btn_novo = buttons.novo
        self.btn_editar = buttons.editar
        self.btn_subpastas = buttons.subpastas
        self.btn_excluir = buttons.excluir
        self.btn_obrigacoes = buttons.obrigacoes
        self.btn_batch_delete = buttons.batch_delete
        self.btn_batch_restore = buttons.batch_restore
        self.btn_batch_export = buttons.batch_export
        self.frame = buttons.frame

    def _iter_pick_buttons(self) -> list[SupportsCgetConfigure]:
        """Lista exatamente os botões da actionbar que devem ser controlados em pick mode.
        
        Retorna SupportsCgetConfigure (Protocol) para tipagem estrutural (Microfase 9).
        """
        buttons: list[SupportsCgetConfigure] = []
        for btn in [self.btn_novo, self.btn_editar, self.btn_subpastas]:
            if btn is not None:
                buttons.append(btn)
        return buttons

    def enter_pick_mode(self) -> None:
        """Desabilita botões da actionbar em modo seleção de clientes."""
        log.debug("ClientesActionBarCtk.enter_pick_mode()")

        # Salva estado original e desabilita
        for btn in self._iter_pick_buttons():
            try:
                if btn not in self._pick_prev_states:
                    current_state = str(btn["state"]) if not HAS_CUSTOMTKINTER else btn.cget("state")
                    self._pick_prev_states[btn] = current_state
                btn.configure(state="disabled")
            except Exception as exc:
                log.debug(f"Ignorando falha ao desabilitar botão {btn} em pick mode: {exc}")

    def leave_pick_mode(self) -> None:
        """Restaura estados dos botões da actionbar após sair do modo seleção."""
        log.debug("ClientesActionBarCtk.leave_pick_mode()")

        # Restaura estados originais
        for btn in self._iter_pick_buttons():
            try:
                prev = self._pick_prev_states.get(btn)
                if prev is not None:
                    btn.configure(state=prev)
            except Exception as exc:
                log.debug(f"Ignorando falha ao restaurar botão {btn} após pick mode: {exc}")

        self._pick_prev_states.clear()
