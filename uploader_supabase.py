# -*- coding: utf-8 -*-
"""Helpers para o fluxo de upload de documentos ao Supabase."""
from __future__ import annotations

import logging
import os
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import ttkbootstrap as tb

from adapters.storage.supabase_storage import SupabaseStorageAdapter
from infra.supabase_client import supabase
from src.ui.utils import center_window

log = logging.getLogger(__name__)

CLIENTS_BUCKET = (os.getenv("SUPABASE_CLIENTS_BUCKET") or "clientes").strip() or "clientes"
VOLUME_CONFIRM_THRESHOLD = int(os.getenv("RC_UPLOAD_CONFIRM_THRESHOLD") or "200")


@dataclass(slots=True)
class UploadItem:
    """Container para um item a ser enviado ao Storage."""

    path: Path
    relative_path: str


class UploadProgressDialog(tb.Toplevel):
    """Janela simples com barra de progresso deterministica."""

    def __init__(self, parent: tk.Misc, total: int) -> None:
        super().__init__(parent)
        self.withdraw()
        self.title("Enviando arquivos")
        self.transient(parent)
        self.resizable(False, False)

        self._total = max(int(total), 1)
        self._value = 0

        frame = tb.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        self._label = tb.Label(frame, text="Preparando", anchor="w")
        self._label.pack(fill="x", pady=(0, 8))

        self._bar = ttk.Progressbar(frame, maximum=self._total, mode="determinate", length=360)
        self._bar.pack(fill="x")

        try:
            center_window(self, parent)
        except Exception as e:
            log.debug("Failed to center progress window: %s", e)

        self.deiconify()
        self.grab_set()
        self.update_idletasks()

    def advance(self, label: str) -> None:
        self._value = min(self._total, self._value + 1)
        try:
            self._label.configure(text=label)
            self._bar.configure(value=self._value)
            self.update_idletasks()
        except Exception as e:
            log.debug("Failed to update progress bar: %s", e)

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception as e:
            log.debug("Failed to release grab: %s", e)
        try:
            self.destroy()
        except Exception as e:
            log.debug("Failed to destroy progress window: %s", e)


def _normalize_cnpj(cnpj: str | None) -> str:
    s = (cnpj or "").strip()
    return "".join(ch for ch in s if ch.isdigit())


def _select_pdfs_dialog(parent: Optional[tk.Misc] = None) -> List[str]:
    paths = filedialog.askopenfilenames(
        title="Selecione um ou mais PDFs",
        filetypes=[("PDF", "*.pdf")],
        parent=parent,
    )
    return list(paths or [])


def _show_upload_summary(ok_count: int, failed_paths: List[str], *, parent: Optional[tk.Misc] = None) -> None:
    if failed_paths:
        messagebox.showwarning(
            "Envio concluido com falhas",
            "Alguns arquivos nao foram enviados:\n- " + "\n- ".join(failed_paths),
            parent=parent,
        )
    else:
        messagebox.showinfo(
            "Envio concluido",
            f"Todos os {ok_count} arquivo(s) foram enviados com sucesso.",
            parent=parent,
        )


def _normalize_relative_path(relative: str) -> str:
    rel = relative.replace("\\", "/")
    rel = posixpath.normpath(rel)
    rel = rel.replace("..", "").lstrip("./")
    return rel.strip("/")


def _build_remote_path(cnpj_digits: str, item: UploadItem, subfolder: Optional[str]) -> str:
    parts: List[str] = [cnpj_digits]
    if subfolder:
        parts.append(subfolder.strip("/"))
        parts.append(_normalize_relative_path(item.relative_path))
    else:
        parts.append(_normalize_relative_path(item.relative_path))
    return "/".join(segment.strip("/") for segment in parts if segment)


def collect_pdfs_from_folder(dirpath: str) -> List[UploadItem]:
    """Percorre recursivamente uma pasta e retorna apenas PDFs."""
    base = Path(dirpath)
    if not base.is_dir():
        return []

    items: List[UploadItem] = []
    for file_path in base.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() != ".pdf":
            continue
        relative = file_path.relative_to(base).as_posix()
        items.append(UploadItem(path=file_path, relative_path=relative))
    items.sort(key=lambda item: item.relative_path.lower())
    return items


def build_items_from_files(paths: Sequence[str]) -> List[UploadItem]:
    items: List[UploadItem] = []
    for raw in paths:
        path = Path(raw)
        if path.suffix.lower() != ".pdf":
            continue
        items.append(UploadItem(path=path, relative_path=path.name))
    items.sort(key=lambda item: item.relative_path.lower())
    return items


def ensure_client_saved_or_abort(app: tk.Misc, client_id: int) -> bool:
    """Verifica se ha formulario de edicao com alteracoes pendentes."""
    handler = getattr(app, "ensure_client_saved_for_upload", None)
    if callable(handler):
        return bool(handler(client_id))
    return True


def ask_storage_subfolder(parent: tk.Misc) -> Optional[str]:
    from src.ui.forms.actions import SubpastaDialog

    dialog = SubpastaDialog(parent, default="")
    parent.wait_window(dialog)
    return dialog.result


def _confirm_large_volume(parent: tk.Misc, total: int) -> bool:
    if total <= VOLUME_CONFIRM_THRESHOLD:
        return True
    return messagebox.askyesno(
        "Confirmar envio",
        (
            f"Voce selecionou {total} arquivos.\n\n"
            "Esse volume pode levar algum tempo. Deseja continuar?"
        ),
        parent=parent,
    )


