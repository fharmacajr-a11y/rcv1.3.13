# -*- coding: utf-8 -*-
"""MF-16: Estrutura para callbacks de navegação do HubScreen.

Este módulo define dataclass para agrupar todos os callbacks de navegação
de módulos externos, reduzindo o número de atributos individuais em HubScreen.

Responsabilidades:
- Centralizar callbacks de abertura de módulos (clientes, senhas, etc.)
- Fornecer interface clara para registro de callbacks
- Reduzir aliases e repetição em HubScreen

Benefícios:
- Menos atributos individuais em HubScreen (~9 atributos → 1)
- Clareza de quais callbacks estão disponíveis
- Facilita mock em testes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class HubNavigationCallbacks:
    """Container para callbacks de navegação de módulos externos.

    MF-16: Agrupa todos os callbacks open_* em uma estrutura,
    reduzindo o número de atributos individuais em HubScreen.

    Cada callback é opcional (None = funcionalidade não disponível).
    """

    # Módulo de Clientes
    open_clientes: Optional[Callable[[], None]] = None

    # Módulo de Senhas
    open_senhas: Optional[Callable[[], None]] = None

    # Módulo de Auditoria
    open_auditoria: Optional[Callable[[], None]] = None

    # Módulo de Fluxo de Caixa
    open_cashflow: Optional[Callable[[], None]] = None

    # Módulo ANVISA
    open_anvisa: Optional[Callable[[], None]] = None

    # Módulo Farmácia Popular
    open_farmacia_popular: Optional[Callable[[], None]] = None

    # Módulo SNGPC
    open_sngpc: Optional[Callable[[], None]] = None

    # Módulo SIFAP
    open_mod_sifap: Optional[Callable[[], None]] = None

    # Sites Externos
    open_sites: Optional[Callable[[], None]] = None

    def get_callback(self, module_name: str) -> Optional[Callable[[], None]]:
        """Obtém callback por nome de módulo.

        Args:
            module_name: Nome do módulo (ex: 'clientes', 'senhas', etc.)

        Returns:
            Callback correspondente ou None se não encontrado
        """
        callback_map = {
            "clientes": self.open_clientes,
            "senhas": self.open_senhas,
            "auditoria": self.open_auditoria,
            "cashflow": self.open_cashflow,
            "anvisa": self.open_anvisa,
            "farmacia_popular": self.open_farmacia_popular,
            "sngpc": self.open_sngpc,
            "sifap": self.open_mod_sifap,
            "sites": self.open_sites,
        }
        return callback_map.get(module_name)

    def is_available(self, module_name: str) -> bool:
        """Verifica se módulo tem callback configurado.

        Args:
            module_name: Nome do módulo

        Returns:
            True se callback está disponível (não None)
        """
        callback = self.get_callback(module_name)
        return callback is not None

    def invoke(self, module_name: str) -> bool:
        """Invoca callback de módulo se disponível.

        Args:
            module_name: Nome do módulo

        Returns:
            True se callback foi invocado, False se não encontrado
        """
        callback = self.get_callback(module_name)
        if callback:
            callback()
            return True
        return False
