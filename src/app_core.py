# -*- coding: utf-8 -*-
"""High-level actions triggered by the GUI (CRUD, folders, trash integration)."""

from __future__ import annotations

import importlib
import logging
import os
from tkinter import messagebox
from typing import Any, Sequence, Tuple

from src.config.paths import CLOUD_ONLY
from src.modules.clientes.service import get_cliente_by_id, mover_cliente_para_lixeira

try:
    from src.modules.lixeira import abrir_lixeira as _module_abrir_lixeira, refresh_if_open as _module_refresh_if_open
except Exception:
    _module_abrir_lixeira = None
    _module_refresh_if_open = None

# ------------------------------------------------------------
# Modo "somente nuvem" (não cria nada em disco local)
# defina RC_NO_LOCAL_FS=1 no .env para ativar
# ------------------------------------------------------------
NO_FS = os.getenv("RC_NO_LOCAL_FS") == "1"

# Utilitários que podem ser usados quando o FS local estiver habilitado
try:
    from src.config.paths import DOCS_DIR

    from .app_utils import safe_base_from_fields
except Exception:  # best-effort para manter compatibilidade
    safe_base_from_fields = None  # type: ignore[assignment]
    DOCS_DIR = os.getcwd()  # type: ignore[assignment]

log = logging.getLogger(__name__)

MARKER_NAME = ".rc_client_id"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_messagebox(method: str, *args: Any, **kwargs: Any) -> Any:
    """Invoca messagebox.<method> em modo best-effort, ignorando falhas em ambientes sem GUI."""
    func = getattr(messagebox, method, None)
    if callable(func):
        try:
            return func(*args, **kwargs)
        except Exception:
            log.debug("messagebox.%s failed", method, exc_info=True)
    return None


