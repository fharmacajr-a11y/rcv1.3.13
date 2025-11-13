# gui/menu_bar.py
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Iterable, Optional


def _available_themes() -> Iterable[str]:
    try:
        from src.utils import theme_manager as tm

        names = getattr(tm, "available_themes", None)
        if callable(names):
            return list(names())
        names = getattr(tm, "THEMES", None)
        if isinstance(names, (list, tuple, set)):
            return list(names)
    except Exception:
        pass
    return [
        "flatly",
        "cosmo",
        "darkly",
        "litera",
        "morph",
        "pulse",
        "sandstone",
        "solar",
        "superhero",
        "yeti",
    ]


class AppMenuBar(tk.Menu):
    def __init__(
        self,
        master: tk.Misc,
        *,
        on_home: Optional[Callable[[], None]] = None,
        on_open_subpastas: Optional[Callable[[], None]] = None,
        on_open_lixeira: Optional[Callable[[], None]] = None,
        on_upload: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_change_theme: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(master, tearoff=False)
        self._on_home = on_home
        self._on_open_subpastas = on_open_subpastas
        self._on_open_lixeira = on_open_lixeira
        self._on_upload = on_upload
        self._on_quit = on_quit
        self._on_change_theme = on_change_theme

        # Arquivo
        menu_arquivo = tk.Menu(self, tearoff=False)
        menu_arquivo.add_command(label="Início", command=self._handle_home)
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Subpastas", command=self._safe(self._on_open_subpastas))
        menu_arquivo.add_command(label="Lixeira", command=self._safe(self._on_open_lixeira))
        menu_arquivo.add_command(label="Enviar para Supabase", command=self._safe(self._on_upload))
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Sair", command=self._safe(self._on_quit))
        self.add_cascade(label="Arquivo", menu=menu_arquivo)
        self._menu_arquivo = menu_arquivo

        # Exibir > Tema
        menu_exibir = tk.Menu(self, tearoff=False)
        self._theme_var = tk.StringVar(value="")
        menu_tema = tk.Menu(menu_exibir, tearoff=False)
        for name in _available_themes():
            menu_tema.add_radiobutton(
                label=name,
                value=name,
                variable=self._theme_var,
                command=lambda n=name: self._handle_change_theme(n),
            )
        menu_exibir.add_cascade(label="Tema", menu=menu_tema)
        self.add_cascade(label="Exibir", menu=menu_exibir)

        # Ajuda
        menu_ajuda = tk.Menu(self, tearoff=False)
        menu_ajuda.add_command(label="Sobre", command=self._about)
        self.add_cascade(label="Ajuda", menu=menu_ajuda)

        self._is_hub = False
        self._sync_home_state()

    def attach(self) -> None:
        try:
            self.master.configure(menu=self)
        except Exception:
            pass

    def refresh_theme(self, current: Optional[str]) -> None:
        try:
            self._theme_var.set(current or "")
        except Exception:
            pass

    def set_is_hub(self, is_hub: bool) -> None:
        self._is_hub = bool(is_hub)
        self._sync_home_state()

    # ------- handlers -------
    def _safe(self, fn: Optional[Callable[[], None]]):
        def _wrap():
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass

        return _wrap

    def _handle_home(self) -> None:
        if callable(self._on_home):
            try:
                self._on_home()
            except Exception:
                pass

    def _handle_change_theme(self, name: str) -> None:
        if callable(self._on_change_theme):
            try:
                self._on_change_theme(name)
            except Exception:
                pass
        self.refresh_theme(name)

    def _about(self) -> None:
        try:
            messagebox.showinfo("Sobre", "RC - Gestor de Clientes", parent=self.master)
        except Exception:
            pass

    def _sync_home_state(self) -> None:
        try:
            state = "disabled" if self._is_hub else "normal"
            self._menu_arquivo.entryconfig(0, state=state)  # "Início" é o item 0
        except Exception:
            pass
