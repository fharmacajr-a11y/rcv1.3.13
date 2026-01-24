"""Diálogos auxiliares utilizados pela tela principal de Auditoria."""

from __future__ import annotations

import logging
import time
import tkinter as tk

from typing import Callable, Protocol

from src.ui.components.progress_dialog import ProgressDialog
from src.ui.window_utils import show_centered
from src.ui.widgets import CTkTableView

logger = logging.getLogger(__name__)

__all__ = ["UploadProgressDialog", "DuplicatesDialog"]


class _ProgressState(Protocol):
    """Protocol para estado de progresso de upload."""

    start_ts: float
    done_bytes: int
    total_bytes: int
    done_files: int
    total_files: int
    ema_bps: float


class UploadProgressDialog:
    """Wrapper que utiliza ProgressDialog para exibir progresso detalhado."""

    def __init__(self, parent: tk.Misc, title: str, message: str, on_cancel: Callable[[], None] | None = None):
        self._dialog = ProgressDialog(
            parent,
            title=title,
            message=message,
            detail="0% - 0/0 itens",
            can_cancel=on_cancel is not None,
            on_cancel=on_cancel,
        )
        self._dialog.set_progress(0.0)
        self._dialog.set_eta_text("00:00:00 restantes @ 0.0 MB/s")

    def update_with_state(self, state: "_ProgressState", alpha: float = 0.2) -> None:
        """Atualiza a UI com base no estado atual do upload."""
        if not self._dialog:
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

        status_text = f"{pct:.0f}% - {state.done_files}/{state.total_files} itens - {bytes_text}"
        eta_text = self._format_eta_text(eta_sec, state.ema_bps)

        try:
            self._dialog.set_detail(status_text)
            self._dialog.set_eta_text(eta_text)
            self._dialog.set_progress(pct / 100 if state.total_bytes > 0 else 0.0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar UploadProgressDialog: %s", exc)

    def close(self) -> None:
        """Fecha o modal."""
        if not self._dialog:
            return
        try:
            self._dialog.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao destruir UploadProgressDialog: %s", exc)
        finally:
            self._dialog = None

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
        self.withdraw()
        self.title("Duplicatas Detectadas")

        if hasattr(parent, "winfo_toplevel"):
            self.transient(parent.winfo_toplevel())

        self.resizable(False, False)

        self.strategy: str | None = None
        self.apply_once: bool = True

        msg = f"Encontrados {duplicates_count} arquivo(s) duplicado(s).\nEscolha como proceder:"
        ctk.CTkLabel(self, text=msg, font=("-size", 10), wraplength=520).pack(padx=20, pady=(20, 10))

        # Frame amostra com label
        sample_container = ctk.CTkFrame(self)
        sample_container.pack(padx=20, pady=(0, 12), fill="both", expand=True)
        ctk.CTkLabel(sample_container, text="Amostra (até 20 arquivos)", font=("-size", 10, "bold")).pack(
            anchor="w", padx=8, pady=(4, 2)
        )
        frame_sample = ctk.CTkFrame(sample_container)
        frame_sample.pack(padx=8, pady=(0, 8), fill="both", expand=True)

        tree_frame = ctk.CTkFrame(frame_sample)
        tree_frame.pack(fill="both", expand=True)

        height = min(len(sample_names[:20]), 10)
        self.tree_sample = CTkTableView(
            tree_frame, columns=("arquivo",), show="tree headings", height=height, selectmode="none", zebra=True
        )
        self.tree_sample.heading("#0", text="")
        self.tree_sample.heading("arquivo", text="Arquivo", anchor="w")
        self.tree_sample.column("#0", width=0, stretch=False)
        self.tree_sample.column("arquivo", width=500, anchor="w", stretch=True)

        self.tree_sample.pack(side="left", fill="both", expand=True)

        for name in sample_names[:20]:
            self.tree_sample.insert("", "end", values=[name])
        if len(sample_names) > 20:
            remaining = len(sample_names) - 20
            self.tree_sample.insert("", "end", values=[f"... e mais {remaining} arquivo(s)"])

        self.var_apply_once = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self,
            text="Não aplicar só a este envio (não lembrar esta escolha)",
            variable=self.var_apply_once,
        ).pack(padx=20, pady=(0, 12), anchor="w")

        # Frame estratégia com label
        opts_container = ctk.CTkFrame(self)
        opts_container.pack(padx=20, pady=(0, 10), fill="x")
        ctk.CTkLabel(opts_container, text="Estratégia", font=("-size", 10, "bold")).pack(
            anchor="w", padx=8, pady=(4, 2)
        )
        frame_opts = ctk.CTkFrame(opts_container)
        frame_opts.pack(padx=8, pady=(0, 8), fill="x")

        self.var_strategy = tk.StringVar(value="skip")

        ctk.CTkRadioButton(
            frame_opts,
            text="Pular duplicatas (não envia arquivos que já existem)",
            variable=self.var_strategy,
            value="skip",
        ).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(
            frame_opts,
            text="Substituir duplicatas (sobrescrever com novos arquivos)",
            variable=self.var_strategy,
            value="replace",
        ).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(
            frame_opts,
            text="Renomear duplicatas (sufixo arquivo (2).pdf)",
            variable=self.var_strategy,
            value="rename",
        ).pack(anchor="w", pady=2)

        frame_buttons = ctk.CTkFrame(self)
        frame_buttons.pack(padx=20, pady=(0, 20))

        btn_ok = ctk.CTkButton(frame_buttons, text="OK", command=self._on_ok, width=12)
        btn_ok.pack(side="left", padx=5)

        ctk.CTkButton(frame_buttons, text="Cancelar", command=self._on_cancel, width=12).pack(side="left", padx=5)

        try:
            self.update_idletasks()
            show_centered(self)
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar DuplicatesDialog: %s", exc)

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
