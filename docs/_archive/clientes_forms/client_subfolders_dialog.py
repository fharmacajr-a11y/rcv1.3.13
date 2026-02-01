from __future__ import annotations

from src.ui.ctk_config import ctk

# -*- coding: utf-8 -*-
"""
Dialogo para visualizar e gerenciar subpastas locais de clientes.
"""

import logging
import os
import tkinter as tk
from typing import Iterable, List

from src.config.paths import CLOUD_ONLY
from src.ui.window_utils import show_centered
from src.utils.file_utils import ensure_subpastas, open_folder

logger = logging.getLogger(__name__)


def open_subpastas_dialog(
    parent: tk.Tk | tk.Toplevel,
    base_path: str,
    subpastas: Iterable[str] | None = None,
    extras_visiveis: Iterable[str] | None = None,
) -> None:
    win = tk.Toplevel(parent)
    win.withdraw()
    win.title("Subpastas do Cliente")
    win.transient(parent)
    win.resizable(True, True)

    header = tk.Frame(win)
    header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
    header.columnconfigure(0, weight=1)
    tk.Label(header, text=base_path).grid(row=0, column=0, sticky="w")

    tools = tk.Frame(win)
    tools.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 0))
    tools.columnconfigure(1, weight=1)

    tk.Label(tools, text="Filtrar:").grid(row=0, column=0, sticky="w", padx=(0, 6))
    var_filter = tk.StringVar()
    ent_filter = tk.Entry(tools, textvariable=var_filter)
    ent_filter.grid(row=0, column=1, sticky="ew")

    def _clear_filter():
        var_filter.set("")
        _refresh_rows()

    tk.Button(tools, text="Limpar", command=_clear_filter).grid(row=0, column=2, padx=(6, 12))

    var_only_missing = tk.BooleanVar(value=False)
    tk.Checkbutton(
        tools,
        text="Só faltando",
        variable=var_only_missing,
        command=lambda: _refresh_rows(),
    ).grid(row=0, column=3, sticky="w")

    list_box = tk.Frame(win)
    list_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(10, 0))
    win.rowconfigure(2, weight=1)
    win.columnconfigure(0, weight=1)

    canvas = tk.Canvas(list_box, highlightthickness=0)
    vsb = ctk.CTkScrollbar(list_box, command=canvas.yview)
    rows_holder = tk.Frame(canvas)

    rows_holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=rows_holder, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    list_box.rowconfigure(0, weight=1)
    list_box.columnconfigure(0, weight=1)

    headers = tk.Frame(win)
    headers.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 0))
    headers.columnconfigure(0, weight=1)
    tk.Label(headers, text="Subpasta").grid(row=0, column=0, sticky="w")
    tk.Label(headers, text="Status").grid(row=0, column=1, sticky="w", padx=(6, 0))
    tk.Label(headers, text="").grid(row=0, column=2)

    footer = tk.Frame(win)
    footer.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
    footer.columnconfigure(0, weight=1)

    def _criar_todas():
        nomes = list(sorted(set(list(subpastas or []) + list(extras_visiveis or []))))
        if not nomes:
            try:
                from src.utils.subpastas_config import load_subpastas_config

                _subs, _ext = load_subpastas_config()
                nomes = list(sorted(set(_subs + _ext)))
            except Exception:
                nomes = []
        if nomes:
            ensure_subpastas(base_path, nomes)
        else:
            ensure_subpastas(base_path, None)
        _refresh_rows()

    tk.Button(footer, text="Criar todas", command=_criar_todas).grid(row=0, column=0, sticky="w")

    tk.Button(
        footer,
        text="Abrir pasta base",
        command=lambda: open_folder(base_path),
    ).grid(row=0, column=1, padx=6, sticky="w")

    tk.Button(footer, text="Fechar", command=win.destroy).grid(row=0, column=2, sticky="e")

    all_items: List[str] = list(sorted(set(list(subpastas or []) + list(extras_visiveis or []))))

    if not all_items:
        try:
            from src.utils.subpastas_config import load_subpastas_config

            _subs, _ext = load_subpastas_config()
            all_items = list(sorted(set(_subs + _ext)))
        except Exception:
            all_items = []

    def _normalized_display(name: str) -> str:
        return " / ".join([seg for seg in name.replace("\\", "/").split("/") if seg])

    def _add_row(path_display: str, full_path: str, exists: bool) -> None:
        r = tk.Frame(rows_holder)
        r.grid(sticky="ew", padx=(0, 4), pady=3)
        r.columnconfigure(0, weight=1)

        tk.Label(r, text=path_display).grid(row=0, column=0, sticky="w")
        status_label = tk.Label(
            r,
            text="OK" if exists else "Faltando",
            foreground="green" if exists else "red",
        )
        status_label.grid(row=0, column=1, padx=(10, 10), sticky="w")

        def _open():
            if CLOUD_ONLY:
                from pathlib import Path

                open_folder(Path.home() / "Downloads")
                return
            if not CLOUD_ONLY:
                try:
                    os.makedirs(full_path, exist_ok=True)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao criar subpasta local %s: %s", full_path, exc)
            open_folder(full_path)
            _refresh_rows()

        tk.Button(r, text="Abrir", command=_open).grid(row=0, column=2, sticky="e")

    def _refresh_rows():
        for c in rows_holder.winfo_children():
            c.destroy()

        flt = (var_filter.get() or "").strip().lower()
        only_missing = bool(var_only_missing.get())

        for rel in all_items:
            rel = (rel or "").replace("\\", "/").strip("/")
            if not rel:
                continue
            full = os.path.join(base_path, rel)
            display = _normalized_display(rel)
            exists = os.path.isdir(full)

            if flt and flt not in display.lower():
                continue
            if only_missing and exists:
                continue

            _add_row(display, full, exists)

        rows_holder.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    ent_filter.bind("<KeyRelease>", lambda e: _refresh_rows())
    win.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    min_w, min_h = 640, 420
    win.minsize(min_w, min_h)
    win.update_idletasks()
    show_centered(win)
    _refresh_rows()
    win.grab_set()
    win.focus_force()
