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
            name: Nome único da tela (ex: "hub", "main", "passwords")
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
            self._hide_screen(self._current_screen)

        # Mostrar nova tela
        self._show_screen(screen)

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
