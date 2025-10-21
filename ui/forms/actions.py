from __future__ import annotations
from config.paths import CLOUD_ONLY

# ui/forms/actions.py

import os
import re
import shutil
import logging
import threading
import mimetypes
import hashlib
import datetime
import unicodedata
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from dotenv import load_dotenv
from utils.resource_path import resource_path
from adapters.storage.api import (
    delete_file as storage_delete_file,
    download_file as storage_download_file,
    list_files as storage_list_files,
    upload_file as storage_upload_file,
    using_storage_backend,
)
from adapters.storage.supabase_storage import SupabaseStorageAdapter
from infra.supabase_client import (
    exec_postgrest,
    get_supabase_state,
    is_really_online,
    is_supabase_online,
    supabase,
)
from ui.forms.pipeline import (
    finalize_state,
    perform_uploads,
    prepare_payload,
    validate_inputs,
)

load_dotenv()

# Phase 1: shared helpers with defensive fallbacks
try:
    from utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover

    def _sha256(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()


try:
    from utils.validators import only_digits as _only_digits
except Exception:  # pragma: no cover

    def _only_digits(value: str | None) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())


try:
    from ui import center_on_parent
except Exception:  # pragma: no cover
    try:
        from ui.utils import center_on_parent
    except Exception:  # pragma: no cover

        def center_on_parent(win, parent=None, pad=0):
            return win


from core.services.clientes_service import salvar_cliente, checar_duplicatas_info
from utils.file_utils import list_and_classify_pdfs, find_cartao_cnpj_pdf
from utils.pdf_reader import read_pdf_text
from utils.text_utils import extract_company_fields

log = logging.getLogger(__name__)

# Onde os uploads “de pasta inteira” vão parar
DEFAULT_IMPORT_SUBFOLDER = "GERAL"


# -----------------------------------------------------------------------------
# utils locais
# -----------------------------------------------------------------------------


def _now_iso_z() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _get_bucket_name(default_env: str | None = None) -> str:
    return (default_env or os.getenv("SUPABASE_BUCKET") or "rc-docs").strip()


def _current_user_id() -> Optional[str]:
    try:
        resp = supabase.auth.get_user()
        u = getattr(resp, "user", None)
        if u and getattr(u, "id", None):
            return u.id
        if isinstance(resp, dict):
            u = resp.get("user") or (resp.get("data") or {}).get("user") or {}
            return u.get("id") or u.get("uid")
    except Exception:
        pass
    return None


def _resolve_org_id() -> str:
    uid = _current_user_id()
    fallback = (os.getenv("SUPABASE_DEFAULT_ORG") or "").strip()
    if not uid and not fallback:
        raise RuntimeError(
            "Usuário não autenticado e SUPABASE_DEFAULT_ORG não definido."
        )
    try:
        if uid:
            res = exec_postgrest(
                supabase.table("memberships")
                .select("org_id")
                .eq("user_id", uid)
                .limit(1)
            )
            data = getattr(res, "data", None) or []
            if data:
                return data[0]["org_id"]
    except Exception:
        pass
    if fallback:
        return fallback
    raise RuntimeError("Não foi possível resolver a organização do usuário.")


def _sanitize_key_component(s: str | None) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace("\\", "/").replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9._/-]", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-").strip(".")
    return s


def _build_storage_path(*parts: str) -> str:
    cleaned = [_sanitize_key_component(str(p)) for p in parts if str(p)]
    return re.sub(r"/+", "/", "/".join(cleaned)).strip("/")


