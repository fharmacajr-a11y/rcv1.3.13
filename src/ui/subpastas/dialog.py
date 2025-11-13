# ui/subpastas/dialog.py
from __future__ import annotations

import os
import tkinter as tk
from typing import Iterable, List

import ttkbootstrap as tb

from src.config.paths import CLOUD_ONLY
from src.utils.file_utils import ensure_subpastas, open_folder

try:
    from ui import center_on_parent
except Exception:  # pragma: no cover
    try:
        from src.ui.utils import center_on_parent
    except Exception:  # pragma: no cover

        def center_on_parent(win, parent=None, pad=0):
            return win


def open_subpastas_dialog(
    parent: tk.Tk | tk.Toplevel,
    base_path: str,
    subpastas: Iterable[str] | None = None,
    extras_visiveis: Iterable[str] | None = None,
) -> None:
    win = tb.Toplevel(parent)
    win.title("Subpastas do Cliente")
    win.transient(parent)
    win.resizable(True, True)

    # ---------- Header ----------
    header = tb.Frame(win, padding=(10, 10, 10, 0))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(0, weight=1)
    tb.Label(header, text=base_path).grid(row=0, column=0, sticky="w")

    # ---------- Filtro ----------
    tools = tb.Frame(win, padding=(10, 6, 10, 0))
    tools.grid(row=1, column=0, sticky="ew")
    tools.columnconfigure(1, weight=1)

    tb.Label(tools, text="Filtrar:").grid(row=0, column=0, sticky="w", padx=(0, 6))
    var_filter = tk.StringVar()
    ent_filter = tb.Entry(tools, textvariable=var_filter)
    ent_filter.grid(row=0, column=1, sticky="ew")

    def _clear_filter():
        var_filter.set("")
        _refresh_rows()

    tb.Button(tools, text="Limpar", bootstyle="secondary", command=_clear_filter).grid(row=0, column=2, padx=(6, 12))

    var_only_missing = tk.BooleanVar(value=False)
    tb.Checkbutton(
        tools,
        text="Só faltando",
        variable=var_only_missing,
        command=lambda: _refresh_rows(),
    ).grid(row=0, column=3, sticky="w")

    # ---------- Lista rolável ----------
    list_box = tb.Frame(win, padding=(10, 10, 10, 0))
    list_box.grid(row=2, column=0, sticky="nsew")
    win.rowconfigure(2, weight=1)
    win.columnconfigure(0, weight=1)

    canvas = tk.Canvas(list_box, highlightthickness=0)
    vsb = tb.Scrollbar(list_box, orient="vertical", command=canvas.yview)
    rows_holder = tb.Frame(canvas)

    rows_holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=rows_holder, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    list_box.rowconfigure(0, weight=1)
    list_box.columnconfigure(0, weight=1)

    # ---------- Cabeçalhos ----------
    headers = tb.Frame(win, padding=(10, 6, 10, 0))
    headers.grid(row=3, column=0, sticky="ew")
    headers.columnconfigure(0, weight=1)
    tb.Label(headers, text="Subpasta").grid(row=0, column=0, sticky="w")
    tb.Label(headers, text="Status").grid(row=0, column=1, sticky="w", padx=(6, 0))
    tb.Label(headers, text="").grid(row=0, column=2)  # botão Abrir

    # ---------- Rodapé ----------
    footer = tb.Frame(win, padding=10)
    footer.grid(row=4, column=0, sticky="ew")
    footer.columnconfigure(0, weight=1)

    def _criar_todas():
        nomes = list(sorted(set(list(subpastas or []) + list(extras_visiveis or []))))
        if not nomes:  # se não veio nada, carrega do YAML
            try:
                from src.utils.subpastas_config import load_subpastas_config

                _subs, _ext = load_subpastas_config()
                nomes = list(sorted(set(_subs + _ext)))
            except Exception:
                nomes = []
        if nomes:
            ensure_subpastas(base_path, nomes)
        else:
            ensure_subpastas(base_path, None)  # fallback: loader interno do file_utils
        _refresh_rows()

    tb.Button(footer, text="Criar todas", bootstyle="primary", command=_criar_todas).grid(row=0, column=0, sticky="w")

    tb.Button(
        footer,
        text="Abrir pasta base",
        bootstyle="secondary",
        command=lambda: open_folder(base_path),
    ).grid(row=0, column=1, padx=6, sticky="w")

    tb.Button(footer, text="Fechar", bootstyle="secondary", command=win.destroy).grid(row=0, column=2, sticky="e")

    # ---------- Dados ----------
    all_items: List[str] = list(sorted(set(list(subpastas or []) + list(extras_visiveis or []))))

    # Se vier vazio, tenta carregar do YAML aqui mesmo
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
        r = tb.Frame(rows_holder)
        r.grid(sticky="ew", padx=(0, 4), pady=3)
        r.columnconfigure(0, weight=1)

        tb.Label(r, text=path_display).grid(row=0, column=0, sticky="w")
        status = tb.Label(
            r,
            text="OK" if exists else "Faltando",
            bootstyle=("success" if exists else "danger"),
        )
        status.grid(row=0, column=1, padx=(10, 10), sticky="w")

        def _open():
            if CLOUD_ONLY:
                from pathlib import Path

                open_folder(Path.home() / "Downloads")
                return
            if not CLOUD_ONLY:
                try:
                    os.makedirs(full_path, exist_ok=True)
                except Exception:
                    pass
            open_folder(full_path)
            _refresh_rows()

        tb.Button(r, text="Abrir", bootstyle="secondary", command=_open).grid(row=0, column=2, sticky="e")

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

    # binds e layout final (fora de _refresh_rows)
    ent_filter.bind("<KeyRelease>", lambda e: _refresh_rows())
    win.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    win.update_idletasks()
    min_w, min_h = 640, 420
    win.minsize(min_w, min_h)
    center_on_parent(win, parent)
    _refresh_rows()
    win.grab_set()
    win.focus_force()
