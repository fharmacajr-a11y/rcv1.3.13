# -*- coding: utf-8 -*-
"""
MF-18: Helpers para módulos e navegação do Hub.

Este módulo contém funções relacionadas à construção e estilo de
botões de módulos no HubScreen.

Extraído de hub_screen_helpers.py na MF-18 para melhor organização.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModuleButton:
    """Configuração de um botão de módulo no Hub."""

    text: str
    enabled: bool
    bootstyle: str
    has_callback: bool


def build_module_buttons(
    has_clientes: bool = True,
    has_senhas: bool = True,
    has_auditoria: bool = True,
    has_cashflow: bool = False,
    has_anvisa: bool = False,
    has_farmacia_popular: bool = False,
    has_sngpc: bool = False,
    has_sifap: bool = False,
) -> list[ModuleButton]:
    """
    Constrói lista de botões de módulos baseado em features habilitadas.

    Esta função centraliza a lógica de quais módulos aparecem no Hub
    e em qual ordem, facilitando testes e manutenção.

    Args:
        has_clientes: Se módulo Clientes está habilitado
        has_senhas: Se módulo Senhas está habilitado
        has_auditoria: Se módulo Auditoria está habilitado
        has_cashflow: Se módulo Fluxo de Caixa está habilitado
        has_anvisa: Se módulo Anvisa está habilitado
        has_farmacia_popular: Se módulo Farmácia Popular está habilitado
        has_sngpc: Se módulo Sngpc está habilitado
        has_sifap: Se módulo Sifap está habilitado

    Returns:
        Lista de ModuleButton na ordem de exibição

    Examples:
        >>> buttons = build_module_buttons()
        >>> len(buttons)
        8
        >>> buttons[0].text
        'Clientes'
        >>> buttons[0].bootstyle
        'info'
        >>> buttons[0].enabled
        True
        >>> buttons_no_cashflow = build_module_buttons(has_cashflow=False)
        >>> cashflow_btn = [b for b in buttons_no_cashflow if b.text == 'Fluxo de Caixa'][0]
        >>> cashflow_btn.enabled
        False
    """
    buttons = []

    # Ordem fixa de módulos
    if has_clientes:
        buttons.append(ModuleButton("Clientes", True, "info", True))

    if has_senhas:
        buttons.append(ModuleButton("Senhas", True, "info", True))

    if has_auditoria:
        buttons.append(ModuleButton("Auditoria", True, "success", True))

    # Fluxo de Caixa (em desenvolvimento)
    buttons.append(
        ModuleButton(
            "Fluxo de Caixa",
            enabled=has_cashflow,
            bootstyle="warning",
            has_callback=has_cashflow,
        )
    )

    # Módulos em desenvolvimento (sempre aparecem, mas desabilitados)
    buttons.append(ModuleButton("Anvisa", has_anvisa, "secondary", has_anvisa))
    buttons.append(
        ModuleButton(
            "Farmácia Popular",
            has_farmacia_popular,
            "secondary",
            has_farmacia_popular,
        )
    )
    buttons.append(ModuleButton("Sngpc", has_sngpc, "secondary", has_sngpc))
    buttons.append(ModuleButton("Sifap", has_sifap, "secondary", has_sifap))

    return buttons


def calculate_module_button_style(
    highlight: bool = False,
    yellow: bool = False,
    bootstyle: Optional[str] = None,
) -> str:
    """
    Determina o estilo de um botão de módulo baseado em flags de estado.

    Esta função implementa a hierarquia de prioridade de estilos:
    1. bootstyle explícito (maior prioridade)
    2. yellow (warning)
    3. highlight (success)
    4. padrão (secondary)

    Args:
        highlight: Se True, usa estilo "success" (verde)
        yellow: Se True, usa estilo "warning" (amarelo)
        bootstyle: Estilo explícito que sobrescreve highlight/yellow

    Returns:
        str: Nome do estilo ttkbootstrap ("success", "warning", "secondary", ou customizado)

    Examples:
        >>> calculate_module_button_style()
        'secondary'
        >>> calculate_module_button_style(highlight=True)
        'success'
        >>> calculate_module_button_style(yellow=True)
        'warning'
        >>> calculate_module_button_style(bootstyle='danger')
        'danger'
        >>> calculate_module_button_style(highlight=True, yellow=True)
        'warning'
        >>> calculate_module_button_style(highlight=True, bootstyle='info')
        'info'
    """
    if bootstyle:
        return bootstyle
    if yellow:
        return "warning"
    if highlight:
        return "success"
    return "secondary"
