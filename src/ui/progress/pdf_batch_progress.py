from __future__ import annotations

import logging
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional

from src.ui.window_utils import show_centered
from src.utils.paths import resource_path

_log = logging.getLogger(__name__)


class PDFBatchProgressDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk | tk.Toplevel, total_bytes: int, total_subdirs: int) -> None:
        super().__init__(parent)
        self.withdraw()
        self._parent = parent
        self.title("Conversor PDF")
        self.total_bytes = total_bytes
        self.total_subdirs = total_subdirs
        self.start_time = time.monotonic()
        self._closed = False

        try:
            icon_path = resource_path("rc.ico")
            if icon_path:
                try:
                    self.iconbitmap(icon_path)
                except Exception:
                    try:
                        img = tk.PhotoImage(file=icon_path)
                        self.iconphoto(True, img)
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao definir iconphoto em pdf_batch_progress: %s", exc)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao definir ícone em pdf_batch_progress: %s", exc)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=320, mode="determinate", maximum=100)
        self.progress.pack(padx=12, pady=(12, 6))

        self.label_subdir = ttk.Label(self, text="Subpasta 0/0")
        self.label_subdir.pack(padx=12, pady=2)

        self.label_bytes = ttk.Label(self, text="0 KB de 0 KB (~0.0%)")
        self.label_bytes.pack(padx=12, pady=2)

        self.label_eta = ttk.Label(self, text="Tempo estimado: 00:00")
        self.label_eta.pack(padx=12, pady=(2, 12))

        self.resizable(False, False)
        try:
            self.transient(parent)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao configurar modal em pdf_batch_progress: %s", exc)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._center_on_parent()

    def update_progress(
        self,
        processed_bytes: int,
        total_bytes: int,
        current_index: int,
        total_subdirs: int,
        current_subdir: Optional[Path],
        current_image: Optional[Path],
    ) -> None:
        if self.is_closed:
            return

        percent = 0.0
        if total_bytes > 0:
            percent = (processed_bytes / total_bytes) * 100.0
        elapsed = time.monotonic() - self.start_time
        if processed_bytes > 0 and elapsed > 0:
            speed = processed_bytes / elapsed
            remaining = total_bytes - processed_bytes
            eta_seconds = int(remaining / speed) if speed > 0 else 0
        else:
            eta_seconds = 0
        minutes, seconds = divmod(eta_seconds, 60)
        eta_str = f"{minutes:02d}:{seconds:02d}"

        try:
            self.progress["value"] = percent

            subdir_name = current_subdir.name if current_subdir else ""
            self.label_subdir.configure(text=f"Subpasta {current_index}/{total_subdirs}: {subdir_name}")
            self.label_bytes.configure(
                text=f"{processed_bytes // 1024} KB de {total_bytes // 1024} KB (~{percent:.1f}%)"
            )
            self.label_eta.configure(text=f"Tempo estimado: {eta_str}")

            self.update_idletasks()
        except tk.TclError:
            self._closed = True

    def close(self) -> None:
        self._on_close()

    def _center_on_parent(self) -> None:
        try:
            self.update_idletasks()
            show_centered(self)
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao centralizar PDFBatchProgressDialog: %s", exc)

    def _on_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except tk.TclError:
            pass

    @property
    def is_closed(self) -> bool:
        if self._closed:
            return True
        try:
            return not self.winfo_exists()
        except tk.TclError:
            return True
