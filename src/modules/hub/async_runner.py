# -*- coding: utf-8 -*-
"""HubAsyncRunner: helper para executar tarefas assíncronas do HUB.

Este componente orquestra a execução de operações de I/O em background (threads)
e garante que callbacks sejam executados na thread principal do Tkinter.

Não contém lógica de negócio; é apenas um helper de orquestração.
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass
class HubAsyncRunner:
    """Executa tarefas assíncronas do HUB e retorna callbacks no main thread.

    Attributes:
        tk_root: Widget Tkinter para agendar callbacks via .after()
        logger: Logger opcional para registrar erros
    """

    tk_root: tk.Misc
    logger: logging.Logger | None = None

    def run(
        self,
        func: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Executa func() em background e chama callbacks no main thread.

        Args:
            func: Função a ser executada em thread separada (sem parâmetros)
            on_success: Callback chamado no main thread com o resultado
            on_error: Callback chamado no main thread em caso de exceção

        Example:
            runner.run(
                func=lambda: expensive_operation(),
                on_success=lambda result: update_ui(result),
                on_error=lambda exc: show_error(exc),
            )
        """

        def _worker() -> None:
            try:
                result = func()
            except Exception as exc:  # noqa: BLE001
                if self.logger:
                    self.logger.exception(
                        "Erro em tarefa assíncrona do HUB",
                        exc_info=exc,
                    )
                # Garantir retorno no main thread
                self.tk_root.after(0, on_error, exc)
            else:
                self.tk_root.after(0, on_success, result)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
