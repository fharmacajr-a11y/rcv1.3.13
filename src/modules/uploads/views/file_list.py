from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Optional


class FileList(ttk.Frame):
    """Treeview que exibe arquivos e delega acoes para callbacks."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_download: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_download = on_download
        self._on_delete = on_delete
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self, columns=("size", "modified", "status"), show="tree headings")
        self.tree.heading("size", text="Tamanho")
        self.tree.heading("modified", text="Modificado")
        self.tree.heading("status", text="Status")
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("modified", width=160, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Delete>", lambda _event: self._handle_delete())
        self.tree.bind("<BackSpace>", lambda _event: self._handle_delete())
        self.tree.bind("<Return>", lambda _event: self._handle_download())

    def populate_rows(self, rows: Iterable[dict], status_cache: dict[str, str]) -> None:
        self.tree.delete(*self.tree.get_children(""))
        for entry in rows:
            name = entry.get("name") or entry.get("Key")
            size = entry.get("size") or entry.get("Size") or ""
            modified = entry.get("updated_at") or entry.get("LastModified") or ""
            iid = self.tree.insert("", "end", text=name or "--", values=(size, modified, ""))
            self.tree.set(iid, "status", status_cache.get(name or "", ""))

    def selected_item(self) -> Optional[str]:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.tree.item(selection[0], "text")

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children(""))

    def _handle_download(self) -> None:
        if self._on_download:
            self._on_download()

    def _handle_delete(self) -> None:
        if self._on_delete:
            self._on_delete()
