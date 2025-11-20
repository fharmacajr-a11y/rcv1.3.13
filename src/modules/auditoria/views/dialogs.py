"""Diálogos auxiliares utilizados pela tela principal de Auditoria."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .main_frame import _ProgressState

__all__ = ["UploadProgressDialog", "DuplicatesDialog"]


class UploadProgressDialog:
    """Janela modal que acompanha envio de arquivos com barra de progresso e ETA."""

    def __init__(self, parent: tk.Misc, title: str, message: str, on_cancel: Callable[[], None] | None = None):
        self._cancel_callback = on_cancel
        self._window = tk.Toplevel(parent.winfo_toplevel())
        self._window.title(title)
        self._window.transient(parent)
        self._window.grab_set()
        self._window.resizable(False, False)

        self._window.update_idletasks()
        width, height = 420, 220
        pos_x = (self._window.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self._window.winfo_screenheight() // 2) - (height // 2)
        self._window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        ttk.Label(self._window, text=message, font=("-size", 10)).pack(padx=20, pady=(20, 12))

        self._progress = ttk.Progressbar(self._window, mode="determinate", length=360, maximum=100)
        self._progress.pack(padx=20, pady=(0, 8), fill="x")
        self._progress["value"] = 0

        self._status_label = ttk.Label(self._window, text="0% — 0/0 itens", font=("-size", 9))
        self._status_label.pack(padx=20, pady=(0, 4))

        self._eta_label = ttk.Label(self._window, text="00:00:00 restantes @ 0.0 MB/s", font=("-size", 9), foreground="#666")
        self._eta_label.pack(padx=20, pady=(0, 16))

        self._cancel_button = ttk.Button(self._window, text="Cancelar", command=self._on_cancel)
        self._cancel_button.pack(pady=(0, 20))

    def update_with_state(self, state: "_ProgressState", alpha: float = 0.2) -> None:
        """Atualiza a UI com base no estado atual do upload."""
        if self._window is None:
            return

        elapsed = time.monotonic() - state.start_ts
        if elapsed > 0:
            instant_bps = state.done_bytes / elapsed
            state.ema_bps = instant_bps if state.ema_bps == 0 else alpha * instant_bps + (1 - alpha) * state.ema_bps

        pct = 0.0
        eta_sec = 0.0
        bytes_text = "0 B / 0 B"

        if state.total_bytes > 0:
            pct = (state.done_bytes / state.total_bytes) * 100
            bytes_text = f"{self._fmt_bytes(state.done_bytes)} / {self._fmt_bytes(state.total_bytes)}"

            if state.ema_bps > 0:
                remaining_bytes = state.total_bytes - state.done_bytes
                eta_sec = remaining_bytes / state.ema_bps

        status_text = f"{pct:.0f}% — {state.done_files}/{state.total_files} itens — {bytes_text}"
        self._status_label.configure(text=status_text)

        eta_text = self._format_eta_text(eta_sec, state.ema_bps)
        self._eta_label.configure(text=eta_text)

        self._progress["value"] = pct

    def close(self) -> None:
        """Fecha o modal."""
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass
            finally:
                self._window = None

    def _on_cancel(self) -> None:
        if self._cancel_button["state"] == "disabled":
            return
        self._cancel_button.configure(state="disabled", text="Cancelando...")
        if self._cancel_callback:
            self._cancel_callback()

    def _format_eta_text(self, eta_sec: float, ema_bps: float) -> str:
        if eta_sec <= 0 or ema_bps <= 0:
            return "00:00:00 restantes @ 0.0 MB/s"

        if eta_sec < 3600:
            minutes = int(eta_sec // 60)
            seconds = int(eta_sec % 60)
            eta_formatted = f"{minutes:02d}:{seconds:02d}"
            prefix = "ETA ~"
        else:
            eta_formatted = self._fmt_eta(eta_sec)
            prefix = ""

        speed = f"{ema_bps / 1_048_576:.1f} MB/s"
        return f"{prefix} {eta_formatted} @ {speed}".strip()

    def _fmt_eta(self, seconds: float) -> str:
        if seconds <= 0:
            return "00:00:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _fmt_bytes(self, value: int) -> str:
        if value < 1024:
            return f"{value} B"
        if value < 1_048_576:
            return f"{value / 1024:.1f} KB"
        if value < 1_073_741_824:
            return f"{value / 1_048_576:.1f} MB"
        return f"{value / 1_073_741_824:.1f} GB"


class DuplicatesDialog(tk.Toplevel):
    """Janela modal para definir a estratégia diante de arquivos duplicados."""

    def __init__(self, parent: tk.Misc, duplicates_count: int, sample_names: list[str]):
        super().__init__(parent)
        self.title("Duplicatas Detectadas")

        if hasattr(parent, "winfo_toplevel"):
            self.transient(parent.winfo_toplevel())

        self.grab_set()
        self.resizable(False, False)

        self.strategy: str | None = None
        self.apply_once: bool = True

        self.update_idletasks()
        width = 560
        height = 480
        pos_x = (self.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        msg = f"Encontrados {duplicates_count} arquivo(s) duplicado(s).\nEscolha como proceder:"
        ttk.Label(self, text=msg, font=("-size", 10), wraplength=520).pack(padx=20, pady=(20, 10))

        frame_sample = ttk.LabelFrame(self, text="Amostra (até 20 arquivos)", padding=10)
        frame_sample.pack(padx=20, pady=(0, 12), fill="both", expand=True)

        tree_frame = ttk.Frame(frame_sample)
        tree_frame.pack(fill="both", expand=True)

        height = min(len(sample_names[:20]), 10)
        self.tree_sample = ttk.Treeview(tree_frame, columns=("arquivo",), show="tree headings", height=height, selectmode="none")
        self.tree_sample.heading("#0", text="")
        self.tree_sample.heading("arquivo", text="Arquivo", anchor="w")
        self.tree_sample.column("#0", width=0, stretch=False)
        self.tree_sample.column("arquivo", width=500, anchor="w", stretch=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_sample.yview)
        self.tree_sample.configure(yscrollcommand=scrollbar.set)
        self.tree_sample.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for name in sample_names[:20]:
            self.tree_sample.insert("", "end", values=(name,))
        if len(sample_names) > 20:
            remaining = len(sample_names) - 20
            self.tree_sample.insert("", "end", values=(f"... e mais {remaining} arquivo(s)",))

        self.var_apply_once = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self,
            text="Não aplicar só a este envio (não lembrar esta escolha)",
            variable=self.var_apply_once,
        ).pack(padx=20, pady=(0, 12), anchor="w")

        frame_opts = ttk.LabelFrame(self, text="Estratégia", padding=10)
        frame_opts.pack(padx=20, pady=(0, 16), fill="x")

        self.var_strategy = tk.StringVar(value="skip")

        ttk.Radiobutton(
            frame_opts,
            text="Pular duplicatas (não envia arquivos que já existem)",
            variable=self.var_strategy,
            value="skip",
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            frame_opts,
            text="Substituir duplicatas (sobrescrever com novos arquivos)",
            variable=self.var_strategy,
            value="replace",
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            frame_opts,
            text="Renomear duplicatas (sufixo arquivo (2).pdf)",
            variable=self.var_strategy,
            value="rename",
        ).pack(anchor="w", pady=2)

        frame_buttons = ttk.Frame(self)
        frame_buttons.pack(padx=20, pady=(0, 20))

        btn_ok = ttk.Button(frame_buttons, text="OK", command=self._on_ok, width=12)
        btn_ok.pack(side="left", padx=5)

        ttk.Button(frame_buttons, text="Cancelar", command=self._on_cancel, width=12).pack(side="left", padx=5)

        btn_ok.focus_set()
        self.bind("<Return>", lambda _event: self._on_ok())
        self.bind("<Escape>", lambda _event: self._on_cancel())

    def _on_ok(self) -> None:
        self.strategy = self.var_strategy.get()
        self.apply_once = self.var_apply_once.get()
        self.destroy()

    def _on_cancel(self) -> None:
        self.strategy = None
        self.apply_once = True
        self.destroy()
