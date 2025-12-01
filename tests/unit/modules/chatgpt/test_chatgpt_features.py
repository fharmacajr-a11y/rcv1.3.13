"""Testes unitários para novas funcionalidades do ChatGPT."""

from __future__ import annotations

import tkinter as tk

import pytest

from src.modules.chatgpt.views.chatgpt_window import ChatGPTWindow


def _create_root_or_skip() -> tk.Tk:
    """Cria um Tk root ou faz skip se o Tkinter não estiver disponível."""
    try:
        return tk.Tk()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tkinter indisponível para testes de ChatGPT: {exc}")


def test_new_conversation_clears_history() -> None:
    """Testa que nova conversa limpa o histórico visual e de mensagens."""
    root = _create_root_or_skip()
    try:

        def fake_send_fn(messages: list[dict[str, str]]) -> str:
            return "resposta teste"

        win = ChatGPTWindow(root, send_fn=fake_send_fn)

        # Adicionar algumas mensagens
        win._messages.append({"role": "user", "content": "msg1"})
        win._messages.append({"role": "assistant", "content": "resp1"})
        win._append_to_history("Voce", "msg1")
        win._append_to_history("ChatGPT", "resp1")

        # Verificar que há conteúdo
        history_before = win._history.get("1.0", "end").strip()
        assert "msg1" in history_before
        assert "resp1" in history_before
        assert len(win._messages) == 3  # system + user + assistant

        # Chamar nova conversa
        win.new_conversation()

        # Verificar que histórico foi limpo
        history_after = win._history.get("1.0", "end").strip()
        assert "msg1" not in history_after
        assert "resp1" not in history_after
        assert "Nova conversa iniciada" in history_after

        # Verificar que mensagens foram resetadas (apenas system message)
        assert len(win._messages) == 1
        assert win._messages[0]["role"] == "system"
    finally:
        root.destroy()


def test_new_conversation_preserves_system_message() -> None:
    """Testa que nova conversa mantém a mensagem de sistema."""
    root = _create_root_or_skip()
    try:

        def fake_send_fn(messages: list[dict[str, str]]) -> str:
            return "ok"

        win = ChatGPTWindow(root, send_fn=fake_send_fn)

        original_system = win._messages[0].copy()

        # Adicionar mensagens e limpar
        win._messages.append({"role": "user", "content": "teste"})
        win.new_conversation()

        # Verificar que system message foi mantida
        assert len(win._messages) == 1
        assert win._messages[0] == original_system
    finally:
        root.destroy()


def test_show_method_exists() -> None:
    """Testa que o método show() existe e pode ser chamado."""
    root = _create_root_or_skip()
    try:
        win = ChatGPTWindow(root, send_fn=lambda m: "ok")

        # Verificar que método existe
        assert hasattr(win, "show")
        assert callable(win.show)

        # Chamar show não deve lançar exceção
        win.iconify()  # minimizar primeiro com iconify
        win.show()  # depois mostrar

    finally:
        root.destroy()


def test_on_minimize_method_exists() -> None:
    """Testa que o método on_minimize() existe e pode ser chamado."""
    root = _create_root_or_skip()
    try:
        win = ChatGPTWindow(root, send_fn=lambda m: "ok")

        # Verificar que método existe
        assert hasattr(win, "on_minimize")
        assert callable(win.on_minimize)

        # Chamar on_minimize não deve lançar exceção (usa iconify agora)
        win.on_minimize()

    finally:
        root.destroy()


def test_messages_start_with_system_only() -> None:
    """Testa que a lista de mensagens inicia apenas com a mensagem de sistema."""
    root = _create_root_or_skip()
    try:
        win = ChatGPTWindow(root, send_fn=lambda m: "ok")

        assert len(win._messages) == 1
        assert win._messages[0]["role"] == "system"
        assert "RC Gestor" in win._messages[0]["content"]
    finally:
        root.destroy()


def test_new_conversation_can_be_called_multiple_times() -> None:
    """Testa que nova conversa pode ser chamada múltiplas vezes sem erro."""
    root = _create_root_or_skip()
    try:
        win = ChatGPTWindow(root, send_fn=lambda m: "ok")

        # Chamar várias vezes
        for _ in range(3):
            win._messages.append({"role": "user", "content": "test"})
            win.new_conversation()
            assert len(win._messages) == 1
            assert win._messages[0]["role"] == "system"
    finally:
        root.destroy()


def test_window_not_modal() -> None:
    """Testa que a janela não usa grab_set (não é modal)."""
    root = _create_root_or_skip()
    try:
        win = ChatGPTWindow(root, send_fn=lambda m: "ok")

        # Se fosse modal, grab_current() retornaria a janela
        # Como não é modal, deve retornar None ou outro widget
        grabbed = root.grab_current()
        assert grabbed != win or grabbed is None
    finally:
        root.destroy()


def test_close_callback_is_called() -> None:
    """Testa que o callback de fechamento é chamado."""
    root = _create_root_or_skip()
    try:
        callback_called = []

        def on_close():
            callback_called.append(True)

        win = ChatGPTWindow(root, send_fn=lambda m: "ok", on_close_callback=on_close)

        # Simular fechamento pelo botão X
        win._on_close_clicked()

        # Aguardar processamento
        root.update()

        # Callback deve ter sido chamado
        assert len(callback_called) == 1
    finally:
        try:
            root.destroy()
        except Exception:
            pass
