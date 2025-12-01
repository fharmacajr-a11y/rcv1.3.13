# -*- coding: utf-8 -*-
"""Helpers para o fluxo de upload de documentos ao Supabase."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, cast

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import ttkbootstrap as tb

from src.modules.uploads import service as uploads_service
from src.modules.uploads.components.helpers import _cnpj_only_digits
from src.ui.utils import center_window

log = logging.getLogger(__name__)

CLIENTS_BUCKET = (os.getenv("SUPABASE_CLIENTS_BUCKET") or "clientes").strip() or "clientes"
VOLUME_CONFIRM_THRESHOLD = int(os.getenv("RC_UPLOAD_CONFIRM_THRESHOLD") or "200")


UploadItem = uploads_service.UploadItem
collect_pdfs_from_folder = uploads_service.collect_pdfs_from_folder
build_items_from_files = uploads_service.build_items_from_files


class UploadProgressDialog(tb.Toplevel):
    """Janela simples com barra de progresso deterministica."""

    def __init__(self, parent: tk.Misc, total: int) -> None:
        # tb.Toplevel herda de tk.Toplevel; aceita parent como primeiro argumento posicional
        super().__init__(parent)  # type: ignore[arg-type]
        self.withdraw()
        self.title("Enviando arquivos")
        # Cast parent para tk.Tk para chamar transient()
        parent_window = cast(tk.Tk, parent)
        self.transient(parent_window)
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
            # center_window espera (win, width, height)
            center_window(self, w=400, h=120)
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


def _select_pdfs_dialog(parent: Optional[tk.Misc] = None) -> List[str]:
    """Abre diálogo de seleção múltipla de PDFs e retorna os paths escolhidos."""
    paths = filedialog.askopenfilenames(
        title="Selecione um ou mais PDFs",
        filetypes=[("PDF", "*.pdf")],
        parent=parent,
    )
    return list(paths or [])


def _show_upload_summary(ok_count: int, failed_paths: List[str], *, parent: Optional[tk.Misc] = None) -> None:
    """Exibe resumo de sucesso/falha dos uploads em dialog de alerta."""
    # messagebox fun��es esperam parent n�o-None; usar None como fallback padr�o
    if failed_paths:
        messagebox.showwarning(
            "Envio concluido com falhas",
            "Alguns arquivos nao foram enviados:\n- " + "\n- ".join(failed_paths),
            parent=parent if parent is not None else None,  # type: ignore[arg-type]
        )
    else:
        messagebox.showinfo(
            "Envio concluido",
            f"Todos os {ok_count} arquivo(s) foram enviados com sucesso.",
            parent=parent if parent is not None else None,  # type: ignore[arg-type]
        )


def ensure_client_saved_or_abort(app: tk.Misc, client_id: int) -> bool:
    """Verifica se ha formulario de edicao com alteracoes pendentes."""
    handler = getattr(app, "ensure_client_saved_for_upload", None)
    if callable(handler):
        return bool(handler(client_id))
    return True


def ask_storage_subfolder(parent: tk.Misc) -> Optional[str]:
    """Abre dialogo para escolher subpasta de storage (pode retornar None se cancelado)."""
    from src.modules.forms.view import SubpastaDialog

    dialog = SubpastaDialog(parent, default="")
    parent.wait_window(dialog)
    return dialog.result


def _confirm_large_volume(parent: tk.Misc, total: int) -> bool:
    """Pergunta ao usuario se deve continuar quando o volume de arquivos excede o threshold."""
    if total <= VOLUME_CONFIRM_THRESHOLD:
        return True
    return messagebox.askyesno(
        "Confirmar envio",
        (f"Voce selecionou {total} arquivos.\n\nEsse volume pode levar algum tempo. Deseja continuar?"),
        parent=parent,
    )


def _upload_batch(
    app: tk.Misc,
    items: Sequence[UploadItem],
    cnpj_digits: str,
    subfolder: Optional[str],
    parent: tk.Misc,
    *,
    bucket: Optional[str] = None,
    client_id: Optional[int] = None,
    org_id: Optional[str] = None,
) -> Tuple[int, List[Tuple[UploadItem, Exception]]]:
    """
    Upload batch with threading support.

    PERF-002: Movido I/O de rede para thread background para evitar
    travamento da GUI durante uploads. A janela de progresso � atualizada
    via widget.after() chamado da thread de I/O.
    """
    import threading
    import queue

    progress = UploadProgressDialog(parent, len(items))
    result_queue: queue.Queue = queue.Queue()

    def _safe_after(delay: int, callback: Any) -> None:
        """Schedule callback on main thread safely."""
        try:
            progress.after(delay, callback)
        except Exception as e:
            log.debug("Failed to schedule callback: %s", e)

    def _progress(item: UploadItem) -> None:
        label = Path(item.relative_path).name
        # Atualiza progresso via main thread
        _safe_after(0, lambda: progress.advance(f"Enviando {label}"))

    def _upload_worker() -> None:
        """Execute upload em thread background."""
        try:
            ok, failures = uploads_service.upload_items_for_client(
                items,
                cnpj_digits=cnpj_digits,
                bucket=bucket or CLIENTS_BUCKET,
                supabase_client=getattr(app, "supabase", None),
                subfolder=subfolder,
                progress_callback=_progress,
                client_id=client_id,
                org_id=org_id,
            )
            result_queue.put(("success", ok, failures))
        except Exception as exc:
            log.error("Upload batch error: %s", exc, exc_info=True)
            result_queue.put(("error", exc))

    # Inicia upload em background thread
    worker = threading.Thread(target=_upload_worker, daemon=True)
    worker.start()

    # Aguarda resultado bloqueando apenas esta janela, n�o a GUI principal
    # A janela de progresso continua processando eventos via update_idletasks
    while worker.is_alive():
        try:
            progress.update_idletasks()
            progress.update()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar janela de progresso: %s", exc)
        worker.join(timeout=0.05)

    # Recupera resultado
    try:
        result = result_queue.get_nowait()
        progress.close()

        if result[0] == "success":
            return result[1], result[2]
        else:
            # Se houve erro, relan�a
            raise result[1]
    except queue.Empty:
        progress.close()
        raise RuntimeError("Upload thread finished without result")


def upload_files_to_supabase(
    app: tk.Misc,
    cliente: dict,
    items: Sequence[UploadItem],
    subpasta: Optional[str],
    *,
    parent: Optional[tk.Misc] = None,
    bucket: Optional[str] = None,
    client_id: Optional[int] = None,
) -> Tuple[int, int]:
    """Executa o upload para <bucket>/<org_id>/<client_id>/GERAL/<arquivo>."""
    if not items:
        return 0, 0

    target = parent or app
    if not _confirm_large_volume(target, len(items)):
        return 0, 0

    cnpj_raw = cliente.get("cnpj")
    cnpj_digits = _cnpj_only_digits(cnpj_raw) if cnpj_raw else ""
    if not cnpj_digits:
        messagebox.showwarning(
            "Envio",
            "Este cliente nao possui CNPJ cadastrado. Salve antes de enviar.",
            parent=target,
        )
        return 0, len(items)

    # Obtem org_id do usuario logado
    org_id: Optional[str] = None
    if client_id is not None:
        try:
            from src.modules.uploads.components.helpers import get_current_org_id

            sb = getattr(app, "supabase", None)
            if sb:
                org_id = get_current_org_id(sb)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao resolver org_id para upload: %s", exc)

    ok, failures = _upload_batch(
        app,
        items,
        cnpj_digits,
        subpasta,
        target,
        bucket=bucket,
        client_id=client_id,
        org_id=org_id,
    )

    failed_paths = [Path(item.relative_path).name for item, _ in failures]
    _show_upload_summary(ok_count=ok, failed_paths=failed_paths, parent=target)

    return ok, len(failures)


def _resolve_selected_cliente(app: tk.Misc) -> Optional[Tuple[int, dict[str, str]]]:
    """Obt�m o cliente selecionado na UI, retornando id e mapping de colunas ou None."""
    resolver = getattr(app, "_selected_main_values", None)
    if not callable(resolver):
        return None

    values = resolver()
    if not values:
        return None

    frame_getter = getattr(app, "_main_screen_frame", None)
    frame = frame_getter() if callable(frame_getter) else None
    columns = tuple(getattr(frame, "_col_order", ()))

    # Cast para Sequence para garantir que suporta len() e indexa��o
    values_seq = cast(Sequence, values)
    columns_seq = cast(Sequence, columns)

    mapping: dict[str, str] = {}
    if columns_seq and len(columns_seq) == len(values_seq):
        mapping = {str(columns_seq[idx]): str(values_seq[idx]) for idx in range(len(columns_seq))}
    else:
        mapping = {str(idx): str(values_seq[idx]) for idx in range(len(values_seq))}

    try:
        client_id_raw = mapping.get("ID", str(values_seq[0]))
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
    """Fluxo interativo: seleciona cliente, coleta PDFs e envia ao Supabase."""
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
        client_id=client_id,
    )


def send_folder_to_supabase(
    app: tk.Misc,
    *,
    default_bucket: Optional[str] = None,
    parent: Optional[tk.Misc] = None,
) -> Tuple[int, int]:
    """Fluxo interativo: seleciona cliente e pasta local, envia todos os PDFs."""
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

    # Captura o nome da pasta selecionada para usar como subfolder no Storage
    from pathlib import Path as _Path

    folder_name = _Path(folder).name

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
        subpasta=folder_name,  # Passa o nome da pasta como subfolder
        parent=target,
        bucket=default_bucket,
        client_id=client_id,
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