def _upload_batch(
    adapter: SupabaseStorageAdapter,
    items: Sequence[UploadItem],
    cnpj_digits: str,
    subfolder: Optional[str],
    parent: tk.Misc,
) -> Tuple[int, List[Tuple[UploadItem, Exception]]]:
    progress = UploadProgressDialog(parent, len(items))
    ok = 0
    failures: List[Tuple[UploadItem, Exception]] = []

    for item in items:
        label = Path(item.relative_path).name
        progress.advance(f"Enviando {label}")
        try:
            remote_key = _build_remote_path(cnpj_digits, item, subfolder)
            adapter.upload_file(
                item.path,
                remote_key,
                content_type="application/pdf",
            )
            ok += 1
        except Exception as exc:  # pragma: no cover - integracoes externas
            failures.append((item, exc))

    progress.close()
    return ok, failures


def upload_files_to_supabase(
    app: tk.Misc,
    cliente: dict,
    items: Sequence[UploadItem],
    subpasta: Optional[str],
    *,
    parent: Optional[tk.Misc] = None,
    bucket: Optional[str] = None,
) -> Tuple[int, int]:
    """Executa o upload para <bucket>/<cnpj>/<arquivo>."""
    if not items:
        return 0, 0

    target = parent or app
    if not _confirm_large_volume(target, len(items)):
        return 0, 0

    cnpj_digits = _normalize_cnpj(cliente.get("cnpj"))
    if not cnpj_digits:
        messagebox.showwarning(
            "Envio",
            "Este cliente nao possui CNPJ cadastrado. Salve antes de enviar.",
            parent=target,
        )
        return 0, len(items)

    adapter = SupabaseStorageAdapter(
        client=getattr(app, "supabase", None) or supabase,
        bucket=(bucket or CLIENTS_BUCKET),
        overwrite=False,
    )

    ok, failures = _upload_batch(adapter, items, cnpj_digits, subpasta, target)

    failed_paths = [Path(item.relative_path).name for item, _ in failures]
    _show_upload_summary(ok_count=ok, failed_paths=failed_paths, parent=target)

    return ok, len(failures)


def _resolve_selected_cliente(app: tk.Misc) -> Optional[Tuple[int, dict[str, str]]]:
    resolver = getattr(app, "_selected_main_values", None)
    if not callable(resolver):
        return None

    values = resolver()
    if not values:
        return None

    frame_getter = getattr(app, "_main_screen_frame", None)
    frame = frame_getter() if callable(frame_getter) else None
    columns = tuple(getattr(frame, "_col_order", ()))

    mapping: dict[str, str] = {}
    if columns and len(columns) == len(values):
        mapping = {columns[idx]: str(values[idx]) for idx in range(len(columns))}
    else:
        mapping = {str(idx): str(values[idx]) for idx in range(len(values))}

    try:
        client_id_raw = mapping.get("ID", values[0])
        client_id = int(str(client_id_raw).strip())
    except Exception:
        return None

    return client_id, mapping


def send_to_supabase_interactive(
    app: tk.Misc,
    *,
    default_bucket: Optional[str] = None,
    base_prefix: Optional[str] = None,  # mantido por compatibilidade
    default_subprefix: Optional[str] = None,
    parent: Optional[tk.Misc] = None,
) -> Tuple[int, int]:
    del base_prefix, default_subprefix  # parametros legados nao utilizados

    target = parent or app

    resolved = _resolve_selected_cliente(app)
    if not resolved:
        messagebox.showinfo("Envio", "Selecione um cliente primeiro.", parent=target)
        return 0, 0

    client_id, row = resolved

    if not ensure_client_saved_or_abort(app, client_id):
        return 0, 0

    cnpj_value = row.get("CNPJ", "")

    files = _select_pdfs_dialog(parent=target)
    if not files:
        messagebox.showinfo("Envio", "Nenhum arquivo selecionado.", parent=target)
        return 0, 0

    items = build_items_from_files(files)
    if not items:
        messagebox.showwarning(
            "Envio",
            "Nenhum PDF valido foi selecionado.",
            parent=target,
        )
        return 0, 0

    cliente = {"cnpj": cnpj_value}
    return upload_files_to_supabase(
        app,
        cliente,
        items,
        subpasta=None,
        parent=target,
        bucket=default_bucket,
    )


def send_folder_to_supabase(
    app: tk.Misc,
    *,
    default_bucket: Optional[str] = None,
    parent: Optional[tk.Misc] = None,
) -> Tuple[int, int]:
    target = parent or app

    resolved = _resolve_selected_cliente(app)
    if not resolved:
        messagebox.showinfo("Envio", "Selecione um cliente primeiro.", parent=target)
        return 0, 0

    client_id, row = resolved

    if not ensure_client_saved_or_abort(app, client_id):
        return 0, 0

    folder = filedialog.askdirectory(title="Selecione a pasta com os PDFs", parent=target)
    if not folder:
        messagebox.showinfo("Envio", "Nenhuma pasta selecionada.", parent=target)
        return 0, 0

    items = collect_pdfs_from_folder(folder)
    if not items:
        messagebox.showinfo(
            "Envio",
            "Nenhum PDF encontrado nessa pasta.",
            parent=target,
        )
        return 0, 0

    cliente = {"cnpj": row.get("CNPJ", "")}
    return upload_files_to_supabase(
        app,
        cliente,
        items,
        subpasta=None,
        parent=target,
        bucket=default_bucket,
    )


__all__ = [
    "UploadItem",
    "collect_pdfs_from_folder",
    "build_items_from_files",
    "ensure_client_saved_or_abort",
    "ask_storage_subfolder",
    "upload_files_to_supabase",
    "send_to_supabase_interactive",
    "send_folder_to_supabase",
]
