# -*- coding: utf-8 -*-
import os
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from adapters.storage.api import DownloadCancelledError, download_folder_zip
from infra.supabase.storage_helpers import download_bytes
from src.ui.forms.actions import download_file, list_storage_objects
from src.ui.pdf_preview_native import open_pdf_viewer
from src.utils.resource_path import resource_path  # evita ciclo com app_gui


def open_files_browser(
    parent, *, org_id: str, client_id: Any, razao: str, cnpj: str
) -> None:
    """Abre uma janela para navegar/baixar arquivos do Storage (listar, baixar arquivo, baixar pasta .zip)."""
    BUCKET = "rc-docs"
    root_prefix = f"{org_id}/{client_id}".strip("/")

    titulo_parts = [
        p for p in [(razao or "").strip(), (cnpj or "").strip(), f"ID {client_id}"] if p
    ]
    titulo = "Arquivos: " + " - ".join(titulo_parts)

    docs_window = tk.Toplevel(parent)
    docs_window.title(titulo)
    try:
        docs_window.iconbitmap(resource_path("rc.ico"))
    except Exception:
        pass

    # Helpers
    def _center_on_parent(
        win: tk.Toplevel,
        parent_win: tk.Misc,
        width: int | None = None,
        height: int | None = None,
    ):
        win.update_idletasks()
        pw, ph = parent_win.winfo_width(), parent_win.winfo_height()
        px, py = parent_win.winfo_rootx(), parent_win.winfo_rooty()
        w = width or max(1, win.winfo_width())
        h = height or max(1, win.winfo_height())
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    _invalid_chars = r'[<>:"/\\|?*]'

    def _sanitize_filename(name: str) -> str:
        import re as _re

        s = _re.sub(_invalid_chars, "_", name).strip()
        return s.rstrip(" .")

    # Centraliza a janela
    _center_on_parent(docs_window, parent, width=760, height=520)

    # Toolbar
    toolbar = ttk.Frame(docs_window)
    toolbar.pack(fill="x", padx=8, pady=(8, 0))
    ttk.Button(toolbar, text="Baixar selecionado", command=lambda: do_download()).pack(
        side="left"
    )

    btn_preview = ttk.Button(toolbar, text="Visualizar", state="disabled")
    btn_preview.pack(side="left", padx=(8, 0))

    btn_zip_folder = ttk.Button(toolbar, text="Baixar pasta (.zip)")
    btn_zip_folder.pack(side="left", padx=(8, 0))

    ttk.Button(toolbar, text="Fechar", command=docs_window.destroy).pack(side="right")
    docs_window.bind("<Escape>", lambda e: docs_window.destroy())

    info = ttk.Label(
        docs_window, text=f"Supabase: {BUCKET}/{root_prefix}/", foreground="#7a7a7a"
    )
    info.pack(fill="x", padx=8, pady=(2, 0))

    tree = ttk.Treeview(
        docs_window, columns=("type",), show="tree headings", selectmode="browse"
    )
    tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
    tree.heading("type", text="Tipo", anchor="center")
    tree.column("#0", width=560, stretch=True)
    tree.column("type", width=120, anchor="center", stretch=False)
    tree.pack(expand=True, fill="both", padx=8, pady=8)

    def _run_bg(target, on_done):
        res = {"value": None, "err": None}

        def _worker():
            try:
                res["value"] = target()
            except Exception as e:
                res["err"] = e
            finally:
                docs_window.after(0, lambda: on_done(res["value"], res["err"]))

        threading.Thread(target=_worker, daemon=True).start()

    def populate_tree(parent_item, rel_prefix: str):
        full_prefix = (
            root_prefix if not rel_prefix else f"{root_prefix}/{rel_prefix}".rstrip("/")
        )
        objects = list_storage_objects(BUCKET, prefix=full_prefix) or []
        for obj in objects:
            name = (obj.get("name") or "").strip("/")
            is_folder = bool(obj.get("is_folder"))
            item_id = tree.insert(
                parent_item,
                "end",
                text=name,
                values=("Pasta" if is_folder else "Arquivo",),
                open=False,
            )
            if is_folder:
                tree.insert(item_id, "end", text="", values=("...",))

    def _get_rel_path(item) -> str:
        parts = []
        cur = item
        while cur:
            t = tree.item(cur)["text"]
            if t:
                parts.append(t)
            cur = tree.parent(cur)
        parts.reverse()
        return "/".join(parts)

    def on_tree_open(_event=None):
        sel = tree.selection()
        if not sel:
            return
        item = sel[0]
        kids = tree.get_children(item)
        if kids and tree.item(kids[0])["text"] == "":
            tree.delete(kids[0])
            rel = _get_rel_path(item)
            rel_prefix = (rel + "/") if rel else ""
            populate_tree(item, rel_prefix)

    def _current_item_info() -> tuple[str, str, str, str] | None:
        sel = tree.selection()
        if not sel:
            return None
        item = sel[0]
        tipo = (tree.item(item).get("values") or [""])[0]
        rel = _get_rel_path(item)
        nome = (tree.item(item).get("text") or "").strip()
        return item, tipo, rel, nome

    def _update_preview_state() -> None:
        info = _current_item_info()
        if not info:
            btn_preview.configure(state="disabled")
            return
        _, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel or not nome.lower().endswith(".pdf"):
            btn_preview.configure(state="disabled")
            return
        btn_preview.configure(state="normal")

    def do_download():
        info = _current_item_info()
        if not info:
            return
        _item, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel:
            return
        file_path = f"{root_prefix}/{rel}".strip("/")

        base = nome or os.path.basename(rel)
        stem, ext = os.path.splitext(base)
        sufixo = cnpj or f"ID {client_id}"
        suggest = _sanitize_filename(f"{stem} - {sufixo}{ext}")

        local_path = filedialog.asksaveasfilename(
            parent=docs_window, title="Salvar como", initialfile=suggest
        )
        if local_path:
            try:
                download_file(BUCKET, file_path, local_path)
                messagebox.showinfo("Sucesso", "Arquivo baixado!", parent=docs_window)
            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Falha ao baixar: {e}", parent=docs_window
                )

    # Baixar pasta como ZIP (com Cancelar)
    def on_zip_folder():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo(
                "Baixar pasta",
                "Selecione uma pasta (ex.: GERAL, SIFAP).",
                parent=docs_window,
            )
            return
        item = sel[0]
        tipo = (tree.item(item).get("values") or [""])[0]
        if (tipo or "").lower() != "pasta":
            messagebox.showinfo(
                "Baixar pasta", "O item selecionado nao e pasta.", parent=docs_window
            )
            return

        rel = _get_rel_path(item)
        if not rel:
            messagebox.showerror(
                "Baixar pasta",
                "Nao foi possivel determinar a pasta.",
                parent=docs_window,
            )
            return

        prefix = f"{root_prefix}/{rel}".strip("/")
        pasta = rel.rstrip("/").split("/")[-1] or "pasta"
        ident = cnpj or f"ID {client_id}"
        zip_name = _sanitize_filename(f"{pasta} - {ident} - {razao}".strip())

        # Pasta de destino (Cancelar => Downloads)
        initial = str(Path.home() / "Downloads")
        chosen_dir = filedialog.askdirectory(
            parent=docs_window,
            title="Escolha a pasta para salvar o ZIP (Cancelar = Downloads padrao)",
            initialdir=initial,
            mustexist=True,
        )
        out_dir = chosen_dir or None

        # Dialogo "Aguarde..."
        wait = tk.Toplevel(docs_window)
        wait.withdraw()
        wait.title("Aguarde...")
        wait.resizable(False, False)
        wait.transient(docs_window)
        try:
            wait.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass
        wait.grab_set()

        frm = ttk.Frame(wait, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=f"Compactando e baixando: {pasta}").pack(pady=(0, 8))
        pb = ttk.Progressbar(frm, mode="indeterminate", length=260)
        pb.pack()
        pb.start(12)

        # Centraliza e mostra
        docs_window.update_idletasks()
        pw, ph = docs_window.winfo_width(), docs_window.winfo_height()
        px, py = docs_window.winfo_rootx(), docs_window.winfo_rooty()
        w, h = 320, 140
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        wait.geometry(f"{w}x{h}+{x}+{y}")
        wait.deiconify()

        cancel_event = threading.Event()
        btns = ttk.Frame(frm)
        btns.pack(pady=(10, 0))
        btn_cancel = ttk.Button(btns, text="Cancelar")
        btn_cancel.pack(side="left")

        def _do_cancel():
            btn_cancel.configure(state="disabled")
            try:
                pb.stop()
                pb.configure(mode="determinate", value=0, maximum=100)
            except Exception:
                pass
            cancel_event.set()

        btn_cancel.configure(command=_do_cancel)
        btn_zip_folder.configure(state="disabled")

        def _target():
            return download_folder_zip(
                prefix,
                bucket=BUCKET,
                zip_name=zip_name,
                out_dir=out_dir,
                timeout_s=300,
                cancel_event=cancel_event,
            )

        def _done(destino, err):
            try:
                wait.grab_release()
            except Exception:
                pass
            try:
                wait.destroy()
            except Exception:
                pass
            btn_zip_folder.configure(state="normal")

            if err:
                if isinstance(err, DownloadCancelledError):
                    messagebox.showinfo(
                        "Download cancelado",
                        "Voce cancelou o download.",
                        parent=docs_window,
                    )
                elif isinstance(err, TimeoutError):
                    messagebox.showerror(
                        "Tempo esgotado",
                        "O servidor nao respondeu a tempo (conexao ou leitura). "
                        "Verifique sua internet e tente novamente.",
                        parent=docs_window,
                    )
                else:
                    messagebox.showerror(
                        "Erro ao baixar pasta", str(err), parent=docs_window
                    )
            else:
                messagebox.showinfo(
                    "Download concluido",
                    f"ZIP salvo em:\n{destino}",
                    parent=docs_window,
                )

            try:
                docs_window.lift()
                docs_window.attributes("-topmost", True)
                docs_window.after(
                    200, lambda: docs_window.attributes("-topmost", False)
                )
            except Exception:
                pass

        _run_bg(_target, _done)

    btn_zip_folder.configure(command=on_zip_folder)

    def on_preview() -> None:
        info = _current_item_info()
        if not info:
            return
        _item, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel or not nome.lower().endswith(".pdf"):
            _update_preview_state()
            return

        btn_preview.configure(state="disabled")
        remote_path = f"{root_prefix}/{rel}".strip("/")

        def _target():
            return download_bytes(BUCKET, remote_path)

        def _done(data, err):
            if err or not data:
                messagebox.showerror(
                    "Visualizar",
                    "Nao foi possivel carregar este PDF.",
                    parent=docs_window,
                )
            else:
                tmp_path = None
                try:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    try:
                        tmp.write(data)
                        tmp_path = tmp.name
                    finally:
                        tmp.close()
                    viewer = open_pdf_viewer(docs_window, tmp_path, display_name=nome)

                    def _cleanup(_event=None):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                    viewer.bind("<Destroy>", _cleanup, add="+")
                except Exception as exc:
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass
                    messagebox.showerror(
                        "Visualizar",
                        f"Falha ao abrir visualizacao: {exc}",
                        parent=docs_window,
                    )
            _update_preview_state()

        _run_bg(_target, _done)

    btn_preview.configure(command=on_preview)

    def on_double_click(_event=None):
        do_download()

    tree.bind("<<TreeviewOpen>>", on_tree_open)
    tree.bind("<Double-1>", on_double_click)
    tree.bind("<<TreeviewSelect>>", lambda _e: _update_preview_state())
    populate_tree("", rel_prefix="")
    _update_preview_state()
