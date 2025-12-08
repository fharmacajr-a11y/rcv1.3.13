# -*- coding: utf-8 -*-
# pyright: strict

"""Pick Mode Manager - Gerenciamento headless de modo de seleção (pick mode).

MS-20: Responsável por gerenciar estado de pick mode de forma desacoplada
da interface Tkinter.

Responsabilidades:
- Rastrear se pick mode está ativo ou não
- Determinar quais elementos da UI devem ser desabilitados/ocultados
- Fornecer snapshot imutável do estado de pick mode
- Centralizar decisões sobre comportamento em pick mode

A MainScreenFrame continua responsável por:
- Chamar enter_pick_mode() / exit_pick_mode() em resposta a eventos
- Aplicar o snapshot nos widgets (footer, topbar, botões)
- Gerenciar callbacks e retorno ao módulo anterior
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PickModeSnapshot:
    """Snapshot imutável do estado de pick mode.

    Atributos:
        is_pick_mode_active: Se o pick mode está ativo
        should_disable_trash_button: Se o botão lixeira deve estar desabilitado
        should_disable_topbar_menus: Se menus da topbar devem estar desabilitados
        should_show_pick_banner: Se o banner de pick mode deve ser exibido
        should_disable_crud_buttons: Se botões CRUD (novo, editar, etc.) devem estar desabilitados
    """

    is_pick_mode_active: bool
    should_disable_trash_button: bool
    should_disable_topbar_menus: bool
    should_show_pick_banner: bool
    should_disable_crud_buttons: bool


class PickModeManager:
    """Gerencia estado de pick mode de forma headless (sem UI).

    MS-20: Extrai a lógica de pick mode da MainScreenFrame,
    permitindo que a View apenas aplique o snapshot nos widgets.

    Regras de pick mode:
    - Quando ativo:
      - Banner de seleção deve aparecer
      - Botões CRUD (novo, editar, subpastas, enviar) ficam ocultos
      - Lixeira fica VISÍVEL mas DESABILITADA (cinza)
      - Menus da topbar (Conversor PDF, etc.) ficam desabilitados
      - Botão "Selecionar" aparece e fica habilitado quando há seleção

    Exemplo de uso:
        # Na MainScreenFrame:
        manager = PickModeManager()

        # Ao entrar em pick mode:
        snapshot = manager.enter_pick_mode()

        # Aplicar snapshot:
        if snapshot.should_show_pick_banner:
            self._pick_banner_frame.pack(...)

        if snapshot.should_disable_trash_button:
            self.btn_lixeira.configure(state="disabled")

        if snapshot.should_disable_topbar_menus:
            self.app.topbar.set_pick_mode_active(True)

        # Ao sair de pick mode:
        snapshot = manager.exit_pick_mode()

        if not snapshot.should_show_pick_banner:
            self._pick_banner_frame.pack_forget()
    """

    def __init__(self) -> None:
        """Inicializa o PickModeManager."""
        self._active: bool = False
        self._trash_button_state_before_pick: str | None = None

    def enter_pick_mode(self, trash_button_current_state: str | None = None) -> PickModeSnapshot:
        """Entra em pick mode e retorna snapshot.

        Args:
            trash_button_current_state: Estado atual do botão lixeira (para restaurar depois)

        Returns:
            PickModeSnapshot com flags para aplicar na UI.
        """
        self._active = True

        # Salvar estado da lixeira para restaurar depois
        if trash_button_current_state is not None:
            self._trash_button_state_before_pick = trash_button_current_state

        return self._build_snapshot()

    def exit_pick_mode(self) -> PickModeSnapshot:
        """Sai de pick mode e retorna snapshot.

        Returns:
            PickModeSnapshot com flags para restaurar UI ao estado normal.
        """
        self._active = False
        return self._build_snapshot()

    def get_snapshot(self) -> PickModeSnapshot:
        """Obtém snapshot atual do estado de pick mode.

        Returns:
            PickModeSnapshot com estado atual.
        """
        return self._build_snapshot()

    def get_saved_trash_button_state(self) -> str:
        """Obtém estado salvo do botão lixeira antes do pick mode.

        Returns:
            Estado salvo ou "normal" se não houver estado salvo.
        """
        return self._trash_button_state_before_pick or "normal"

    def _build_snapshot(self) -> PickModeSnapshot:
        """Constrói snapshot baseado no estado atual.

        Returns:
            PickModeSnapshot imutável.
        """
        return PickModeSnapshot(
            is_pick_mode_active=self._active,
            should_disable_trash_button=self._active,  # Lixeira desabilitada em pick mode
            should_disable_topbar_menus=self._active,  # Menus desabilitados em pick mode
            should_show_pick_banner=self._active,  # Banner visível em pick mode
            should_disable_crud_buttons=self._active,  # CRUD desabilitado em pick mode
        )
