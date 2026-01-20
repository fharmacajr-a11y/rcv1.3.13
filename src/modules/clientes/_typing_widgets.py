# -*- coding: utf-8 -*-
"""Protocolos de tipagem para widgets do módulo Clientes.

Este módulo define Protocols (PEP 544) para tipagem estrutural de widgets,
permitindo aceitar tanto tk.Widget quanto ctk.CTkButton sem usar Any.

Criado na Microfase 9 para substituir Any por tipagem estrutural.
"""

from __future__ import annotations

from typing import Any, Protocol

__all__ = ["SupportsCgetConfigure"]


class SupportsCgetConfigure(Protocol):
    """Protocol para widgets que suportam cget/configure (structural subtyping).
    
    Este protocolo define a interface mínima esperada para widgets usados no
    "pick mode" da actionbar, onde é necessário ler/alterar estado via cget/configure.
    
    Widgets compatíveis:
    - tk.Button, tk.Label, tk.Entry, etc. (tkinter padrão)
    - ctk.CTkButton, ctk.CTkLabel, ctk.CTkEntry, etc. (themed widgets)
    - ctk.CTkButton, ctk.CTkLabel, ctk.CTkEntry, etc. (customtkinter)
    
    Uso típico:
        def save_state(widget: SupportsCgetConfigure) -> str:
            return widget.cget("state")
        
        def restore_state(widget: SupportsCgetConfigure, state: str) -> None:
            widget.configure(state=state)
    
    Referências:
    - PEP 544: Protocols: Structural subtyping (static duck typing)
    - https://peps.python.org/pep-0544/
    """

    def cget(self, key: str) -> Any:
        """Obtém valor de uma opção de configuração do widget.
        
        Args:
            key: Nome da opção (ex: "state", "text", "fg")
        
        Returns:
            Valor atual da opção
        """
        ...

    def configure(self, **kwargs: Any) -> Any:
        """Configura opções do widget.
        
        Args:
            **kwargs: Pares chave=valor de opções a configurar
        
        Returns:
            None ou dicionário de configuração (dependendo do widget)
        """
        ...

    def __getitem__(self, key: str) -> Any:
        """Acesso por colchetes para opções do widget (equivalente a cget).
        
        Args:
            key: Nome da opção (ex: "state", "text", "fg")
        
        Returns:
            Valor atual da opção
        
        Note:
            Alguns widgets tkinter suportam sintaxe widget["key"] como alternativa
            a widget.cget("key"). Este método permite essa sintaxe.
        """
        ...
