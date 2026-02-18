# -*- coding: utf-8 -*-
"""Shim para show_client_obligations_window.

Este módulo existe para que ``@patch`` nos testes consiga resolver o caminho
``src.modules.clientes.views.client_obligations_window.show_client_obligations_window``
sem gerar ``AttributeError``.

A funcionalidade real de gerenciamento de obrigações ainda não foi implementada;
quando for, este arquivo deverá ser substituído pela implementação completa.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def show_client_obligations_window(
    *,
    parent: Any = None,
    org_id: Optional[str] = None,
    created_by: Optional[str] = None,
    client_id: Optional[int] = None,
    client_name: Optional[str] = None,
    on_refresh_hub: Optional[Callable[[], None]] = None,
) -> None:
    """Abre a janela de obrigações para um cliente.

    .. note::
        Stub – a funcionalidade está em desenvolvimento.
        Os parâmetros refletem a assinatura esperada pelos testes existentes.
    """
    logger.info(
        "show_client_obligations_window chamada (stub) – client_id=%s, client_name=%s",
        client_id,
        client_name,
    )
