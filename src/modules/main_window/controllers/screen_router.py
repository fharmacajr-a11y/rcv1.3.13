# -*- coding: utf-8 -*-
"""ScreenRouter headless para gerenciar troca de telas no MainWindow.

REFATORAÇÃO: Extração da lógica de roteamento do MainWindow
- Centraliza show/hide de telas com cache
- Mantém apenas uma tela visível por vez
- Reutiliza instâncias de telas (cache) quando aplicável
- Headless: não importa Tkinter diretamente
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

_log = logging.getLogger(__name__)


class ScreenRouter:
    """Router headless para gerenciar navegação entre telas.

    Responsabilidades:
    - Registrar factories de telas
    - Criar/cachear instâncias de telas
    - Esconder tela atual e mostrar nova tela
    - Manter referência à tela atual
    """

    def __init__(
        self,
        container: Any,
        *,
        logger: Optional[logging.Logger] = None,
    ):
        """Inicializa o router.

        Args:
            container: Widget container onde telas serão montadas
            logger: Logger customizado (opcional)
        """
        self._container = container
        self._log = logger or _log

        # Registro de factories: name -> (factory, cache_policy)
        self._factories: dict[str, tuple[Callable[[], Any], bool]] = {}

        # Cache de instâncias: name -> screen_instance
        self._cache: dict[str, Any] = {}

        # Tela atual
        self._current_name: Optional[str] = None
        self._current_screen: Optional[Any] = None

    def register(
        self,
        name: str,
        factory: Callable[[], Any],
        *,
        cache: bool = True,
    ) -> None:
        """Registra uma factory de tela.

        Args:
            name: Nome único da tela (ex: "hub", "main", "cashflow")
            factory: Função que cria a tela (sem argumentos)
            cache: Se True, reutiliza instância; se False, cria nova a cada show()
        """
        self._factories[name] = (factory, cache)
        self._log.debug("Tela registrada: %s (cache=%s)", name, cache)

    def show(self, name: str) -> Any:
        """Mostra uma tela, escondendo a anterior.

        Args:
            name: Nome da tela registrada

        Returns:
            Instância da tela mostrada

        Raises:
            ValueError: Se tela não foi registrada
        """
        if name not in self._factories:
            raise ValueError(f"Tela não registrada: {name}")

        factory, should_cache = self._factories[name]

        # Buscar ou criar instância
        if should_cache and name in self._cache:
            screen = self._cache[name]
            self._log.debug("Reutilizando instância cacheada: %s", name)
        else:
            self._log.debug("Criando nova instância: %s", name)
            screen = factory()

            if should_cache:
                self._cache[name] = screen

        # Esconder tela atual (se houver)
        if self._current_screen is not None and self._current_screen is not screen:
            # Correção para BUG #6: cover temporário com APP_BG para evitar
            # exposição do content_container preto durante a transição.
            cover = self._place_transition_cover()
            self._hide_screen(self._current_screen)
        else:
            cover = None

        # Mostrar nova tela
        self._show_screen(screen)

        # Correção para BUG #6: remover cover após nova tela estar visível
        if cover is not None:
            self._remove_transition_cover(cover)

        # Atualizar estado
        self._current_name = name
        self._current_screen = screen

        return screen

    def current_name(self) -> Optional[str]:
        """Retorna nome da tela atual (ou None se nenhuma)."""
        return self._current_name

    def current_screen(self) -> Optional[Any]:
        """Retorna instância da tela atual (ou None se nenhuma)."""
        return self._current_screen

    def clear_cache(self, name: Optional[str] = None) -> None:
        """Limpa cache de telas.

        Args:
            name: Nome da tela para limpar (se None, limpa todas)
        """
        if name is None:
            self._cache.clear()
            self._log.debug("Cache completo limpo")
        elif name in self._cache:
            del self._cache[name]
            self._log.debug("Cache limpo: %s", name)

    # ===== Métodos de UI (com tratamento de erros) =====

    def _hide_screen(self, screen: Any) -> None:
        """Esconde uma tela (pack_forget/place_forget)."""
        try:
            screen.pack_forget()
        except Exception as exc:  # noqa: BLE001
            self._log.debug("pack_forget failed, trying place_forget: %s", exc)
            try:
                screen.place_forget()
            except Exception as exc2:  # noqa: BLE001
                self._log.debug("place_forget also failed: %s", exc2)

    def _show_screen(self, screen: Any) -> None:
        """Mostra uma tela (place ou pack + lift)."""
        # Tentar place primeiro (melhor para sobreposição)
        try:
            screen.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as exc:  # noqa: BLE001
            self._log.debug("place failed, trying pack: %s", exc)
            try:
                screen.pack(fill="both", expand=True)
            except Exception as exc2:  # noqa: BLE001
                self._log.debug("pack also failed: %s", exc2)

        # Trazer para frente
        try:
            screen.lift()
        except Exception as exc:  # noqa: BLE001
            self._log.debug("lift failed: %s", exc)

    # Correção para BUG #6: helpers de cover temporário

    def _place_transition_cover(self) -> Any:
        """Cria frame opaco sobre o container para mascarar transição."""
        try:
            import tkinter as _tk
            from src.ui.ui_tokens import APP_BG
            from src.ui.ctk_config import ctk as _ctk

            if _ctk is not None:
                cover = _ctk.CTkFrame(
                    self._container,
                    fg_color=APP_BG,
                    corner_radius=0,
                )
            else:
                # Auditoria Anti-Flash: respeitar modo de aparência atual
                if isinstance(APP_BG, tuple):
                    try:
                        import customtkinter as _ctk_mod

                        bg = APP_BG[1] if _ctk_mod.get_appearance_mode().lower() == "dark" else APP_BG[0]
                    except Exception:  # noqa: BLE001
                        bg = APP_BG[1]
                else:
                    bg = APP_BG
                cover = _tk.Frame(self._container, bg=bg)
            cover.place(relx=0, rely=0, relwidth=1, relheight=1)
            cover.lift()
            return cover
        except Exception as exc:  # noqa: BLE001
            self._log.debug("Falha ao criar transition cover: %s", exc)
            return None

    @staticmethod
    def _remove_transition_cover(cover: Any) -> None:
        """Remove cover temporário."""
        try:
            cover.destroy()
        except Exception:  # noqa: BLE001
            pass
