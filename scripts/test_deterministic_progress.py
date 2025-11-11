#!/usr/bin/env python3
"""
Script de teste para validar barra de progresso determinística.
Simula upload com tracking de %, MB/s, ETA e contagem de itens.

Uso:
    python scripts/test_deterministic_progress.py
"""
from __future__ import annotations

import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

from ttkbootstrap import ttk


@dataclass
class _ProgressState:
    """Estado do progresso de upload para barra determinística."""
    total_files: int = 0
    total_bytes: int = 0
    done_files: int = 0
    done_bytes: int = 0
    start_ts: float = 0.0
    ema_bps: float = 0.0  # Exponential Moving Average de bytes por segundo


class TestProgressWindow(tk.Tk):
    """Janela de teste para progresso determinístico."""

    def __init__(self):
        super().__init__()
        self.title("Teste: Barra de Progresso Determinística")
        self.geometry("500x300")
        self.resizable(False, False)

        # Label de instruções
        lbl_info = ttk.Label(
            self,
            text="Clique em 'Iniciar' para simular upload com progresso determinístico",
            font=("-size", 10),
            wraplength=460
        )
        lbl_info.pack(padx=20, pady=(20, 16))

        # Botão de iniciar
        self.btn_start = ttk.Button(self, text="Iniciar Simulação", command=self._start_test)
        self.btn_start.pack(pady=(0, 20))

        # Frame do progresso (inicialmente oculto)
        self.progress_frame = ttk.Frame(self)
        
        # Label de mensagem
        self.lbl_msg = ttk.Label(self.progress_frame, text="Enviando arquivos...", font=("-size", 10))
        self.lbl_msg.pack(padx=20, pady=(12, 8))

        # Progressbar
        self.pb = ttk.Progressbar(self.progress_frame, mode="determinate", length=420, maximum=100)
        self.pb.pack(padx=20, pady=(0, 8), fill="x")

        # Label de status (% e itens)
        self.lbl_status = ttk.Label(self.progress_frame, text="0% — 0/0 itens", font=("-size", 9))
        self.lbl_status.pack(padx=20, pady=(0, 4))

        # Label de ETA e velocidade
        self.lbl_eta = ttk.Label(self.progress_frame, text="00:00:00 restantes @ 0.0 MB/s", font=("-size", 9), foreground="#666")
        self.lbl_eta.pack(padx=20, pady=(0, 12))

        self._cancel_flag = False

    def _fmt_eta(self, seconds: float) -> str:
        """Formata segundos em HH:MM:SS."""
        if seconds <= 0:
            return "00:00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _progress_update_ui(self, state: _ProgressState, alpha: float = 0.2) -> None:
        """
        Atualiza UI da barra de progresso.

        Args:
            state: Estado atual do progresso
            alpha: Fator de suavização EMA (0.2 = suave)
        """
        # Calcular velocidade instantânea
        elapsed = time.monotonic() - state.start_ts
        if elapsed > 0:
            instant_bps = state.done_bytes / elapsed
            # EMA para suavizar
            if state.ema_bps == 0:
                state.ema_bps = instant_bps
            else:
                state.ema_bps = alpha * instant_bps + (1 - alpha) * state.ema_bps

        # Calcular % e ETA
        pct = 0.0
        eta_str = "00:00:00"
        speed_str = "0.0 MB/s"

        if state.total_bytes > 0:
            pct = (state.done_bytes / state.total_bytes) * 100
            if state.ema_bps > 0:
                remaining_bytes = state.total_bytes - state.done_bytes
                eta_sec = remaining_bytes / state.ema_bps
                eta_str = self._fmt_eta(eta_sec)
                speed_str = f"{state.ema_bps / 1_048_576:.1f} MB/s"

        # Atualizar barra
        self.pb["value"] = pct

        # Atualizar labels
        status_text = f"{pct:.0f}% — {state.done_files}/{state.total_files} itens"
        self.lbl_status.configure(text=status_text)

        eta_text = f"{eta_str} restantes @ {speed_str}"
        self.lbl_eta.configure(text=eta_text)

    def _start_test(self) -> None:
        """Inicia simulação de upload."""
        self.btn_start.configure(state="disabled")
        self.progress_frame.pack(padx=20, pady=(0, 20), fill="both", expand=True)

        # Simular 50 arquivos, tamanhos variados (1-10 MB)
        import random
        state = _ProgressState()
        state.total_files = 50
        state.total_bytes = sum(random.randint(1_000_000, 10_000_000) for _ in range(50))
        state.start_ts = time.monotonic()

        file_sizes = [random.randint(1_000_000, 10_000_000) for _ in range(50)]

        def _simulate_upload(idx: int = 0):
            if idx >= state.total_files:
                # Concluído
                self.lbl_msg.configure(text="✓ Upload concluído!")
                self.pb["value"] = 100
                self.lbl_status.configure(text=f"100% — {state.total_files}/{state.total_files} itens")
                self.lbl_eta.configure(text="00:00:00 restantes @ 0.0 MB/s")
                return

            # Simular upload de 1 arquivo (delay variável)
            delay = random.randint(50, 200)  # 50-200ms por arquivo
            state.done_files = idx + 1
            state.done_bytes += file_sizes[idx]

            # Atualizar UI
            self._progress_update_ui(state)

            # Próximo arquivo
            self.after(delay, lambda: _simulate_upload(idx + 1))

        # Iniciar simulação
        _simulate_upload()


if __name__ == "__main__":
    print("=== Teste: Barra de Progresso Determinística ===")
    print("\n📊 Validações:")
    print("  ✓ Barra muda de 0% → 100%")
    print("  ✓ % é exibido corretamente")
    print("  ✓ Contador de itens (done/total)")
    print("  ✓ MB/s calculado com EMA (suavizado)")
    print("  ✓ ETA formatado HH:MM:SS")
    print("  ✓ ETA diminui conforme progresso")
    print("\n" + "=" * 50)

    app = TestProgressWindow()
    app.mainloop()

    print("\n✅ Teste concluído. Verifique:")
    print("  - Barra progrediu suavemente")
    print("  - % exibido de 0 → 100")
    print("  - MB/s teve valores realistas")
    print("  - ETA diminuiu conforme progresso")
    print("  - Contador de itens correto (1/50 → 50/50)")
