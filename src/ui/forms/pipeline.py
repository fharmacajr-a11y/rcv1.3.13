# -*- coding: utf-8 -*-
"""Pipeline helpers reais para salvar_e_upload_docs."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# Garantir que .docx tenha MIME correto em qualquer SO
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx",
)

from adapters.storage.api import delete_file as storage_delete_file
from adapters.storage.api import upload_file as storage_upload_file
from adapters.storage.api import using_storage_backend
from adapters.storage.supabase_storage import SupabaseStorageAdapter
from infra.supabase_client import exec_postgrest, get_supabase_state, supabase
from src.config.paths import CLOUD_ONLY
from src.core.logger import get_logger
from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm
from src.utils.typing_helpers import is_optional_str
from src.core.db_manager import find_cliente_by_cnpj_norm
from src.core.services.clientes_service import checar_duplicatas_info, salvar_cliente
from src.core.storage_key import make_storage_key, storage_slug_part

logger = get_logger(__name__)

if TYPE_CHECKING:
    # apenas para type-checkers; não roda em runtime
    pass

DEFAULT_IMPORT_SUBFOLDER = "GERAL"


@dataclass
class UploadCtx:
    app: Any = None
    row: Any = None
    ents: Dict[str, Any] = field(default_factory=dict)
    arquivos_selecionados: Optional[List[str]] = None
    win: Optional[Any] = None
    bucket: Optional[str] = None
    client_id: Optional[int] = None
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    pasta_local: Optional[str] = None
    parent_win: Optional[Any] = None
    subpasta: Optional[str] = None
    storage_adapter: Optional[SupabaseStorageAdapter] = None
    files: List[tuple[str, str]] = field(default_factory=list)
    src_dir: Optional[str] = None
    busy_dialog: Optional[Any] = None
    falhas: int = 0
    abort: bool = False
    valores: Dict[str, Any] = field(default_factory=dict)
    base_local: Optional[str] = None
    finalize_ready: bool = False
    misc: Dict[str, Any] = field(default_factory=dict)


def _only_digits(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _get_bucket_name(default_env: str | None = None) -> str:
    return (default_env or os.getenv("SUPABASE_BUCKET") or "rc-docs").strip()


def _build_storage_prefix(*parts: str | None) -> str:
    sanitized: list[str] = []
    for part in parts:
        value = storage_slug_part(part)
        if value:
            sanitized.append(value)
    return "/".join(sanitized).strip("/")


def _ask_subpasta(parent: Any) -> Optional[str]:
    """
    Abre o diálogo de subpasta de forma lazy para evitar ciclos de import.
    Retorna o nome da subpasta escolhida ou None se cancelado/indisponível.
    """
    try:
        # Import correto do SubpastaDialog
        from src.ui.forms.actions import SubpastaDialog
    except ImportError as exc:
        logger.exception(
            "Erro ao importar SubpastaDialog: %s. Verifique src.ui.forms.actions.",
            exc,
        )
        return None

    dlg = SubpastaDialog(parent, default="")
    parent.wait_window(dlg)
    return dlg.result


def _current_user_id() -> Optional[str]:
    try:
        resp = supabase.auth.get_user()
        user = getattr(resp, "user", None)
        if user and getattr(user, "id", None):
            return user.id
        if isinstance(resp, dict):
            u = resp.get("user") or (resp.get("data") or {}).get("user") or {}
            return u.get("id") or u.get("uid")
    except Exception:
        pass
    return None


def _now_iso_z() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _resolve_org_id() -> str:
    uid = _current_user_id()
    fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip()
    if not uid and not fallback:
        raise RuntimeError("Usuário não autenticado e SUPABASE_DEFAULT_ORG não definido.")
    try:
        if uid:
            res = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1))
            data = getattr(res, "data", None) or []
            if data:
                return data[0]["org_id"]
    except Exception:
        pass
    if fallback:
        return fallback
    raise RuntimeError("Não foi possível resolver a organização do usuário.")


def _classify_storage_error(exc: Exception) -> str:
    s = str(exc).lower()
    if "invalidkey" in s or "invalid key" in s:
        return "invalid_key"
    if "row-level security" in s or "rls" in s or "42501" in s or "403" in s:
        return "rls"
    if "already exists" in s or "keyalreadyexists" in s or "409" in s:
        return "exists"
    return "other"


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
        )
        setattr(self, "_upload_ctx", ctx)
    else:
        ctx.app = self
        ctx.row = row
        ctx.ents = ents or {}
        ctx.arquivos_selecionados = list(arquivos or [])
        ctx.win = win
    return ctx


def _cleanup_ctx(self) -> None:
    if hasattr(self, "_upload_ctx"):
        delattr(self, "_upload_ctx")


def validate_inputs(*args, **kwargs) -> Tuple[tuple, Dict[str, Any]]:
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
            state.upper(),
            description,
        )
        ctx.abort = True
        return args, kwargs

    valores = {
        "Razão Social": ents["Razão Social"].get().strip(),
        "CNPJ": ents["CNPJ"].get().strip(),
        "Nome": ents["Nome"].get().strip(),
        "WhatsApp": _only_digits(ents["WhatsApp"].get().strip()),
        "Observações": ents["Observações"].get("1.0", "end-1c").strip(),
    }
    ctx.valores = valores

    try:
        current_id = None
        try:
            current_id = int(row[0]) if row else None
        except Exception:
            current_id = None

        cnpj_norm = normalize_cnpj_norm(valores.get("CNPJ"))
        if cnpj_norm:
            dup = find_cliente_by_cnpj_norm(cnpj_norm, exclude_id=current_id)
            if dup:
                messagebox.showwarning(
                    "CNPJ duplicado",
                    (
                        "CNPJ já cadastrado para o cliente ID "
                        f"{getattr(dup, 'id', '?')} — "
                        f"{getattr(dup, 'razao_social', '') or '-'}\n"
                        f"CNPJ registrado: {getattr(dup, 'cnpj', '') or '-'}"
                    ),
                    parent=win,
                )
                ctx.abort = True
                return args, kwargs

        # Type narrowing: valores.get() retorna Unknown | None, validamos antes
        cnpj_val = valores.get("CNPJ")
        razao_val = valores.get("Razão Social")
        numero_val = valores.get("WhatsApp")
        nome_val = valores.get("Nome")

        info = checar_duplicatas_info(
            cnpj=cnpj_val if is_optional_str(cnpj_val) else "",
            razao=razao_val if is_optional_str(razao_val) else "",
            numero=numero_val if is_optional_str(numero_val) else "",
            nome=nome_val if is_optional_str(nome_val) else "",
            exclude_id=current_id,
        )

        razao_conflicts_raw = info.get("razao_conflicts")
        razao_conflicts: list[Any] = razao_conflicts_raw if isinstance(razao_conflicts_raw, list) else []
        if razao_conflicts:
            lines: list[str] = []
            for idx, cliente in enumerate(razao_conflicts, start=1):
                if idx > 3:
                    break
                lines.append(
                    f"- ID {getattr(cliente, 'id', '?')} — {getattr(cliente, 'razao_social', '') or '-'} (CNPJ: {getattr(cliente, 'cnpj', '') or '-'})"
                )
            remaining = max(0, len(razao_conflicts) - len(lines))
            if remaining:
                lines.append(f"- ... e mais {remaining} registro(s)")

            header = "Existe outro cliente com a mesma Razão Social mas CNPJ diferente. Deseja continuar?\n\n"
            msg = header + "\n".join(lines)
            if not messagebox.askokcancel(
                "Razão Social repetida",
                msg,
                parent=win,
            ):
                ctx.abort = True
                return args, kwargs
    except Exception:
        pass

    return args, kwargs


def prepare_payload(*args, **kwargs) -> Tuple[tuple, Dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx = getattr(self, "_upload_ctx", None)
    if not ctx or ctx.abort:
        return args, kwargs

    valores = ctx.valores or {
        "Razão Social": ents["Razão Social"].get().strip(),
        "CNPJ": ents["CNPJ"].get().strip(),
        "Nome": ents["Nome"].get().strip(),
        "WhatsApp": _only_digits(ents["WhatsApp"].get().strip()),
        "Observações": ents["Observações"].get("1.0", "end-1c").strip(),
    }

    try:
        client_id, pasta_local = salvar_cliente(row, valores)
    except Exception as exc:
        messagebox.showerror("Erro ao salvar cliente no DB", str(exc))
        logger.exception("Falha ao salvar cliente no DB: %s", exc)
        ctx.abort = True
        return args, kwargs

    ctx.client_id = client_id
    ctx.pasta_local = pasta_local
    ctx.valores = valores

    ctx.user_id = _current_user_id()
    ctx.created_at = _now_iso_z()

    try:
        ctx.org_id = _resolve_org_id()
    except Exception as exc:
        messagebox.showerror("Erro ao resolver organização", str(exc))
        logger.exception("Falha ao resolver org_id: %s", exc)
        ctx.abort = True
        return args, kwargs

    ctx.bucket = _get_bucket_name()
    logger.info("Bucket em uso: %s", ctx.bucket)

    ctx.storage_adapter = SupabaseStorageAdapter(bucket=ctx.bucket)

    parent_win = win if (win and hasattr(win, "winfo_exists") and win.winfo_exists()) else self
    ctx.parent_win = parent_win

    subpasta = _ask_subpasta(parent_win)
    if subpasta is None:
        ctx.abort = True
        return args, kwargs
    ctx.subpasta = subpasta

    prefix_parts = [ctx.org_id, ctx.client_id, DEFAULT_IMPORT_SUBFOLDER]
    if ctx.subpasta:
        prefix_parts.append(ctx.subpasta)
    ctx.misc["storage_prefix"] = _build_storage_prefix(*prefix_parts)

    src = filedialog.askdirectory(
        parent=parent_win,
        title=(f"Escolha a PASTA para importar (irá para '{DEFAULT_IMPORT_SUBFOLDER}{'/' + ctx.subpasta if ctx.subpasta else ''}')"),
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
        except Exception:
            pass
        ctx.abort = True
        return args, kwargs

    return args, kwargs


def perform_uploads(*args, **kwargs) -> Tuple[tuple, Dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx = getattr(self, "_upload_ctx", None)
    if not ctx or ctx.abort:
        return args, kwargs

    parent_win = ctx.parent_win or self

    from src.ui.forms import actions as actions_module

    BusyDialog = actions_module.BusyDialog

    busy = BusyDialog(parent_win, text="Enviando arquivos para o Supabase…")
    busy.set_total(len(ctx.files) if ctx.files else 1)
    ctx.busy_dialog = busy

    base_local = (
        os.path.join(
            ctx.pasta_local,
            DEFAULT_IMPORT_SUBFOLDER,
            ctx.subpasta,
        )
        if ctx.subpasta
        else os.path.join(ctx.pasta_local, DEFAULT_IMPORT_SUBFOLDER)
    )
    ctx.base_local = base_local

    def worker():
        falhas = 0
        arquivos_falhados = []  # Track quais arquivos falharam

        if ctx.src_dir:
            base_local_inner = (
                os.path.join(ctx.pasta_local, DEFAULT_IMPORT_SUBFOLDER, ctx.subpasta)
                if ctx.subpasta
                else os.path.join(ctx.pasta_local, DEFAULT_IMPORT_SUBFOLDER)
            )
            try:
                if not CLOUD_ONLY:
                    os.makedirs(base_local_inner, exist_ok=True)
                for lp, rel in ctx.files:
                    dest = os.path.join(base_local_inner, rel) if ctx.src_dir and rel else os.path.join(base_local_inner, os.path.basename(lp))
                    if not CLOUD_ONLY:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                    try:
                        shutil.copy2(lp, dest)
                    except Exception:
                        pass
            except Exception as exc:
                logger.error("Falha ao copiar local: %s", exc)

        def _after_step(msg: Optional[str] = None):
            if msg:
                busy.set_text(msg)
            busy.step()

        with using_storage_backend(ctx.storage_adapter):
            base_parts = [ctx.org_id, ctx.client_id, DEFAULT_IMPORT_SUBFOLDER]
            if ctx.subpasta:
                base_parts.append(ctx.subpasta)

            for local_path, rel in ctx.files:
                try:
                    rel_path = (rel or "").replace("\\", "/").strip("/")
                    segments = [seg for seg in rel_path.split("/") if seg] if rel_path else []
                    if segments:
                        filename_original = segments[-1]
                        dir_segments = segments[:-1]
                    else:
                        filename_original = os.path.basename(local_path)
                        dir_segments = []

                    key_parts = base_parts + dir_segments
                    storage_path = make_storage_key(*key_parts, filename=filename_original)
                    logger.info(
                        "Upload Storage: original=%r -> key=%s (bucket=%s)",
                        rel or filename_original,
                        storage_path,
                        ctx.bucket,
                    )

                    data = Path(local_path).read_bytes()
                    sanitized_filename = storage_path.split("/")[-1]
                    content_type = mimetypes.guess_type(sanitized_filename)[0] or "application/octet-stream"
                    storage_delete_file(storage_path)
                    storage_upload_file(data, storage_path, content_type)

                    size_bytes = len(data)
                    sha256_hash = hashlib.sha256(data).hexdigest()

                    doc = exec_postgrest(
                        supabase.table("documents").insert(
                            {
                                "client_id": ctx.client_id,
                                "title": os.path.basename(local_path),
                                "kind": os.path.splitext(local_path)[1].lstrip("."),
                                "current_version": None,
                            }
                        )
                    )
                    document_id = doc.data[0]["id"]

                    ver = exec_postgrest(
                        supabase.table("document_versions").insert(
                            {
                                "document_id": document_id,
                                "path": storage_path,
                                "size_bytes": size_bytes,
                                "sha256": sha256_hash,
                                "uploaded_by": ctx.user_id or "unknown",
                                "created_at": ctx.created_at,
                            }
                        )
                    )
                    version_id = ver.data[0]["id"]
                    exec_postgrest(supabase.table("documents").update({"current_version": version_id}).eq("id", document_id))

                    logger.info("Upload OK: %s", storage_path)
                except Exception as exc:
                    falhas += 1
                    arquivo_nome = os.path.basename(local_path)
                    arquivos_falhados.append(arquivo_nome)
                    kind = _classify_storage_error(exc)
                    if kind == "invalid_key":
                        logger.error(
                            "Nome/caminho inválido: %s | arquivo: %s",
                            storage_path,
                            arquivo_nome,
                        )
                    elif kind == "rls":
                        logger.error(
                            "Permissão negada (RLS) no upload de %s | arquivo: %s",
                            storage_path,
                            arquivo_nome,
                        )
                    elif kind == "exists":
                        logger.warning(
                            "Chave já existia: %s | arquivo: %s",
                            storage_path,
                            arquivo_nome,
                        )
                    else:
                        logger.exception(
                            "Falha upload/registro (%s) | arquivo: %s: %s",
                            local_path,
                            arquivo_nome,
                            exc,
                        )
                finally:
                    self.after(0, _after_step)

        ctx.falhas = falhas
        ctx.misc["arquivos_falhados"] = arquivos_falhados
        ctx.finalize_ready = True
        self.after(
            0,
            lambda: finalize_state(self, row, ents, arquivos, win, ctx_override=ctx),
        )

    threading.Thread(target=worker, daemon=True).start()
    return args, kwargs


def finalize_state(*args, ctx_override: Optional[UploadCtx] = None, **kwargs) -> Tuple[tuple, Dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx = ctx_override or getattr(self, "_upload_ctx", None)
    if not ctx:
        return args, kwargs
    if ctx.abort and not ctx.finalize_ready:
        _cleanup_ctx(self)
        return args, kwargs
    if not ctx.finalize_ready:
        return args, kwargs

    try:
        if ctx.busy_dialog:
            ctx.busy_dialog.close()
    except Exception:
        pass

    # Mensagem de sucesso com informação do prefixo
    prefix_info = ""
    if ctx.misc.get("storage_prefix"):
        prefix_info = f"\\n\\nPrefixo no Storage: {ctx.misc['storage_prefix']}"

    # Lista de arquivos que falharam
    arquivos_falhados = ctx.misc.get("arquivos_falhados", [])
    falhas_info = ""
    if arquivos_falhados:
        # Limitar a 10 arquivos para não poluir a mensagem
        lista = arquivos_falhados[:10]
        falhas_info = "\\n\\nArquivos que falharam:\\n- " + "\\n- ".join(lista)
        if len(arquivos_falhados) > 10:
            falhas_info += f"\\n... e mais {len(arquivos_falhados) - 10} arquivo(s)"
        logger.warning("Arquivos que falharam no upload: %s", ", ".join(arquivos_falhados))

    msg = (
        f"Cliente salvo e documentos enviados com sucesso!{prefix_info}"
        if ctx.falhas == 0
        else f"Cliente salvo com {ctx.falhas} falha(s) no envio de arquivos.{falhas_info}{prefix_info}"
    )

    try:
        messagebox.showinfo("Sucesso", msg, parent=ctx.parent_win)
    except Exception:
        pass

    try:
        if ctx.win and hasattr(ctx.win, "destroy"):
            ctx.win.destroy()
    except Exception:
        pass

    try:
        self.carregar()
    except Exception:
        pass

    _cleanup_ctx(self)
    return args, kwargs
