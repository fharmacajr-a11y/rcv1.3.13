from __future__ import annotations

import tkinter as tk
from tkinter import ttk

CLOUD_COLORS = {
    "ONLINE": "#22c55e",
    "OFFLINE": "#ef4444",
    "UNKNOWN": "#a3a3a3",
}


class StatusFooter(ttk.Frame):
    def __init__(self, master, on_lixeira_click=None, show_trash=False):
        super().__init__(master)
        self.configure(padding=(6, 2, 6, 2))
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        self._lbl_count = ttk.Label(self, text="")
        self._lbl_count.grid(row=0, column=0, sticky="w", padx=(6, 0), pady=3)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="e", padx=6, pady=2)

        self._dot = tk.Canvas(right, width=14, height=14, highlightthickness=0, bd=0)
        self._dot.create_oval(2, 2, 12, 12, fill=CLOUD_COLORS["UNKNOWN"], outline="")
        self._lbl_cloud = ttk.Label(right, text="Nuvem: Desconhecido")

        sep = ttk.Label(right, text="  •  ")
        self._lbl_user = ttk.Label(right, text="Usuário: —")

        self._dot.grid(row=0, column=0, sticky="e")
        self._lbl_cloud.grid(row=0, column=1, sticky="e", padx=(6, 0))
        sep.grid(row=0, column=2, sticky="e")
        self._lbl_user.grid(row=0, column=3, sticky="e", padx=(0, 6))

        # Botão Lixeira opcional (apenas se show_trash=True)
        self._btn_lixeira = None
        if show_trash and on_lixeira_click:
            self._btn_lixeira = ttk.Button(
                right, text="Lixeira", command=on_lixeira_click
            )
            self._btn_lixeira.grid(row=0, column=4, sticky="e")

        self._cloud_state = "UNKNOWN"
        self._user_email = None
        self._count_text = ""

    def set_count(self, total: int | str):
        self._count_text = (
            f"{total} cliente(s)" if isinstance(total, int) else str(total)
        )
        self._lbl_count.config(text=self._count_text)

    def set_user(self, email: str | None):
        self._user_email = email or "—"
        self._lbl_user.config(text=f"Usuário: {self._user_email}")

    def set_cloud(self, state: str):
        state = (state or "UNKNOWN").upper()
        if state not in CLOUD_COLORS:
            state = "UNKNOWN"
        if state == self._cloud_state:
            return
        self._cloud_state = state
        color = CLOUD_COLORS[state]
        self._dot.itemconfig(1, fill=color)
        label = {"ONLINE": "Online", "OFFLINE": "Offline", "UNKNOWN": "Desconhecido"}[
            state
        ]
        self._lbl_cloud.config(text=f"Nuvem: {label}")
