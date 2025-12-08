# -*- coding: utf-8 -*-
# pyright: strict

"""Connectivity State Manager - Gerenciamento headless de estado de conectividade.

MS-19: Responsável por gerenciar e computar estados de conectividade
de forma desacoplada da interface Tkinter.

Responsabilidades:
- Receber estado de conectividade bruto (state, description, text)
- Determinar se está online (bool)
- Computar texto para status bar
- Detectar transições de estado (para log)
- Centralizar lógica de interpretação de conectividade

A MainScreenFrame continua responsável por:
- Chamar get_supabase_state() e obter dados brutos
- Alimentar o ConnectivityStateManager com os dados
- Aplicar o snapshot nos widgets/atributos (app, status_var_text, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ConnectivityRawInput:
    """Input bruto de estado de conectividade.

    Atributos:
        state: Estado atual ("online", "unstable", "offline", "unknown")
        description: Descrição detalhada do estado
        text: Texto curto para exibição
        last_known_state: Último estado conhecido (para detectar transições)
    """

    state: Literal["online", "unstable", "offline", "unknown"]
    description: str
    text: str
    last_known_state: Literal["online", "unstable", "offline", "unknown"] = "unknown"


@dataclass(frozen=True)
class ConnectivitySnapshot:
    """Snapshot imutável do estado de conectividade computado.

    Atributos:
        state: Estado atual ("online", "unstable", "offline", "unknown")
        description: Descrição detalhada do estado
        text_for_status_bar: Texto completo para exibir na barra de status
        is_online: Se considera online (apenas quando state == "online")
        should_log_transition: Se deve logar transição de estado
        old_state: Estado anterior (para log)
    """

    state: Literal["online", "unstable", "offline", "unknown"]
    description: str
    text_for_status_bar: str
    is_online: bool
    should_log_transition: bool
    old_state: Literal["online", "unstable", "offline", "unknown"] = "unknown"


class ConnectivityStateManager:
    """Gerencia estado de conectividade de forma headless (sem UI).

    MS-19: Extrai a lógica de conectividade da MainScreenFrame,
    permitindo que a View apenas aplique o snapshot nos widgets.

    Exemplo de uso:
        # Na MainScreenFrame:
        manager = ConnectivityStateManager()

        # Ao receber estado de conectividade:
        state, description = get_supabase_state()

        raw = ConnectivityRawInput(
            state=state,
            description=description,
            text=text,
            last_known_state=self._last_cloud_state,
        )

        snapshot = manager.compute_snapshot(raw)

        # Aplicar snapshot:
        self.app._net_is_online = snapshot.is_online
        status_var.set(snapshot.text_for_status_bar)

        if snapshot.should_log_transition:
            log.info("Mudança: %s -> %s", snapshot.old_state, snapshot.state)
    """

    def __init__(self) -> None:
        """Inicializa o ConnectivityStateManager."""
        pass

    def compute_snapshot(self, raw: ConnectivityRawInput) -> ConnectivitySnapshot:
        """Computa snapshot de conectividade baseado no input bruto.

        Args:
            raw: Input bruto de conectividade (state, description, text, last_known_state)

        Returns:
            ConnectivitySnapshot com dados computados para aplicar na UI.
        """
        # Determinar se está online (apenas quando state == "online")
        is_online = raw.state == "online"

        # Computar texto para status bar
        # Formato: "Nuvem: TEXTO" onde TEXTO vem do raw.text
        text_for_status_bar = f"Nuvem: {raw.text}"

        # Detectar transição de estado
        should_log_transition = raw.state != raw.last_known_state

        return ConnectivitySnapshot(
            state=raw.state,
            description=raw.description,
            text_for_status_bar=text_for_status_bar,
            is_online=is_online,
            should_log_transition=should_log_transition,
            old_state=raw.last_known_state,
        )

    def update_status_bar_text(
        self,
        current_text: str,
        new_cloud_text: str,
    ) -> str:
        """Atualiza texto da status bar preservando outras partes.

        Args:
            current_text: Texto atual da status bar
            new_cloud_text: Novo texto para a parte "Nuvem: ..."

        Returns:
            Texto atualizado da status bar.

        Examples:
            >>> manager = ConnectivityStateManager()
            >>> manager.update_status_bar_text("Nuvem: ONLINE | Usuário: admin", "Nuvem: OFFLINE")
            'Nuvem: OFFLINE | Usuário: admin'

            >>> manager.update_status_bar_text("Usuário: admin", "Nuvem: ONLINE")
            'Nuvem: ONLINE'
        """
        if "Nuvem:" in current_text:
            # Substituir apenas a parte "Nuvem: ..."
            parts = current_text.split("|")
            parts[0] = new_cloud_text
            return " | ".join(parts)
        else:
            # Adicionar "Nuvem: ..." no início
            return new_cloud_text