# -----------------------------------------------------------------------------
# Telinha de carregamento
# -----------------------------------------------------------------------------
class BusyDialog(tk.Toplevel):
    """Progress dialog. Suporta modo indeterminado e determinado (com %)."""

    def __init__(self, parent: tk.Misc, text: str = "Processando…"):
        super().__init__(parent)
        self.withdraw()
        self.title("Aguarde…")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # não fecha
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        self._lbl = ttk.Label(body, text=text, anchor="center", justify="center")
        self._lbl.pack(pady=(0, 8), fill="x")

        self._pb = ttk.Progressbar(body, mode="indeterminate", length=280, maximum=100)
        self._pb.pack(fill="x")

        # centraliza sobre o parent
        try:
            self.update_idletasks()
            center_on_parent(self, parent)
        except Exception:
            pass

        self.deiconify()
        self._pb.start(12)
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(50, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        self.update()

        # estado para modo determinado
        self._det_total = None
        self._det_value = 0

    def set_text(self, txt: str) -> None:
        try:
            self._lbl.configure(text=txt)
            self.update_idletasks()
        except Exception:
            pass

    def set_total(self, total: int) -> None:
        """Troca para modo determinado com 'total' passos."""
        try:
            self._det_total = max(int(total), 1)
            self._det_value = 0
            self._pb.stop()
            self._pb.configure(mode="determinate", maximum=self._det_total, value=0)
            self.update_idletasks()
        except Exception:
            pass

    def step(self, inc: int = 1) -> None:
        try:
            if self._det_total:
                self._det_value = min(self._det_total, self._det_value + inc)
                self._pb.configure(value=self._det_value)
            self.update_idletasks()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self._pb.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Diálogo de subpasta (custom, com ícone e exemplos)
# -----------------------------------------------------------------------------
class SubpastaDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, default: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.title("Subpasta em GERAL")
        self.transient(parent)
        self.resizable(False, False)
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(
            frm,
            text=f"Digite o nome da subpasta (ou deixe vazio para usar só '{DEFAULT_IMPORT_SUBFOLDER}/').",
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            frm,
            text="Ex.: SIFAP, VISA, Farmacia_Popular, Auditoria",
            foreground="#6c757d",
        ).pack(anchor="w")

        self.var = tk.StringVar(value=default or "")
        ent = ttk.Entry(frm, textvariable=self.var, width=40)
        ent.pack(fill="x", pady=(8, 10))
        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="OK", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self._cancel).pack(
            side="left", padx=4
        )

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

        # centraliza
        try:
            self.update_idletasks()
            center_on_parent(self, parent)
        except Exception:
            pass

        self.deiconify()
        self.grab_set()
        ent.focus_force()

        self.result: Optional[str] = None

    def _ok(self):
        raw = (self.var.get() or "").strip()
        self.result = _sanitize_key_component(raw) if raw else ""
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


def _ask_subpasta_nome(parent: tk.Misc, default: str = "") -> Optional[str]:
    dlg = SubpastaDialog(parent, default=default)
    parent.wait_window(dlg)
    return dlg.result


# -----------------------------------------------------------------------------
# Preenchimento via Cartão CNPJ
# -----------------------------------------------------------------------------
def preencher_via_pasta(ents: dict) -> None:
    base = filedialog.askdirectory(
        title="Escolha a pasta do cliente (com o Cartão CNPJ)"
    )
    if not base:
        return

    docs = list_and_classify_pdfs(base)
    cnpj = razao = None
    for d in docs:
        if d.get("type") == "cnpj_card":
            meta = d.get("meta") or {}
            cnpj = meta.get("cnpj")
            razao = meta.get("razao_social")
            break

    if not (cnpj or razao):
        pdf = find_cartao_cnpj_pdf(base)
        if pdf:
            text = read_pdf_text(pdf) or ""
            fields = extract_company_fields(text) if text else {}
            cnpj = fields.get("cnpj")
            razao = fields.get("razao_social")

    if not (cnpj or razao):
        messagebox.showwarning("Atenção", "Nenhum Cartão CNPJ válido encontrado.")
        return

    if "Razão Social" in ents:
        ents["Razão Social"].delete(0, "end")
        if razao:
            ents["Razão Social"].insert(0, razao)
    if "CNPJ" in ents:
        ents["CNPJ"].delete(0, "end")
        if cnpj:
            ents["CNPJ"].insert(0, _only_digits(cnpj))