def _resolve_cliente_row(pk: int) -> Tuple[Any, ...] | None:
    """Carrega do Supabase os dados necessários para popular o formulário de cliente."""
    try:
        cliente = get_cliente_by_id(pk)
    except Exception:
        log.exception("Failed to resolve client %s from Supabase", pk)
        return None

    if cliente is None:
        return None

    return (
        cliente.id,
        cliente.razao_social,
        cliente.cnpj,
        cliente.nome,
        cliente.numero,
        cliente.obs,
        cliente.ultima_alteracao,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def novo_cliente(app: Any) -> None:
    """Abre o formulário para cadastro de um novo cliente."""
    log.info("Opening form for new client")

    from src.modules.clientes.forms.client_form import form_cliente

    form_cliente(app)


def editar_cliente(app: Any, pk: int) -> None:
    """Abre o formulário de edição para o cliente informado."""
    log.info("Opening edit form for client id=%s", pk)
    from src.modules.clientes.forms.client_form import form_cliente

    row = _resolve_cliente_row(pk)
    if row:
        form_cliente(app, row)
    else:
        _safe_messagebox("showerror", "Cliente", "Registro não encontrado no Supabase.")


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
        except Exception:
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
    except Exception as exc:
        _safe_messagebox("showerror", "Erro ao excluir", f"Falha ao enviar para a Lixeira: {exc}")
        log.exception("Failed to soft-delete client %s", label_cli)
        return

    try:
        app.carregar()
    except Exception:
        log.exception("Failed to refresh client list after soft delete")

    if _module_refresh_if_open is not None:
        try:
            _module_refresh_if_open()
        except Exception:
            log.debug("Lixeira refresh skipped", exc_info=True)

    _safe_messagebox("showinfo", "Lixeira", f"Cliente {label_cli} enviado para a Lixeira.")
    log.info("Cliente %s enviado para a Lixeira com sucesso", label_cli)


# ---------------------------------------------------------------------------
# Pastas locais (desligadas quando NO_FS)
# ---------------------------------------------------------------------------
def dir_base_cliente_from_pk(pk: int) -> str:
    if NO_FS:
        return ""

    try:
        from src.core.services.path_resolver import resolve_unique_path

        path, location = resolve_unique_path(pk)
        if path:
            log.debug(
                "Resolved folder via path_resolver: pk=%s path=%s (%s)",
                pk,
                path,
                location,
            )
            return path
    except Exception:
        log.debug("resolve_unique_path not available or failed", exc_info=True)

    try:
        from src.core.db_manager import get_cliente_by_id

        c = get_cliente_by_id(pk)
    except Exception:
        c = None

    numero = getattr(c, "numero", "") or ""
    cnpj = getattr(c, "cnpj", "") or ""
    razao = getattr(c, "razao_social", "") or ""
    base_name = safe_base_from_fields(cnpj, numero, razao, pk) if callable(safe_base_from_fields) else str(pk)
    return os.path.join(str(DOCS_DIR), base_name)


def _ensure_live_folder_ready(pk: int) -> str:
    if NO_FS:
        return ""

    path = dir_base_cliente_from_pk(pk)
    try:
        if not CLOUD_ONLY:
            os.makedirs(path, exist_ok=True)
        try:
            from pathlib import Path

            from src.utils.file_utils import ensure_subpastas, write_marker
            from src.utils.subpastas_config import load_subpastas_config

            try:
                subpastas, _extras = load_subpastas_config()
            except Exception:
                subpastas = []
            ensure_subpastas(path, subpastas=subpastas)

            marker_path = Path(path) / MARKER_NAME
            content_ok = False
            if marker_path.is_file():
                try:
                    content_ok = marker_path.read_text(encoding="utf-8").strip() == str(pk)
                except Exception:
                    content_ok = False
            if not content_ok:
                if not CLOUD_ONLY:
                    write_marker(path, pk)
        except Exception:
            log.debug("ensure_subpastas/write_marker skipped", exc_info=True)
    except Exception:
        log.exception("Failed to prepare folder for client %s", pk)
    return path


def abrir_pasta_cliente(pk: int) -> str | None:
    if NO_FS:
        return None
    return _ensure_live_folder_ready(pk)


def abrir_pasta(app: Any, pk: int) -> None:
    """Abre o explorador de arquivos apontando para a pasta local do cliente."""
    if NO_FS:
        _safe_messagebox(
            "showinfo",
            "Somente Nuvem",
            (
                "Este app está em modo somente nuvem.\n"
                "Use o botão 'Subpastas (Supabase)' para navegar e baixar arquivos do Supabase."
            ),
        )
        return

    path = _ensure_live_folder_ready(pk)
    log.info("Opening folder for client %s: %s", pk, path)
    try:
        # Guardrail adicional: mesmo em modo local, verificar se startfile está disponível
        from src.utils.helpers import check_cloud_only_block

        if check_cloud_only_block("Abrir pasta do cliente"):
            return
        os.startfile(path)  # type: ignore[attr-defined]  # nosec B606 - abre pasta local controlada pelo app
    except Exception:
        log.exception("Failed to open file explorer for %s", path)


def open_client_local_subfolders(app: Any, pk: int) -> None:
    """Abre a UI de subpastas locais configuradas para o cliente."""
    if NO_FS:
        _safe_messagebox(
            "showinfo",
            "Subpastas",
            "Navegação de pastas locais desativada.\nUse 'Subpastas (Supabase)' na tela principal.",
        )
        return

    path = _ensure_live_folder_ready(pk)
    try:
        from src.modules.clientes.forms import open_subpastas_dialog
        from src.utils.subpastas_config import load_subpastas_config

        subpastas, extras = load_subpastas_config()
    except Exception:
        log.exception("Failed to load subfolders configuration; using empty lists")
        subpastas, extras = [], []

    open_subpastas_dialog(app, path, subpastas, extras)


def ver_subpastas(app: Any, pk: int) -> None:
    """DEPRECATED: mantenha compatibilidade com o nome antigo."""
    open_client_local_subfolders(app, pk)


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
        except Exception:
            log.debug("Primary lixeira package import failed", exc_info=True)

    if abrir_fn is None:
        for module_name in ("src.modules.lixeira", "src.ui.lixeira", "ui.lixeira"):
            try:
                module = importlib.import_module(module_name)
                candidate = getattr(module, "abrir_lixeira", None)
                if callable(candidate):
                    abrir_fn = candidate
                    break
            except Exception:
                log.debug("Lixeira import fallback failed (%s)", module_name, exc_info=True)

    if abrir_fn is None:
        log.error("Nenhuma funcao de abertura encontrada em ui.lixeira")
        raise AttributeError("Nenhuma funcao de abertura encontrada em ui.lixeira")

    parent = getattr(app, "root", app)
    app_ctx = getattr(app, "app", app)
    window = abrir_fn(parent, app_ctx, *args, **kwargs)

    try:
        setattr(app, "lixeira_win", window)
    except Exception:
        log.debug("Unable to attach lixeira_win attribute", exc_info=True)


__all__ = [
    "abrir_lixeira_ui",
    "abrir_pasta",
    "abrir_pasta_cliente",
    "dir_base_cliente_from_pk",
    "editar_cliente",
    "excluir_cliente",
    "novo_cliente",
    "open_client_local_subfolders",
    "ver_subpastas",
]
