"""Views do modulo Uploads / Arquivos."""

from __future__ import annotations

import logging
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox, ttk
from typing import Any

from src.modules.uploads.components.helpers import (
    client_prefix_for_id,
    format_cnpj_for_display,
    get_clients_bucket,
    strip_cnpj_from_razao,
)
from src.modules.uploads.service import delete_storage_object, download_storage_object, list_browser_items
from src.utils.prefs import load_browser_status_map, load_last_prefix
from src.utils.resource_path import resource_path

from .action_bar import ActionBar
from .file_list import FileList

_executor = ThreadPoolExecutor(max_workers=4)
_log = logging.getLogger(__name__)


def _join(*parts: str) -> str:
    segs: list[str] = []
    for part in parts:
        if not part:
            continue
        segs.extend([segment for segment in str(part).split("/") if segment])
    return "/".join(segs)


def _norm(path: str) -> str:
    return _join(path)


UI_GAP = 6
UI_PADX = 8
UI_PADY = 6

FOLDER_STATUS_NEUTRAL = "neutral"
FOLDER_STATUS_READY = "ready"
FOLDER_STATUS_NOTREADY = "notready"

STATUS_GLYPHS = {
    FOLDER_STATUS_NEUTRAL: ".",
    FOLDER_STATUS_READY: "OK",
    FOLDER_STATUS_NOTREADY: "X",
}


