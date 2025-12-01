# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from src.modules.uploads.service import upload_folder_to_supabase
from src.utils.resource_path import resource_path
from ui import center_on_parent

logger = logging.getLogger(__name__)


def show_upload_progress(app: tk.Misc, pasta: str, client_id: int, *, subdir: str = "SIFAP") -> None:
    dlg = tk.Toplevel(app)
    dlg.withdraw()
    dlg.title("Aguarde…")
    try:
        dlg.iconbitmap(resource_path("rc.ico"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao aplicar iconbitmap no dialogo de progresso de upload: %s", exc)
    dlg.resizable(False, False)
    dlg.transient(app)
    dlg.grab_set()
    dlg.protocol("WM_DELETE_WINDOW", lambda: None)

    frm = ttk.Frame(dlg, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Enviando arquivos para o Supabase…").pack(anchor="w", pady=(0, 8))
    pb = ttk.Progressbar(frm, mode="indeterminate", length=300)
    pb.pack(fill="x")
    pb.start(12)

    app.update_idletasks()
    w, h = 360, 120
    dlg.geometry(f"{w}x{h}")
    try:
        dlg.update_idletasks()
        center_on_parent(dlg, app)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao centralizar dialogo de progresso de upload: %s", exc)
    dlg.deiconify()

    result: dict[str, Any] = {"ok": None, "err": None}

    def _finish() -> None:
        try:
            pb.stop()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao parar progresso de upload: %s", exc)
        try:
            dlg.grab_release()
            dlg.destroy()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar dialogo de progresso de upload: %s", exc)

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
