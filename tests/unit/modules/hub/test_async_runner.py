# -*- coding: utf-8 -*-
"""Testes para HubAsyncRunner."""

from __future__ import annotations

import logging
import time
from typing import Callable

import pytest


# Fake TkRoot para testes (sem depender de Tkinter real)
class FakeTkRoot:
    """Simula tk.Misc para testes sem criar janela real."""

    def __init__(self):
        self.scheduled_callbacks: list[tuple[int, Callable, tuple]] = []

    def after(self, delay_ms: int, callback: Callable, *args) -> None:
        """Simula tk.after, executando callbacks imediatamente nos testes."""
        # Executar callback imediatamente para simplificar testes
        callback(*args)


@pytest.fixture
def fake_tk_root():
    """Fixture que fornece um FakeTkRoot para testes."""
    return FakeTkRoot()


@pytest.fixture
def runner(fake_tk_root):
    """Fixture que fornece um HubAsyncRunner configurado."""
    from src.modules.hub.async_runner import HubAsyncRunner

    logger = logging.getLogger("test_async_runner")
    return HubAsyncRunner(tk_root=fake_tk_root, logger=logger)


class TestHubAsyncRunner:
    """Testes do HubAsyncRunner."""

    def test_run_success_simple(self, runner):
        """Testa execução bem-sucedida com resultado simples."""
        result_captured = None

        def func():
            return 42

        def on_success(result):
            nonlocal result_captured
            result_captured = result

        def on_error(exc):
            pytest.fail(f"on_error não deveria ser chamado: {exc}")

        runner.run(func=func, on_success=on_success, on_error=on_error)

        # Aguardar thread completar
        time.sleep(0.1)

        assert result_captured == 42

    def test_run_success_with_complex_result(self, runner):
        """Testa execução com resultado complexo (dict)."""
        result_captured = None

        def func():
            return {"status": "ok", "data": [1, 2, 3]}

        def on_success(result):
            nonlocal result_captured
            result_captured = result

        def on_error(exc):
            pytest.fail(f"on_error não deveria ser chamado: {exc}")

        runner.run(func=func, on_success=on_success, on_error=on_error)

        # Aguardar thread completar
        time.sleep(0.1)

        assert result_captured == {"status": "ok", "data": [1, 2, 3]}

    def test_run_error_exception_raised(self, runner):
        """Testa tratamento de exceção em func()."""
        error_captured = None

        def func():
            raise ValueError("Erro intencional de teste")

        def on_success(result):
            pytest.fail(f"on_success não deveria ser chamado: {result}")

        def on_error(exc):
            nonlocal error_captured
            error_captured = exc

        runner.run(func=func, on_success=on_success, on_error=on_error)

        # Aguardar thread completar
        time.sleep(0.1)

        assert error_captured is not None
        assert isinstance(error_captured, ValueError)
        assert str(error_captured) == "Erro intencional de teste"

    def test_run_error_different_exception_types(self, runner):
        """Testa diferentes tipos de exceção."""
        for exc_type in [RuntimeError, KeyError, TypeError, AttributeError]:
            error_captured = None

            def func():
                raise exc_type("Teste")

            def on_success(result):
                pytest.fail(f"on_success não deveria ser chamado: {result}")

            def on_error(exc):
                nonlocal error_captured
                error_captured = exc

            runner.run(func=func, on_success=on_success, on_error=on_error)

            # Aguardar thread completar
            time.sleep(0.1)

            assert error_captured is not None
            assert isinstance(error_captured, exc_type)

    def test_callbacks_executed_in_main_thread(self, fake_tk_root, runner):
        """Verifica que callbacks são agendados via tk.after (main thread)."""
        after_called = False
        original_after = fake_tk_root.after

        def tracked_after(delay_ms, callback, *args):
            nonlocal after_called
            after_called = True
            original_after(delay_ms, callback, *args)

        fake_tk_root.after = tracked_after

        def func():
            return "test"

        def on_success(result):
            pass

        def on_error(exc):
            pass

        runner.run(func=func, on_success=on_success, on_error=on_error)

        # Aguardar thread completar
        time.sleep(0.1)

        assert after_called, "tk.after deveria ter sido chamado"

    def test_logger_logs_exception(self, fake_tk_root, caplog):
        """Verifica que exceções são logadas quando logger está presente."""
        logger = logging.getLogger("test_logger")
        runner_with_logger = __import__(
            "src.modules.hub.async_runner",
            fromlist=["HubAsyncRunner"],
        ).HubAsyncRunner(tk_root=fake_tk_root, logger=logger)

        def func():
            raise RuntimeError("Erro de teste para logging")

        def on_success(result):
            pass

        def on_error(exc):
            pass

        with caplog.at_level(logging.ERROR):
            runner_with_logger.run(func=func, on_success=on_success, on_error=on_error)
            time.sleep(0.1)

        # Verificar que erro foi logado
        assert any("Erro em tarefa assíncrona do HUB" in record.message for record in caplog.records)

    def test_no_error_if_logger_is_none(self, fake_tk_root):
        """Verifica que runner funciona sem logger."""
        runner_no_logger = __import__(
            "src.modules.hub.async_runner",
            fromlist=["HubAsyncRunner"],
        ).HubAsyncRunner(tk_root=fake_tk_root, logger=None)

        error_captured = None

        def func():
            raise ValueError("Erro sem logger")

        def on_success(result):
            pass

        def on_error(exc):
            nonlocal error_captured
            error_captured = exc

        # Não deve lançar exceção mesmo sem logger
        runner_no_logger.run(func=func, on_success=on_success, on_error=on_error)
        time.sleep(0.1)

        assert error_captured is not None
        assert isinstance(error_captured, ValueError)


class TestHubAsyncRunnerIntegration:
    """Testes de integração do HubAsyncRunner."""

    def test_multiple_concurrent_runs(self, runner):
        """Testa múltiplas execuções concorrentes."""
        results = []

        def make_func(value):
            def func():
                time.sleep(0.05)  # simular trabalho
                return value

            return func

        def make_on_success(expected):
            def on_success(result):
                assert result == expected
                results.append(result)

            return on_success

        def on_error(exc):
            pytest.fail(f"on_error não deveria ser chamado: {exc}")

        # Lançar 3 tarefas concorrentes
        for i in range(3):
            runner.run(
                func=make_func(i),
                on_success=make_on_success(i),
                on_error=on_error,
            )

        # Aguardar todas completarem
        time.sleep(0.3)

        assert len(results) == 3
        assert set(results) == {0, 1, 2}

    def test_runner_handles_none_result(self, runner):
        """Testa que runner aceita funções que retornam None."""
        success_called = False

        def func():
            return None

        def on_success(result):
            nonlocal success_called
            success_called = True
            assert result is None

        def on_error(exc):
            pytest.fail(f"on_error não deveria ser chamado: {exc}")

        runner.run(func=func, on_success=on_success, on_error=on_error)
        time.sleep(0.1)

        assert success_called

    def test_func_with_side_effects(self, runner):
        """Testa função com efeitos colaterais (ex: modificar lista)."""
        side_effect_list = []

        def func():
            side_effect_list.append("executed")
            return len(side_effect_list)

        def on_success(result):
            assert result == 1
            assert side_effect_list == ["executed"]

        def on_error(exc):
            pytest.fail(f"on_error não deveria ser chamado: {exc}")

        runner.run(func=func, on_success=on_success, on_error=on_error)
        time.sleep(0.1)

        assert side_effect_list == ["executed"]
