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


from infra.supabase_client import supabase
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
            res = (
                supabase.table("memberships")
                .select("org_id")
                .eq("user_id", uid)
                .limit(1)
                .execute()
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


def salvar_e_upload_docs(
    self, row, ents: dict, arquivos_selecionados: list | None, win=None
) -> None:
    # --- valores
    valores = {
        "Razão Social": ents["Razão Social"].get().strip(),
        "CNPJ": _only_digits(ents["CNPJ"].get().strip()),
        "Nome": ents["Nome"].get().strip(),
        "WhatsApp": _only_digits(ents["WhatsApp"].get().strip()),
        "Observações": ents["Observações"].get("1.0", "end-1c").strip(),
    }

    # -------- duplicatas: Nome/Whats liberados; considerar só CNPJ/Razão --------
    try:
        info = checar_duplicatas_info(
            cnpj=valores.get("CNPJ"),
            razao=valores.get("Razão Social"),
            numero=valores.get("WhatsApp"),  # mantém na chamada
            nome=valores.get("Nome"),  # mantém na chamada
        )
        ids = (info.get("ids") or [])[:]
        if row and ids and int(row[0]) in ids:
            ids = [i for i in ids if i != int(row[0])]

        # filtra os campos para só CNPJ/RAZAO_SOCIAL
        campos_filtrados = [
            c for c in (info.get("campos") or []) if c in ("CNPJ", "RAZAO_SOCIAL")
        ]
        if ids and campos_filtrados:
            campos = ", ".join(campos_filtrados)
            ids_str = ", ".join(str(i) for i in ids)
            if not messagebox.askokcancel(
                "Possível duplicata",
                f'Campos que bateram: {campos or "-"}\nIDs: {ids_str}\n\nDeseja continuar?',
                parent=win,
            ):
                return
    except Exception:
        pass

    # salva cliente
    try:
        client_id, pasta_local = salvar_cliente(row, valores)
    except Exception as e:
        messagebox.showerror("Erro", str(e))
        return

    user_id = _current_user_id()
    created_at = _now_iso_z()
    org_id = _resolve_org_id()
    BUCKET = _get_bucket_name()
    log.info("Bucket em uso: %s", BUCKET)
    storage_adapter = SupabaseStorageAdapter(bucket=BUCKET)

    parent_win = (
        win if (win and hasattr(win, "winfo_exists") and win.winfo_exists()) else self
    )

    # subpasta
    subpasta = _ask_subpasta_nome(parent_win, default="")
    if subpasta is None:
        return

    # garante subpasta no storage (placeholder)
    try:
        if subpasta:
            prefix = _build_storage_path(
                org_id, str(client_id), DEFAULT_IMPORT_SUBFOLDER, subpasta
            )
            with using_storage_backend(storage_adapter):
                existing = list(storage_list_files(prefix))
                if not existing:
                    ph = _build_storage_path(prefix, ".keep")
                    storage_upload_file(b"keep", ph, "text/plain")
                    log.info("Subpasta criada (placeholder): %s", prefix)
    except Exception as e:
        log.warning("Não foi possível garantir a subpasta '%s': %s", subpasta, e)

    # escolhe pasta origem
    src = filedialog.askdirectory(
        parent=parent_win,
        title=f"Escolha a PASTA para importar (irá para '{DEFAULT_IMPORT_SUBFOLDER}{'/' + subpasta if subpasta else ''}')",
    )

    # se nada a enviar
    if not src and not (arquivos_selecionados or []):
        messagebox.showinfo(
            "Nada a enviar", "Cliente salvo, mas nenhum arquivo foi selecionado."
        )
        try:
            self.carregar()
        except Exception:
            pass
        return

    # coleta lista de arquivos a enviar
    files: list[tuple[str, str]] = (
        []
    )  # (local_path, rel_path_na_pasta)  (rel vazio para arquivos soltos)
    for f in arquivos_selecionados or []:
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

    # prepara dialog
    busy = BusyDialog(parent_win, text="Enviando arquivos para o Supabase…")
    busy.set_total(len(files) if files else 1)

    def worker():
        falhas = 0

        # espelha local (se teve pasta)
        if src:
            base_local = (
                os.path.join(pasta_local, DEFAULT_IMPORT_SUBFOLDER, subpasta)
                if subpasta
                else os.path.join(pasta_local, DEFAULT_IMPORT_SUBFOLDER)
            )
            try:
                if not CLOUD_ONLY:
                    os.makedirs(base_local, exist_ok=True)
                for lp, rel in files:
                    dest = (
                        os.path.join(base_local, rel)
                        if src and rel
                        else os.path.join(base_local, os.path.basename(lp))
                    )
                    if not CLOUD_ONLY:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                    try:
                        shutil.copy2(lp, dest)
                    except Exception:
                        # se for pasta inexistente (outra iteração criará)
                        pass
            except Exception as e:
                log.error("Falha ao copiar local: %s", e)

        def _after_step(msg=None):
            if msg:
                busy.set_text(msg)
            busy.step()

        with using_storage_backend(storage_adapter):
            for local_path, rel in files:
                try:
                    rel_parts = (
                        [_sanitize_key_component(p) for p in rel.split("/")]
                        if rel
                        else [_sanitize_key_component(os.path.basename(local_path))]
                    )
                    if subpasta:
                        storage_path = _build_storage_path(
                            org_id,
                            str(client_id),
                            DEFAULT_IMPORT_SUBFOLDER,
                            subpasta,
                            *rel_parts,
                        )
                    else:
                        storage_path = _build_storage_path(
                            org_id, str(client_id), DEFAULT_IMPORT_SUBFOLDER, *rel_parts
                        )

                    data = Path(local_path).read_bytes()
                    ct = (
                        mimetypes.guess_type(storage_path)[0]
                        or "application/octet-stream"
                    )
                    storage_delete_file(storage_path)
                    storage_upload_file(data, storage_path, ct)

                    size_bytes = len(data)
                    sha256_hash = hashlib.sha256(data).hexdigest()

                    # documents
                    doc = (
                        supabase.table("documents")
                        .insert(
                            {
                                "client_id": client_id,
                                "title": os.path.basename(local_path),
                                "kind": os.path.splitext(local_path)[1].lstrip("."),
                                "current_version": None,
                            }
                        )
                        .execute()
                    )
                    document_id = doc.data[0]["id"]

                    # document_versions
                    ver = (
                        supabase.table("document_versions")
                        .insert(
                            {
                                "document_id": document_id,
                                "path": storage_path,
                                "size_bytes": size_bytes,
                                "sha256": sha256_hash,
                                "uploaded_by": user_id or "unknown",
                                "created_at": created_at,
                            }
                        )
                        .execute()
                    )
                    version_id = ver.data[0]["id"]
                    supabase.table("documents").update(
                        {"current_version": version_id}
                    ).eq("id", document_id).execute()

                    log.info("Upload OK: %s", storage_path)
                except Exception as e:
                    falhas += 1
                    kind = _classify_storage_error(e)
                    if kind == "invalid_key":
                        log.error("Nome/caminho inválido: %s", storage_path)
                    elif kind == "rls":
                        log.error(
                            "Permissão negada (RLS) no upload de %s", storage_path
                        )
                    elif kind == "exists":
                        log.warning("Chave já existia: %s", storage_path)
                    else:
                        log.exception("Falha upload/registro (%s): %s", local_path, e)
                finally:
                    self.after(0, _after_step)

        def _finish():
            busy.close()
            msg = (
                "Cliente e docs enviados."
                if falhas == 0
                else f"Cliente salvo com {falhas} falha(s)."
            )
            messagebox.showinfo("Sucesso", msg, parent=parent_win)
            try:
                if win and hasattr(win, "destroy"):
                    win.destroy()
            except Exception:
                pass
            try:
                self.carregar()
            except Exception:
                pass

        self.after(0, _finish)

    threading.Thread(target=worker, daemon=True).start()


# Wrapper usado no botão do form
def salvar_e_enviar_para_supabase(self, row, ents, win=None):
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
