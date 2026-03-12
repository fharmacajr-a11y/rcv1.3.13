# -*- coding: utf-8 -*-
"""High-level actions triggered by the GUI (CRUD, folders, trash integration)."""

from __future__ import annotations

import importlib
import logging
import os
from tkinter import TclError, messagebox
from typing import Any, Sequence

from src.modules.clientes.core.service import mover_cliente_para_lixeira

try:
    from src.modules.lixeira import abrir_lixeira as _module_abrir_lixeira, refresh_if_open as _module_refresh_if_open
except ImportError:
    _module_abrir_lixeira = None
    _module_refresh_if_open = None

# ------------------------------------------------------------
# Modo "somente nuvem" (não cria nada em disco local)
# defina RC_NO_LOCAL_FS=1 no .env para ativar
# ------------------------------------------------------------
NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_messagebox(method: str, *args: Any, **kwargs: Any) -> Any:
    """Invoca messagebox.<method> em modo best-effort, ignorando falhas em ambientes sem GUI."""
    func = getattr(messagebox, method, None)
    if callable(func):
        try:
            return func(*args, **kwargs)
        except (TclError, RuntimeError):
            log.debug("messagebox.%s failed", method, exc_info=True)
    return None


def _try_refresh_clients_frame(app: Any) -> None:
    """Tenta recarregar o frame de clientes (best-effort)."""
    try:
        frame = getattr(app, "_main_screen_frame", lambda: None)()
        if frame is not None and hasattr(frame, "load_async"):
            frame.load_async()
    except Exception:
        log.debug("_try_refresh_clients_frame: could not refresh", exc_info=True)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def novo_cliente(app: Any) -> None:
    """Abre o diálogo para cadastro de um novo cliente (ClientEditorDialog)."""
    log.info("Opening dialog for new client")

    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    def _on_saved(data: dict) -> None:
        log.info("New client saved successfully")
        # Recarregar tela de clientes se estiver visível
        _try_refresh_clients_frame(app)

    ClientEditorDialog(
        parent=app,
        client_id=None,
        on_save=_on_saved,
    )


def editar_cliente(app: Any, pk: int) -> None:
    """Abre o diálogo de edição para o cliente informado (ClientEditorDialog)."""
    log.info("Opening editor dialog for client id=%s", pk)

    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    def _on_saved(data: dict) -> None:
        log.info("Client id=%s saved successfully", pk)
        _try_refresh_clients_frame(app)

    ClientEditorDialog(
        parent=app,
        client_id=pk,
        on_save=_on_saved,
    )


def excluir_cliente(app: Any, selected_values: Sequence[Any]) -> None:
    """Move um cliente selecionado para a lixeira após confirmação do usuário."""
    if not selected_values:
        _safe_messagebox("showwarning", "Atenção", "Selecione um cliente primeiro.")
        return

    try:
        client_id = int(selected_values[0])
    except (TypeError, ValueError):
        _safe_messagebox("showerror", "Erro", "Seleção inválida (ID ausente).")
        log.error("Invalid selected_values for exclusion: %s", selected_values)
        return

    razao = ""
    if len(selected_values) > 1:
        try:
            razao = (selected_values[1] or "").strip()
        except (AttributeError, TypeError):
            razao = ""
    label_cli = f"{razao} (ID {client_id})" if razao else f"ID {client_id}"

    confirm = _safe_messagebox(
        "askyesno",
        "Enviar para Lixeira",
        f"Deseja enviar o cliente {label_cli} para a Lixeira?",
    )
    if confirm is False:
        return

    try:
        mover_cliente_para_lixeira(client_id)
    except (TimeoutError, ConnectionError, OSError) as exc:
        _safe_messagebox("showerror", "Erro ao excluir", f"Falha ao enviar para a Lixeira: {exc}")
        log.exception("Failed to soft-delete client %s", label_cli)
        return

    try:
        app.carregar()
    except (AttributeError, RuntimeError):
        log.exception("Failed to refresh client list after soft delete")

    if _module_refresh_if_open is not None:
        try:
            _module_refresh_if_open()
        except (AttributeError, RuntimeError):
            log.debug("Lixeira refresh skipped", exc_info=True)

    _safe_messagebox("showinfo", "Lixeira", f"Cliente {label_cli} enviado para a Lixeira.")
    log.info("Cliente %s enviado para a Lixeira com sucesso", label_cli)


# ---------------------------------------------------------------------------
# Lixeira (trash)
# ---------------------------------------------------------------------------
def abrir_lixeira_ui(app: Any, *args: Any, **kwargs: Any) -> None:
    """Localiza e abre a janela da Lixeira, armazenando o handle no app."""
    log.info("Opening Lixeira UI window")
    abrir_fn = _module_abrir_lixeira

    if abrir_fn is None:
        try:
            from src.modules.lixeira.views.lixeira import abrir_lixeira as _abrir

            abrir_fn = _abrir
        except ImportError:
            log.debug("Primary lixeira package import failed", exc_info=True)

    if abrir_fn is None:
        for module_name in ("src.modules.lixeira", "src.ui.lixeira", "ui.lixeira"):
            try:
                module = importlib.import_module(module_name)
                candidate = getattr(module, "abrir_lixeira", None)
                if callable(candidate):
                    abrir_fn = candidate
                    break
            except ImportError:
                log.debug("Lixeira import fallback failed (%s)", module_name, exc_info=True)

    if abrir_fn is None:
        log.error("Nenhuma funcao de abertura encontrada em ui.lixeira")
        raise AttributeError("Nenhuma funcao de abertura encontrada em ui.lixeira")

    parent = getattr(app, "root", app)
    app_ctx = getattr(app, "app", app)
    window = abrir_fn(parent, app_ctx, *args, **kwargs)

    try:
        setattr(app, "lixeira_win", window)
    except (AttributeError, TypeError):
        log.debug("Unable to attach lixeira_win attribute", exc_info=True)


__all__ = [
    "abrir_lixeira_ui",
    "editar_cliente",
    "excluir_cliente",
    "novo_cliente",
]
