# -*- coding: utf-8 -*-
"""Helpers de integração para o módulo de Senhas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable
from tkinter import messagebox

from src.infra.supabase_client import supabase
from src.modules.passwords.controller import ClientPasswordsSummary, PasswordsController

if TYPE_CHECKING:
    from src.modules.passwords.views.client_passwords_dialog import ClientPasswordsDialog

log = logging.getLogger(__name__)

ControllerFactory = Callable[[], PasswordsController]
DialogCls = type["ClientPasswordsDialog"]


def _extract_user_and_org(parent: Any | None) -> tuple[str | None, str | None, Any]:
    """Extrai user_id, org_id e app da janela parent.

    Returns:
        tuple[org_id | None, user_id | None, app widget]
    """
    user_id: str | None = None
    org_id: str | None = None
    app = getattr(parent, "winfo_toplevel", lambda: None)() or parent

    try:
        user_resp = supabase.auth.get_user()
        user_obj = getattr(user_resp, "user", None) or user_resp
        if isinstance(user_obj, dict):
            user_id = user_obj.get("id") or user_obj.get("uid")
        else:
            user_id = getattr(user_obj, "id", None)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao obter usuario autenticado para senhas: %s", exc)

    if app and hasattr(app, "_get_org_id_cached") and user_id:
        try:
            org_id = app._get_org_id_cached(user_id)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao obter org_id via app: %s", exc)

    if not org_id:
        try:
            from src.modules.clientes.service import _resolve_current_org_id  # type: ignore

            org_id = _resolve_current_org_id()
        except Exception as exc:  # noqa: BLE001
            log.debug("Fallback de org_id para senhas falhou: %s", exc)

    return org_id, user_id, app


def open_senhas_for_cliente(
    parent: Any | None,
    cliente_id: str | int,
    razao_social: str | None = None,
    *,
    controller_factory: ControllerFactory | None = None,
    dialog_cls: DialogCls | None = None,
) -> None:
    """Abre o diálogo de senhas focado em um cliente específico.

    Se o cliente não possuir senhas cadastradas, exibe um aviso informativo.

    Args:
        parent: Widget Tkinter parent ou None
        cliente_id: ID do cliente (string ou int)
        razao_social: Nome do cliente (opcional)
        controller_factory: Factory para criar controller (para testes)
        dialog_cls: Classe do dialog (para testes)
    """
    from src.modules.passwords.views.client_passwords_dialog import ClientPasswordsDialog

    controller_factory = controller_factory or PasswordsController
    dialog_cls = dialog_cls or ClientPasswordsDialog

    org_id, user_id, app = _extract_user_and_org(parent)
    msg_parent = parent if parent is not None else app
    if not org_id or not user_id:
        messagebox.showerror("Erro", "Não foi possível identificar o usuário/organização atual.", parent=msg_parent)
        return

    controller = controller_factory()

    try:
        controller.load_all_passwords(org_id)
        summaries = controller.group_passwords_by_client()
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha ao carregar senhas: %s", exc)
        messagebox.showerror("Erro", f"Falha ao carregar senhas: {exc}", parent=msg_parent)
        return

    summary: ClientPasswordsSummary | None = next((s for s in summaries if str(s.client_id) == str(cliente_id)), None)
    if summary is None:
        messagebox.showinfo("Senhas do Cliente", "Este cliente não possui senhas cadastradas.", parent=msg_parent)
        return

    try:
        clients = controller.list_clients(org_id)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao carregar lista de clientes para dialogo de senhas: %s", exc)
        clients = []

    try:
        dialog_cls(
            parent if getattr(parent, "winfo_exists", lambda: False)() else app,
            controller,
            summary,
            org_id,
            user_id,
            clients,
            on_close_refresh=getattr(app, "refresh_current_view", None),
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Erro ao abrir dialogo de senhas: %s", exc)
        messagebox.showerror("Erro", f"Falha ao abrir senhas: {exc}", parent=msg_parent)
