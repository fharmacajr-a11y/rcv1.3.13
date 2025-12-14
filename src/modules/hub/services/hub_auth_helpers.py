# -*- coding: utf-8 -*-
"""Hub Auth Helpers - Funções headless para acesso a App/auth/org_id.

═══════════════════════════════════════════════════════════════════════════════
MÓDULO: hub_auth_helpers.py
CONTEXTO: MF-35 - Extração de helpers de auth do HubScreen
═══════════════════════════════════════════════════════════════════════════════

Este módulo contém helpers headless (sem dependências de Tkinter além de tipos)
para acessar informações de autenticação e organização a partir de widgets do Hub.

RESPONSABILIDADES:
- Navegar na hierarquia de widgets para encontrar a App principal
- Obter org_id, email, user_id de forma segura (sem exceções)
- Verificar status de online/autenticação

PRINCÍPIOS:
- Headless: Lógica pura sem conhecimento de UI (apenas tipos de widgets)
- Defensivo: Sempre retorna None/False em caso de erro (nunca levanta exceção)
- Reutilizável: Pode ser usado em qualquer componente do Hub

HISTÓRICO:
- MF-35: Criação inicial (extraído de HubScreen._get_app, _get_org_id_safe, etc.)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_app_from_widget(widget: Any) -> Any | None:
    """Sobe na hierarquia de widgets até encontrar a App principal.

    Equivalente a HubScreen._get_app, mas em forma de helper headless.

    Args:
        widget: Widget Tkinter inicial (geralmente self do HubScreen).

    Returns:
        Referência à App principal (com auth e _org_id_cache), ou None se não encontrado.

    Raises:
        Nenhuma exceção é levantada (retorna None em caso de erro).
    """
    try:
        # Subir na hierarquia até encontrar a janela raiz
        current = widget
        while current is not None:
            if hasattr(current, "auth") or hasattr(current, "_org_id_cache"):
                return current
            current = getattr(current, "master", None)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[HUB] Falha ao obter referência da App: %s", exc)
    return None


def get_org_id_safe_from_widget(widget: Any) -> Optional[str]:
    """Obtém org_id de forma segura a partir de um widget Hub-like.

    Equivalente a HubScreen._get_org_id_safe, mas em forma de helper headless.

    Tenta múltiplas estratégias:
    1. auth.get_org_id() (método preferido)
    2. app._get_org_id_cached(user_id) (fallback legado)

    Args:
        widget: Widget Tkinter inicial (geralmente self do HubScreen).

    Returns:
        org_id (UUID como string), ou None se não disponível.

    Raises:
        Nenhuma exceção é levantada (retorna None em caso de erro).
    """
    try:
        app = get_app_from_widget(widget)
        if not app or not hasattr(app, "auth") or not app.auth:
            return None

        auth = app.auth  # guarda local para satisfazer narrowing do Pyright

        # Tentar via accessor seguro
        org_id = auth.get_org_id()
        if org_id:
            return org_id

        # Fallback: usar método antigo se disponível
        if hasattr(app, "_get_org_id_cached"):
            user_id = auth.get_user_id()
            if user_id:
                return app._get_org_id_cached(user_id)

        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Não foi possível obter org_id (helper): %s", exc)
        return None


def get_email_safe_from_widget(widget: Any) -> Optional[str]:
    """Obtém email de forma segura a partir de um widget Hub-like.

    Equivalente a HubScreen._get_email_safe, mas em forma de helper headless.

    Args:
        widget: Widget Tkinter inicial (geralmente self do HubScreen).

    Returns:
        Email do usuário autenticado, ou None se não disponível.

    Raises:
        Nenhuma exceção é levantada (retorna None em caso de erro).
    """
    try:
        app = get_app_from_widget(widget)
        if not app or not hasattr(app, "auth") or not app.auth:
            return None
        return app.auth.get_email()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Não foi possível obter email (helper): %s", exc)
        return None


def get_user_id_safe_from_widget(widget: Any) -> Optional[str]:
    """Obtém user_id de forma segura a partir de um widget Hub-like.

    Equivalente a HubScreen._get_user_id_safe, mas em forma de helper headless.

    Args:
        widget: Widget Tkinter inicial (geralmente self do HubScreen).

    Returns:
        user_id (UUID como string), ou None se não disponível.

    Raises:
        Nenhuma exceção é levantada (retorna None em caso de erro).
    """
    try:
        app = get_app_from_widget(widget)
        if not app or not hasattr(app, "auth") or not app.auth:
            return None
        return app.auth.get_user_id()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Não foi possível obter user_id (helper): %s", exc)
        return None


def is_online_from_widget(widget: Any) -> bool:
    """Verifica se está online, usando a App (se existir).

    Equivalente a HubScreen._is_online, mas em forma de helper headless.

    Args:
        widget: Widget Tkinter inicial (geralmente self do HubScreen).

    Returns:
        True se online (ou se não conseguir verificar - assume online),
        False se explicitamente offline.

    Raises:
        Nenhuma exceção é levantada (retorna True em caso de erro).
    """
    try:
        app = get_app_from_widget(widget)
        if app and hasattr(app, "_net_is_online"):
            return bool(app._net_is_online)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[HUB] Falha ao verificar _net_is_online: %s", exc)
    return True  # Assume online se não conseguir verificar