class UploadsBrowserWindow(tk.Toplevel):
    """Janela principal para navegar arquivos do Storage."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        org_id: str = "",
        client_id: int,
        razao: str = "",
        cnpj: str = "",
        bucket: str | None = None,
        base_prefix: str | None = None,
        supabase=None,  # type: ignore[no-untyped-def]
        start_prefix: str = "",
        module: str = "",
        modal: bool = False,
    ) -> None:
        super().__init__(parent)
        self._is_closing = False
        self._supabase = supabase
        self._module = module
        self._org_id = org_id
        self._client_id = client_id
        self._browser_key = f"org:{org_id}|client:{client_id}|module:{module or 'clientes'}"
        self._bucket = (bucket or get_clients_bucket()).strip()
        self._base_prefix = _norm(base_prefix or client_prefix_for_id(client_id, org_id))
        self._path_stack: list[str] = []
        self._last_listing_map: dict[str, bool] = {}

        razao_clean = strip_cnpj_from_razao(razao, cnpj)
        cnpj_fmt = format_cnpj_for_display(cnpj)
        if module == "auditoria":
            title = f"Arquivos: {razao_clean} ? {cnpj_fmt} ? ID {client_id}"
        else:
            title = f"Arquivos: ID {client_id} ? {razao_clean} ? {cnpj_fmt}"
        self.title(title)
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aplicar iconbitmap no UploadsBrowser: %s", exc)

        remembered = load_last_prefix(self._browser_key) if module else None
        self._init_path_stack(remembered=remembered, start_prefix=start_prefix)

        self._status_cache = load_browser_status_map(self._browser_key) if module == "auditoria" else {}
        self._build_ui()
        self.transient(parent)
        if modal:
            try:
                self.grab_set()
                self.focus_set()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao configurar janela modal do UploadsBrowser: %s", exc)
        self._populate_initial_state()

    def _init_path_stack(self, *, remembered: str | None, start_prefix: str) -> None:
        """
        Define a pilha inicial de navega��o restringindo ao prefixo base do cliente.
        """
        self._path_stack = []

        def _apply(candidate: str | None) -> bool:
            if not candidate:
                return False
            norm = _norm(candidate)
            rel = norm
            if norm.startswith(self._base_prefix):
                rel = norm[len(self._base_prefix) :].lstrip("/")
            parts = [p for p in rel.split("/") if p]
            self._path_stack = parts
            return True

        if _apply(start_prefix):
            return
        if self._module and _apply(remembered):
            return
        _apply(self._base_prefix)

    def _current_prefix(self) -> str:
        return _join(self._base_prefix, *self._path_stack)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.geometry("1000x620")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        top_bar = ttk.Frame(self, padding=(UI_PADX, UI_PADY))
        top_bar.grid(row=0, column=0, sticky="nsew")
        top_bar.columnconfigure(1, weight=1)

        ttk.Label(top_bar, text="Prefixo atual:").grid(row=0, column=0, sticky="w")
        self.prefix_var = tk.StringVar(value=self._current_prefix())
        prefix_entry = ttk.Entry(top_bar, textvariable=self.prefix_var, state="readonly")
        prefix_entry.grid(row=0, column=1, sticky="ew", padx=(UI_GAP, 0))

        refresh_btn = ttk.Button(top_bar, text="Atualizar", command=self._refresh_listing)
        refresh_btn.grid(row=0, column=3, padx=(UI_GAP, 0))

        up_btn = ttk.Button(top_bar, text="Subir", command=self._go_up)
        up_btn.grid(row=0, column=2, padx=(UI_GAP, 0), sticky="e")

        body = ttk.Frame(self, padding=(UI_PADX, 0))
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.file_list = FileList(body, on_download=self._download_selected, on_delete=self._delete_selected)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.tree.bind("<Double-1>", self._on_tree_double_click)

        actions = ActionBar(
            self, padding=(UI_PADX, UI_PADY), on_download=self._download_selected, on_delete=self._delete_selected
        )
        actions.grid(row=2, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _populate_initial_state(self) -> None:
        self.after(100, self._refresh_listing)

    def _refresh_listing(self) -> None:
        prefix = self._current_prefix()
        self.prefix_var.set(prefix)
        _log.info("Browser prefix atual: %s (bucket=%s, cliente=%s)", prefix, self._bucket, self._client_id)
        items = list_browser_items(prefix, bucket=self._bucket)
        self._last_listing_map = {
            entry.get("name"): bool(entry.get("is_folder")) for entry in items if isinstance(entry, dict)
        }
        self.file_list.populate_rows(items, self._status_cache)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _download_selected(self) -> None:
        item_name = self.file_list.selected_item()
        if not item_name:
            messagebox.showinfo("Arquivos", "Selecione um item para baixar.", parent=self)
            return
        prefix = self._current_prefix()
        remote_key = _join(prefix, item_name)
        local_path = filedialog.asksaveasfilename(parent=self, initialfile=item_name)
        if not local_path:
            return
        try:
            download_storage_object(remote_key, local_path, bucket=self._bucket)
            messagebox.showinfo("Download", f"Arquivo salvo em {local_path}.", parent=self)
        except Exception as exc:
            _log.exception("Download falhou")
            messagebox.showerror("Download", f"Falha ao baixar arquivo: {exc}", parent=self)

    def _delete_selected(self) -> None:
        item_name = self.file_list.selected_item()
        if not item_name:
            return
        prefix = self._current_prefix()
        remote_key = _join(prefix, item_name)
        if not messagebox.askyesno("Excluir", f"Deseja excluir '{item_name}'?", parent=self):
            return
        try:
            delete_storage_object(remote_key, bucket=self._bucket)
            self._refresh_listing()
        except Exception as exc:
            _log.exception("Delete falhou")
            messagebox.showerror("Excluir", f"Falha ao excluir arquivo: {exc}", parent=self)

    def _go_up(self) -> None:
        if self._path_stack:
            self._path_stack.pop()
            self._refresh_listing()

    def _on_tree_double_click(self, _event) -> None:
        item_name = self.file_list.selected_item()
        if not item_name:
            return
        if self._last_listing_map.get(item_name):
            self._path_stack.append(item_name)
            self._refresh_listing()
        else:
            self._download_selected()


def open_files_browser(*args: Any, **kwargs: Any) -> UploadsBrowserWindow:
    modal = kwargs.get("modal", False)
    parent = args[0] if args else kwargs.get("parent")
    window = UploadsBrowserWindow(*args, **kwargs)
    if modal and parent is not None:
        try:
            parent.wait_window(window)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aguardar janela modal do UploadsBrowser: %s", exc)
    return window
