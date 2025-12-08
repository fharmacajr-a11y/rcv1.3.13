# -*- coding: utf-8 -*-
# pyright: strict

"""UI State Manager - Gerenciamento headless de estados de UI (botões).

MS-18: Responsável por calcular estados de botões da tela principal
de forma desacoplada da interface Tkinter.

Responsabilidades:
- Receber inputs de estado (seleção, conectividade, flags UI)
- Calcular estados de botões (enabled/disabled)
- Calcular textos de botões (quando dependem de estado)
- Devolver snapshot imutável de estados

A MainScreenFrame continua responsável por:
- Coletar inputs de estado (seleção, conectividade, flags)
- Aplicar snapshot nos widgets Tkinter
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.modules.clientes.views.main_screen_helpers import calculate_button_states


@dataclass(frozen=True)
class ButtonStatesSnapshot:
    """Snapshot imutável dos estados de botões da tela principal.

    Atributos:
        editar: Botão Editar habilitado (depende de seleção + online)
        subpastas: Botão Subpastas habilitado (depende de seleção + online)
        enviar: Botão Enviar habilitado (depende de seleção + online + não uploading)
        novo: Botão Novo habilitado (depende de online)
        lixeira: Botão Lixeira habilitado (depende de online)
        select: Botão Selecionar habilitado (depende de seleção em pick mode)

        enviar_text: Texto do botão Enviar (varia com conectividade)
    """

    editar: bool
    subpastas: bool
    enviar: bool
    novo: bool
    lixeira: bool
    select: bool

    # Textos dinâmicos
    enviar_text: str = "Enviar Para SupaBase"


@dataclass(frozen=True)
class UiStateInput:
    """Input para cálculo de estados de UI.

    Atributos:
        has_selection: Se há um cliente selecionado na lista
        is_online: Se está conectado ao Supabase (estado "online")
        is_uploading: Se está em processo de upload
        is_pick_mode: Se está em modo de seleção (pick)
        connectivity_state: Estado detalhado de conectividade ("online", "unstable", "offline")
    """

    has_selection: bool
    is_online: bool
    is_uploading: bool
    is_pick_mode: bool = False
    connectivity_state: Literal["online", "unstable", "offline"] = "online"


class UiStateManager:
    """Gerencia estados de UI (botões) de forma headless (sem Tkinter).

    MS-18: Extrai a lógica de cálculo de estados de botões da MainScreenFrame,
    permitindo que a View apenas aplique o snapshot nos widgets.

    Exemplo de uso:
        # Na MainScreenFrame:
        manager = UiStateManager()

        # Ao precisar atualizar botões:
        inp = UiStateInput(
            has_selection=snapshot.has_selection,
            is_online=(state == "online"),
            is_uploading=self._uploading_busy,
            is_pick_mode=self._pick_mode,
            connectivity_state=state,
        )

        button_states = manager.compute_button_states(inp)

        # Aplicar estados:
        self.btn_editar.configure(state="normal" if button_states.editar else "disabled")
        self.btn_enviar.configure(text=button_states.enviar_text)
    """

    def __init__(self) -> None:
        """Inicializa o UiStateManager."""
        pass

    def compute_button_states(self, inp: UiStateInput) -> ButtonStatesSnapshot:
        """Calcula estados de todos os botões baseado no input de estado.

        Args:
            inp: Input de estado (seleção, conectividade, flags UI)

        Returns:
            ButtonStatesSnapshot com estados de todos os botões e textos dinâmicos.
        """
        # Delegar cálculo de estados booleanos ao helper puro
        raw_states = calculate_button_states(
            has_selection=inp.has_selection,
            is_online=inp.is_online,
            is_uploading=inp.is_uploading,
            is_pick_mode=inp.is_pick_mode,
        )

        # Calcular texto do botão Enviar baseado em conectividade
        enviar_text = self._compute_enviar_text(
            connectivity_state=inp.connectivity_state,
            is_uploading=inp.is_uploading,
        )

        return ButtonStatesSnapshot(
            editar=raw_states["editar"],
            subpastas=raw_states["subpastas"],
            enviar=raw_states["enviar"],
            novo=raw_states["novo"],
            lixeira=raw_states["lixeira"],
            select=raw_states["select"],
            enviar_text=enviar_text,
        )

    def _compute_enviar_text(
        self,
        *,
        connectivity_state: Literal["online", "unstable", "offline"],
        is_uploading: bool,
    ) -> str:
        """Calcula o texto do botão Enviar baseado em conectividade.

        Args:
            connectivity_state: Estado de conectividade ("online", "unstable", "offline")
            is_uploading: Se está em processo de upload

        Returns:
            Texto apropriado para o botão Enviar.
        """
        if is_uploading:
            return "Enviando..."

        if connectivity_state == "online":
            return "Enviar Para SupaBase"
        elif connectivity_state == "unstable":
            return "Envio suspenso - Conexao instavel"
        else:  # offline
            return "Envio suspenso - Offline"
