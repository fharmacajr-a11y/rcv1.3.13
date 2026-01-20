"""DEPRECATED UI MODULE - Menu Bar Antiga

Este módulo pertence à UI antiga (pré-modules/*).
Mantido apenas como referência histórica.

NOVO CÓDIGO DEVE USAR:
  - Menu específico de cada módulo em src.modules.*/views/
  - Ou componentes de menu em src.ui.components/

MICROFASE 24: Removido seletor de temas legado.
Agora usa apenas toggle Light/Dark via CustomTkinter.
"""

# gui/menu_bar.py
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

_log = logging.getLogger(__name__)


class AppMenuBar(tk.Menu):
    def __init__(
        self,
        master: tk.Misc,
        *,
        on_home: Optional[Callable[[], None]] = None,
        on_refresh: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_toggle_theme: Optional[Callable[[], None]] = None,
    ) -> None:
        """Inicializa o menu bar.

        MICROFASE 24: Substituído on_change_theme(name) por on_toggle_theme()
        para alternar entre light/dark apenas.
        """
        super().__init__(master, tearoff=False)
        self._on_home = on_home
        self._on_refresh = on_refresh
        self._on_quit = on_quit
        self._on_toggle_theme = on_toggle_theme

        # Opções
        menu_arquivo = tk.Menu(self, tearoff=False)
        menu_arquivo.add_command(label="Início", command=self._safe(self._on_home))
        menu_arquivo.add_command(label="Atualizar", command=self._safe(self._on_refresh))
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Encerrar sessão…", command=self._safe(self._on_quit))
        self.add_cascade(label="Opções", menu=menu_arquivo)
        self._menu_arquivo = menu_arquivo

        # Exibir > Alternar Tema (Light/Dark)
        menu_exibir = tk.Menu(self, tearoff=False)
        menu_exibir.add_command(
            label="Alternar Tema (Light/Dark)",
            command=self._safe(self._on_toggle_theme),
        )
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
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao anexar menu: %s", exc)

    # MICROFASE 24: refresh_theme agora é no-op (compatibilidade)
    def refresh_theme(self, current: Optional[str]) -> None:
        """Mantido para compatibilidade, mas não faz nada (tema gerenciado por CustomTkinter)."""
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
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao executar callback de menu: %s", exc)

        return _wrap

    def _about(self) -> None:
        try:
            messagebox.showinfo("Sobre", "RC - Gestor de Clientes", parent=self.master)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao exibir diálogo Sobre: %s", exc)

    def _sync_home_state(self) -> None:
        try:
            state = "disabled" if self._is_hub else "normal"
            self._menu_arquivo.entryconfig(0, state=state)  # "Início" é o item 0
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao sincronizar estado do menu Início: %s", exc)