# -----------------------------------------------------------------------------
# Upload com telinha (thread) – usado por “Salvar + Enviar para Supabase”
# -----------------------------------------------------------------------------
def _classify_storage_error(exc: Exception) -> str:
    s = str(exc).lower()
    if "invalidkey" in s or "invalid key" in s:
        return "invalid_key"
    if "row-level security" in s or "rls" in s or "42501" in s or "403" in s:
        return "rls"
    if "already exists" in s or "keyalreadyexists" in s or "409" in s:
        return "exists"
    return "other"


def _salvar_e_upload_docs_impl(
    self, row, ents: dict, arquivos_selecionados: list | None, win=None
) -> None:
    ctx = getattr(self, "_upload_ctx", None)
    if not ctx:
        return
    if ctx.abort:
        return

def salvar_e_enviar_para_supabase(self, row, ents, win=None):
    """
    Wrapper para salvar cliente e enviar documentos.
    
    Verifica conectividade com sistema de 3 estados antes de processar.
    Esta função trata a instabilidade da conexão com Supabase.
    """
    
    # Verificação extra de segurança usando is_really_online()
    # que verifica threshold de instabilidade
    if not is_really_online():
        state, description = get_supabase_state()
        
        if state == "unstable":
            messagebox.showwarning(
                "Conexão Instável",
                f"A conexão com o Supabase está instável.\n\n"
                f"{description}\n\n"
                f"Não é possível enviar dados no momento.",
                parent=win
            )
        else:  # offline
            messagebox.showwarning(
                "Sistema Offline",
                f"Não foi possível conectar ao Supabase.\n\n"
                f"{description}\n\n"
                f"Verifique sua conexão e tente novamente.",
                parent=win
            )
        
        log.warning("Envio bloqueado no wrapper: Estado = %s", state.upper())
        return
    
    return salvar_e_upload_docs(self, row, ents, None, win)


# -----------------------------------------------------------------------------
# “Ver Subpastas” – manter compatível com app_gui
# -----------------------------------------------------------------------------
def list_storage_objects(bucket_name: str | None, prefix: str = "") -> list:
    try:
        BN = _get_bucket_name(bucket_name)
        prefix = prefix.strip("/")
        adapter = SupabaseStorageAdapter(bucket=BN)
        with using_storage_backend(adapter):
            response = list(storage_list_files(prefix))
        objects = []
        for obj in response:
            if isinstance(obj, dict):
                is_folder = obj.get("metadata") is None
                name = obj.get("name")
                full_path = obj.get("full_path") or (
                    f"{prefix}/{name}".strip("/") if prefix else name
                )
                objects.append(
                    {"name": name, "is_folder": is_folder, "full_path": full_path}
                )
        return objects
    except Exception as e:
        log.error("Erro ao listar objetos: %s", e)
        return []


def download_file(bucket_name: str | None, file_path: str, local_path: str):
    try:
        BN = _get_bucket_name(bucket_name)
        adapter = SupabaseStorageAdapter(bucket=BN)
        with using_storage_backend(adapter):
            storage_download_file(file_path, local_path)
        log.info("Arquivo baixado: %s", local_path)
    except Exception as e:
        log.error("Erro ao baixar %s: %s", file_path, e)


def salvar_e_upload_docs(
    self, row, ents: dict, arquivos_selecionados: list | None, win=None
):
    args = (self, row, ents, arquivos_selecionados, win)
    kwargs: dict = {}
    args, kwargs = validate_inputs(*args, **kwargs)
    args, kwargs = prepare_payload(*args, **kwargs)
    result = _salvar_e_upload_docs_impl(*args, **kwargs)
    perform_uploads(*args, **kwargs)
    finalize_state(*args, **kwargs)
    return result
