# -*- coding: utf-8 -*-
"""Testes para callbacks do theme_manager.

Valida que callbacks são registrados, notificados e desregistrados corretamente,
e que exceções em um callback não impedem outros de executar.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.ui.theme_manager import GlobalThemeManager


class TestThemeManagerCallbacks:
    """Testes para sistema de callbacks do theme_manager."""

    def test_register_callback_adiciona_callback(self):
        """Teste: register_callback() adiciona callback à lista."""
        manager = GlobalThemeManager()
        callback = MagicMock(__name__="test_callback")

        manager.register_callback(callback)

        assert callback in manager._callbacks

    def test_register_callback_nao_duplica(self):
        """Teste: register_callback() não adiciona callback duplicado."""
        manager = GlobalThemeManager()
        callback = MagicMock(__name__="test_callback")

        manager.register_callback(callback)
        manager.register_callback(callback)  # duplicado

        assert manager._callbacks.count(callback) == 1

    def test_unregister_callback_remove_callback(self):
        """Teste: unregister_callback() remove callback da lista."""
        manager = GlobalThemeManager()
        callback = MagicMock(__name__="test_callback")

        manager.register_callback(callback)
        manager.unregister_callback(callback)

        assert callback not in manager._callbacks

    def test_unregister_callback_ignora_callback_inexistente(self):
        """Teste: unregister_callback() não falha se callback não existe."""
        manager = GlobalThemeManager()
        callback = MagicMock(__name__="test_callback")

        # Não deve lançar exceção
        manager.unregister_callback(callback)

        assert callback not in manager._callbacks

    def test_notify_callbacks_chama_todos_callbacks(self):
        """Teste: _notify_callbacks() chama todos os callbacks registrados."""
        manager = GlobalThemeManager()
        callback1 = MagicMock(__name__="callback1")
        callback2 = MagicMock(__name__="callback2")

        manager.register_callback(callback1)
        manager.register_callback(callback2)

        manager._notify_callbacks("Dark")

        callback1.assert_called_once_with("Dark")
        callback2.assert_called_once_with("Dark")

    def test_callback_com_excecao_nao_impede_outros(self):
        """Teste: Callback que lança exceção não impede outros de executar."""
        manager = GlobalThemeManager()
        callback1 = MagicMock(__name__="bad_callback", side_effect=RuntimeError("Callback ruim"))
        callback2 = MagicMock(__name__="good_callback2")
        callback3 = MagicMock(__name__="good_callback3")

        manager.register_callback(callback1)
        manager.register_callback(callback2)
        manager.register_callback(callback3)

        # Não deve lançar exceção
        manager._notify_callbacks("Light")

        # Todos os callbacks devem ter sido chamados
        callback1.assert_called_once_with("Light")
        callback2.assert_called_once_with("Light")
        callback3.assert_called_once_with("Light")

    def test_callback_recebe_modo_correto(self):
        """Teste: Callback recebe o modo correto (Light/Dark)."""
        manager = GlobalThemeManager()
        callback = MagicMock(__name__="test_callback")

        manager.register_callback(callback)

        manager._notify_callbacks("Light")
        callback.assert_called_with("Light")

        callback.reset_mock()

        manager._notify_callbacks("Dark")
        callback.assert_called_with("Dark")
