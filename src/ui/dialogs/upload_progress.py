# -*- coding: utf-8 -*-
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from src.core.services.upload_service import upload_folder_to_supabase
from ui import center_on_parent
from src.utils.resource_path import resource_path


def show_upload_progress(
    app: tk.Misc, pasta: str, client_id: int, *, subdir: str = "SIFAP"
) -> None:
    dlg = tk.Toplevel(app)
    dlg.withdraw()
    dlg.title("Aguarde…")
    try:
        dlg.iconbitmap(resource_path("rc.ico"))
    except Exception:
        pass
    dlg.resizable(False, False)
    dlg.transient(app)
    dlg.grab_set()
    dlg.protocol("WM_DELETE_WINDOW", lambda: None)

    frm = ttk.Frame(dlg, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Enviando arquivos para o Supabase…").pack(
        anchor="w", pady=(0, 8)
    )
    pb = ttk.Progressbar(frm, mode="indeterminate", length=300)
    pb.pack(fill="x")
    pb.start(12)

    app.update_idletasks()
    w, h = 360, 120
    dlg.geometry(f"{w}x{h}")
    try:
        dlg.update_idletasks()
        center_on_parent(dlg, app)
    except Exception:
        pass
    dlg.deiconify()

    result: dict[str, Any] = {"ok": None, "err": None}

    def _finish() -> None:
        try:
            pb.stop()
        except Exception:
            pass
        try:
            dlg.grab_release()
            dlg.destroy()
        except Exception:
            pass

        if result["err"] is not None:
            messagebox.showerror("Erro ao enviar", result["err"], parent=app)
        else:
            ok = result["ok"] or 0
            messagebox.showinfo(
                "Envio concluído",
                f"{ok} arquivo(s) enviados para o Supabase.",
                parent=app,
            )

    def _worker() -> None:
        try:
            resultados = upload_folder_to_supabase(pasta, int(client_id), subdir=subdir)
            result["ok"] = len(resultados)
        except Exception as exc:
            result["err"] = str(exc)
        finally:
            app.after(0, _finish)

    threading.Thread(target=_worker, daemon=True).start()
