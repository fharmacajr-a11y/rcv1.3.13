# -*- coding: utf-8 -*-
"""INTERNAL: implementação particionada do pipeline de clientes; API pública exposta por pipeline.py."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox
from typing import Any, Mapping

from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.infra.supabase_client import get_supabase_state
from src.core.logger import get_logger
from src.core.storage_key import storage_slug_part
from src.helpers.auth_utils import current_user_id, resolve_org_id
from src.helpers.datetime_utils import now_iso_z
from src.helpers.storage_utils import get_bucket_name
from src.modules.clientes.components.status import apply_status_prefix
from src.modules.clientes.service import excluir_cliente_simples, salvar_cliente
from src.utils.validators import only_digits

LOGGER_NAME = "src.modules.clientes.forms.pipeline"
logger = get_logger(LOGGER_NAME)

DEFAULT_IMPORT_SUBFOLDER = "GERAL"


def _extract_supabase_error(err: Any) -> tuple[str | None, str, str | None]:
    """
    Tenta extrair (code, message, constraint/hint) de respostas do Supabase/PostgREST.
    Retorna message sempre preenchida (fallback em str(err)).
    """

    code: str | None = getattr(err, "code", None)
    constraint: str | None = getattr(err, "constraint", None) or getattr(err, "hint", None)
    message: str | None = getattr(err, "message", None)
    details: str | None = getattr(err, "details", None)
    hint: str | None = getattr(err, "hint", None)

    payloads: list[Mapping[str, Any]] = []
    if isinstance(err, Mapping):
        payloads.append(err)
    if getattr(err, "args", None):
        first = err.args[0]
        if isinstance(first, Mapping):
            payloads.append(first)
        elif isinstance(first, str):
            message = message or first

    for payload in payloads:
        code = code or payload.get("code") or payload.get("status_code")
        message = message or payload.get("message") or payload.get("msg")
        details = details or payload.get("details")
        hint = hint or payload.get("hint")
        constraint = constraint or payload.get("constraint")

    merged_message = message or details or hint or str(err)
    return (str(code) if code else None, merged_message, constraint)


def traduzir_erro_supabase_para_msg_amigavel(err: Any, *, cnpj: str | None = None) -> str:
    """
    Recebe o erro retornado pelo Supabase/PostgREST (exceção ou dict)
    e devolve uma mensagem em português para exibir ao usuário.
    """

    code, raw_message, constraint = _extract_supabase_error(err)
    merged_text = " ".join([p for p in [raw_message, constraint or ""] if p]).lower()

    if (
        code == "23505" or "duplicate key value violates unique constraint" in merged_text
    ) and "uq_clients_cnpj" in merged_text:
        lines = [
            "Já existe um cliente cadastrado com este CNPJ.",
            "Ele pode estar na lista principal ou na Lixeira.",
        ]
        if cnpj:
            lines.append(f"CNPJ em conflito: {cnpj}")
        lines.extend(
            [
                "",
                "Para continuar:",
                "- procure pelo CNPJ na tela principal, ou",
                "- abra a Lixeira de Clientes, busque pelo CNPJ",
                "  e restaure ou apague definitivamente o cadastro antigo.",
            ]
        )
        return "\n".join(lines)

    return raw_message


@dataclass
class UploadCtx:
    app: Any = None
    row: Any = None
    ents: dict[str, Any] = field(default_factory=dict)
    arquivos_selecionados: list[str] | None = None
    win: Any | None = None
    bucket: str | None = None
    client_id: int | None = None
    org_id: str | None = None
    user_id: str | None = None
    created_at: str | None = None
    pasta_local: str | None = None
    parent_win: Any | None = None
    subpasta: str | None = None
    storage_adapter: SupabaseStorageAdapter | None = None
    files: list[tuple[str, str]] = field(default_factory=list)
    src_dir: str | None = None
    busy_dialog: Any | None = None
    falhas: int = 0
    abort: bool = False
    valores: dict[str, Any] = field(default_factory=dict)
    base_local: str | None = None
    finalize_ready: bool = False
    misc: dict[str, Any] = field(default_factory=dict)
    is_new: bool = False


def _extract_status_value(ents: Mapping[str, Any] | None) -> str:
    if not ents:
        return ""
    for key in ("status", "Status do Cliente", "Status"):
        widget = ents.get(key) if isinstance(ents, Mapping) else None
        if widget is None:
            continue
        try:
            raw = widget.get()  # type: ignore[attr-defined]
        except Exception:
            try:
                raw = widget.get("1.0", "end")  # type: ignore[attr-defined]
            except Exception:
                raw = widget
        return (str(raw or "")).strip()
    return ""


def _build_storage_prefix(*parts: str | None) -> str:
    sanitized: list[str] = []
    for part in parts:
        value = storage_slug_part(part)
        if value:
            sanitized.append(value)
    return "/".join(sanitized).strip("/")


def _ask_subpasta(parent: Any) -> str | None:
    """
    Abre o diálogo de subpasta de forma lazy para evitar ciclos de import.
    Retorna o nome da subpasta escolhida ou None se cancelado/indisponível.
    """
    try:
        from src.modules.forms.actions import SubpastaDialog
    except ImportError as exc:
        logger.exception(
            "Erro ao importar SubpastaDialog: %s. Verifique src.modules.forms.actions.",
            exc,
        )
        return None

    dlg = SubpastaDialog(parent, default="")
    parent.wait_window(dlg)
    return getattr(dlg, "result", None)


def _unpack_call(args: tuple, kwargs: dict) -> tuple:
    self = args[0]
    row = args[1] if len(args) > 1 else kwargs.get("row")
    ents = args[2] if len(args) > 2 else kwargs.get("ents")
    arquivos = args[3] if len(args) > 3 else kwargs.get("arquivos_selecionados")
    win = args[4] if len(args) > 4 else kwargs.get("win")
    return self, row, ents, arquivos, win


def _ensure_ctx(self, row, ents, arquivos, win) -> UploadCtx:
    ctx = getattr(self, "_upload_ctx", None)
    if ctx is None:
        ctx = UploadCtx(
            app=self,
            row=row,
            ents=ents or {},
            arquivos_selecionados=list(arquivos or []),
            win=win,
            is_new=not bool(row),
        )
        setattr(self, "_upload_ctx", ctx)
    else:
        ctx.app = self
        ctx.row = row
        ctx.ents = ents or {}
        ctx.arquivos_selecionados = list(arquivos or [])
        ctx.win = win
        try:
            ctx.is_new = not bool(row)
        except Exception:
            ctx.is_new = False

    try:
        forced_id = getattr(self, "_force_client_id_for_upload", None)
        if forced_id is not None:
            ctx.client_id = forced_id
        delattr(self, "_force_client_id_for_upload")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao aplicar client_id forçado no upload: %s", exc)
    try:
        if getattr(self, "_upload_force_is_new", False):
            ctx.is_new = True
        delattr(self, "_upload_force_is_new")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao aplicar flag is_new forçada no upload: %s", exc)
    return ctx


def validate_inputs(*args, **kwargs) -> tuple[tuple, dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx = _ensure_ctx(self, row, ents, arquivos, win)

    state, description = get_supabase_state()
    if state != "online":
        if state == "unstable":
            messagebox.showwarning(
                "Conexão Instável",
                f"A conexão com o Supabase está instável.\n\n"
                f"Detalhes: {description}\n\n"
                f"O cliente será salvo localmente, mas o envio para a nuvem "
                f"não pode ser realizado no momento.\n\n"
                f"Aguarde a estabilização da conexão ou tente novamente mais tarde.",
                parent=win,
            )
        else:
            messagebox.showwarning(
                "Sem Conexão",
                f"O sistema está sem conexão com o Supabase.\n\n"
                f"Detalhes: {description}\n\n"
                f"O cliente será salvo localmente, mas o envio para a nuvem "
                f"não pode ser realizado no momento.\n\n"
                f"Aguarde a reconexão ou tente novamente mais tarde.",
                parent=win,
            )
        logger.warning(
            "Tentativa de envio bloqueada: Estado da nuvem = %s (%s)",
            (state or "unknown").upper(),
            description,
        )
        ctx.abort = True
        return args, kwargs

    valores = {
        "Razão Social": ents["Razão Social"].get().strip(),
        "CNPJ": ents["CNPJ"].get().strip(),
        "Nome": ents["Nome"].get().strip(),
        "WhatsApp": only_digits(ents["WhatsApp"].get().strip()),
        "Observações": ents["Observações"].get("1.0", "end-1c").strip(),
    }
    valores["status"] = _extract_status_value(ents)
    ctx.valores = valores

    return args, kwargs


def prepare_payload(*args, skip_duplicate_prompt: bool = False, **kwargs) -> tuple[tuple, dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx = getattr(self, "_upload_ctx", None)
    if not ctx or ctx.abort:
        return args, kwargs

    valores = ctx.valores or {
        "Razão Social": ents["Razão Social"].get().strip(),
        "CNPJ": ents["CNPJ"].get().strip(),
        "Nome": ents["Nome"].get().strip(),
        "WhatsApp": only_digits(ents["WhatsApp"].get().strip()),
        "Observações": ents["Observações"].get("1.0", "end-1c").strip(),
        "status": _extract_status_value(ents),
    }

    status_found = False
    status = ""
    for key in ("status", "Status do Cliente", "Status"):
        if key in valores:
            status = (valores.pop(key, "") or "").strip()
            status_found = True
            break
    if not status_found:
        status = _extract_status_value(ents)

    obs_key = None
    for candidate in ("Observações", "Observacoes", "observacoes", "Obs", "obs"):
        if candidate in valores:
            obs_key = candidate
            break
    if obs_key is None:
        obs_key = "Observações"
    obs_raw = valores.get(obs_key, "")
    valores[obs_key] = apply_status_prefix(obs_raw, status)

    try:
        client_id, pasta_local = salvar_cliente(row, valores)
    except Exception as exc:
        cnpj_val = None
        try:
            cnpj_val = valores.get("CNPJ") or valores.get("cnpj")
        except Exception as inner_exc:  # noqa: BLE001
            logger.debug("Falha ao extrair CNPJ para mensagem de erro: %s", inner_exc)
        msg_amigavel = traduzir_erro_supabase_para_msg_amigavel(exc, cnpj=cnpj_val)
        try:
            if win and hasattr(win, "winfo_exists") and win.winfo_exists():
                messagebox.showerror("Erro ao salvar cliente no DB", msg_amigavel, parent=win)
            else:
                messagebox.showerror("Erro ao salvar cliente no DB", msg_amigavel)
        except Exception:
            messagebox.showerror("Erro ao salvar cliente no DB", msg_amigavel)
        logger.exception("Falha ao salvar cliente no DB: %s", exc)
        ctx.abort = True
        return args, kwargs

    ctx.client_id = client_id
    ctx.pasta_local = pasta_local
    ctx.valores = valores

    ctx.user_id = current_user_id()
    ctx.created_at = now_iso_z()

    try:
        ctx.org_id = resolve_org_id()
    except Exception as exc:
        messagebox.showerror("Erro ao resolver organização", str(exc))
        logger.exception("Falha ao resolver org_id: %s", exc)
        ctx.abort = True
        return args, kwargs

    ctx.bucket = get_bucket_name()
    logger.info("Bucket em uso: %s", ctx.bucket)

    ctx.storage_adapter = SupabaseStorageAdapter(bucket=ctx.bucket)

    parent_win = win if (win and hasattr(win, "winfo_exists") and win.winfo_exists()) else self
    ctx.parent_win = parent_win

    dlg = _ask_subpasta(parent_win)
    cancelled = False
    subpasta_val: str | None = None
    if dlg is None:
        cancelled = True
    elif hasattr(dlg, "cancelled"):
        cancelled = bool(getattr(dlg, "cancelled", False))
        subpasta_val = getattr(dlg, "result", None)
    elif isinstance(dlg, str):
        subpasta_val = dlg
        cancelled = dlg is None
    else:
        try:
            subpasta_val = dlg.result  # type: ignore[attr-defined]
            cancelled = False if subpasta_val is not None else True
        except Exception:
            cancelled = True

    if cancelled or subpasta_val is None:
        if ctx.is_new and ctx.client_id:
            try:
                excluir_cliente_simples(int(ctx.client_id))
                logger.info("Rollback de cliente recém-criado id=%s após cancelamento da subpasta", ctx.client_id)
            except Exception:
                logger.exception(
                    "Falha ao reverter criação de cliente após cancelamento da subpasta (id=%s)", ctx.client_id
                )
        ctx.abort = True
        return args, kwargs

    ctx.subpasta = subpasta_val or ""

    prefix_parts = [ctx.org_id, ctx.client_id, DEFAULT_IMPORT_SUBFOLDER]
    if ctx.subpasta:
        prefix_parts.append(ctx.subpasta)
    ctx.misc["storage_prefix"] = _build_storage_prefix(*prefix_parts)

    src = filedialog.askdirectory(
        parent=parent_win,
        title=(
            f"Escolha a PASTA para importar (irá para "
            f"'{DEFAULT_IMPORT_SUBFOLDER}{'/' + ctx.subpasta if ctx.subpasta else ''}')"
        ),
    )
    ctx.src_dir = src or ""

    files: list[tuple[str, str]] = []
    for f in ctx.arquivos_selecionados or []:
        files.append((f, os.path.basename(f)))

    if src:
        for root, _dirs, flist in os.walk(src):
            for f in flist:
                name = f.lower()
                if name in {"desktop.ini", ".ds_store", "thumbs.db"}:
                    continue
                local = os.path.join(root, f)
                rel = os.path.relpath(local, src).replace("\\", "/")
                files.append((local, rel))

    ctx.files = files

    if not src and not (ctx.arquivos_selecionados or []):
        messagebox.showinfo("Nada a enviar", "Cliente salvo, mas nenhum arquivo foi selecionado.")
        try:
            self.carregar()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao recarregar tela apos salvar cliente sem arquivos: %s", exc)
        ctx.abort = True
        return args, kwargs

    return args, kwargs


__all__ = [
    "DEFAULT_IMPORT_SUBFOLDER",
    "UploadCtx",
    "traduzir_erro_supabase_para_msg_amigavel",
    "validate_inputs",
    "prepare_payload",
    "_unpack_call",
    "_ensure_ctx",
]
