# -*- coding: utf-8 -*-
"""HubAsyncRunner: helper para executar tarefas assíncronas do HUB.

Este componente orquestra a execução de operações de I/O em background (threads)
e garante que callbacks sejam executados na thread principal do Tkinter.

FASE 5A: Refatorado para usar ThreadPoolExecutor e suportar shutdown seguro.
"""

from __future__ import annotations

import logging
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass
class HubAsyncRunner:
    """Executa tarefas assíncronas do HUB e retorna callbacks no main thread.

    FASE 5A: Refatorado para usar ThreadPoolExecutor (pool fixo) e permitir
    shutdown gracioso com cancelamento de callbacks pendentes.

    Attributes:
        tk_root: Widget Tkinter para agendar callbacks via .after()
        logger: Logger opcional para registrar erros
    """

    tk_root: tk.Misc
    logger: logging.Logger | None = None
    _executor: ThreadPoolExecutor = field(default=None, init=False, repr=False)
    _pending_after_ids: list[str] = field(default_factory=list, init=False, repr=False)
    _shutdown: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        """Inicializa ThreadPoolExecutor após criação do dataclass."""
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="HubAsync")
        if self.logger:
            self.logger.debug("HubAsyncRunner: ThreadPoolExecutor criado (max_workers=4)")

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
        if self._shutdown:
            if self.logger:
                self.logger.debug("HubAsyncRunner: ignorando run() - já em shutdown")
            return

        def _worker() -> None:
            try:
                result = func()
            except Exception as exc:  # noqa: BLE001
                if self.logger:
                    self.logger.exception(
                        "Erro em tarefa assíncrona do HUB",
                        exc_info=exc,
                    )
                # Garantir retorno no main thread com verificação de widget válido
                self._schedule_callback(lambda: on_error(exc))
            else:
                self._schedule_callback(lambda: on_success(result))

        self._executor.submit(_worker)

    def _schedule_callback(self, callback: Callable[[], None]) -> None:
        """Agenda callback no main thread com verificação de widget válido."""
        if self._shutdown:
            if self.logger:
                self.logger.debug("HubAsyncRunner: callback ignorado (shutdown)")
            return

        try:
            # Verificar se tk_root ainda existe
            if not self.tk_root.winfo_exists():
                if self.logger:
                    self.logger.debug("HubAsyncRunner: widget destruído, ignorando callback")
                return
        except tk.TclError:
            if self.logger:
                self.logger.debug("HubAsyncRunner: TclError ao verificar widget, ignorando callback")
            return

        try:
            after_id = self.tk_root.after(0, self._safe_callback_wrapper, callback)
            self._pending_after_ids.append(after_id)
        except tk.TclError:
            if self.logger:
                self.logger.debug("HubAsyncRunner: TclError ao agendar callback")

    def _safe_callback_wrapper(self, callback: Callable[[], None]) -> None:
        """Wrapper que executa callback e remove ID da lista de pendentes."""
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            if self.logger:
                self.logger.exception("Erro ao executar callback do HUB", exc_info=exc)

    def shutdown(self) -> None:
        """Encerra o runner: cancela callbacks pendentes e desliga executor.

        FASE 5A: Chamado no destroy() do HubScreen para cleanup gracioso.
        """
        if self._shutdown:
            return

        self._shutdown = True

        if self.logger:
            self.logger.debug("HubAsyncRunner.shutdown: iniciando cleanup...")

        # Cancelar callbacks pendentes
        cancelled_count = 0
        for after_id in self._pending_after_ids:
            try:
                self.tk_root.after_cancel(after_id)
                cancelled_count += 1
            except (tk.TclError, Exception):
                pass  # Ignorar se widget já destruído
        self._pending_after_ids.clear()

        if self.logger and cancelled_count > 0:
            self.logger.debug(f"HubAsyncRunner.shutdown: {cancelled_count} callbacks cancelados")

        # Encerrar executor sem esperar
        if self._executor:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
                if self.logger:
                    self.logger.debug("HubAsyncRunner.shutdown: ThreadPoolExecutor encerrado")
            except TypeError:
                # Fallback: Python < 3.9 não suporta cancel_futures
                try:
                    self._executor.shutdown(wait=False)
                    if self.logger:
                        self.logger.debug("HubAsyncRunner.shutdown: ThreadPoolExecutor encerrado (sem cancel_futures)")
                except Exception as exc:  # noqa: BLE001
                    if self.logger:
                        self.logger.debug(f"HubAsyncRunner.shutdown: erro ao encerrar executor: {exc}")
            except Exception as exc:  # noqa: BLE001
                if self.logger:
                    self.logger.debug(f"HubAsyncRunner.shutdown: erro ao encerrar executor: {exc}")

        # Limpar referências
        self._executor = None
        self.tk_root = None
