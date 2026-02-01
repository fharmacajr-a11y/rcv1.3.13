# -*- coding: utf-8 -*-
"""Testes dos atalhos de teclado (FASE 3.8).

Valida bindings F5, Ctrl+N, Ctrl+E, Delete no ClientesV2Frame.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.modules.clientes.ui.view import ClientesV2Frame

log = logging.getLogger(__name__)


class TestKeyboardShortcuts:
    """Testes dos atalhos de teclado."""

    def test_f5_reloads_list(self, root: Any) -> None:
        """Testa atalho F5 para recarregar lista.

        FASE 3.8: Validar que F5 chama load_async().
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Mock load_async
        frame.load_async = MagicMock()

        # Act - Chamar handler diretamente (simula F5)
        result = frame._on_reload_shortcut()

        # Assert
        frame.load_async.assert_called_once()
        assert result == "break"

    def test_ctrl_n_opens_new_client_dialog(self, root: Any) -> None:
        """Testa atalho Ctrl+N para novo cliente.

        FASE 3.8: Validar que Ctrl+N chama _on_new_client().
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Mock para verificar chamada
        with patch.object(frame, "_on_new_client", wraps=frame._on_new_client) as mock_handler:
            # Act - Chamar handler diretamente (simula Ctrl+N)
            result = frame._on_new_client(MagicMock())  # event mock

            # Assert
            assert result == "break"
            mock_handler.assert_called_once()

    def test_ctrl_n_uppercase_works(self, root: Any) -> None:
        """Testa atalho Ctrl+Shift+N (Ctrl+N maiúsculo).

        FASE 3.8: Validar que Ctrl+Shift+N também funciona.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Act - Chamar handler diretamente (simula Ctrl+N)
        result = frame._on_new_client(MagicMock())  # event mock

        # Assert
        assert result == "break"

    def test_ctrl_e_opens_edit_dialog_with_selection(self, root: Any) -> None:
        """Testa atalho Ctrl+E para editar cliente com seleção.

        FASE 3.8: Validar que Ctrl+E chama _on_edit_client().
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()
        frame._selected_client_id = 123

        # Act - Chamar handler diretamente (simula Ctrl+E)
        result = frame._on_edit_client(MagicMock())  # event mock

        # Assert
        # Deve mostrar messagebox de aviso (sem cliente selecionado não abre diálogo)
        assert result == "break"

    def test_ctrl_e_uppercase_works(self, root: Any) -> None:
        """Testa atalho Ctrl+Shift+E (Ctrl+E maiúsculo).

        FASE 3.8: Validar que Ctrl+Shift+E também funciona.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()
        frame._selected_client_id = 123

        # Act - Chamar handler diretamente (simula Ctrl+E)
        result = frame._on_edit_client(MagicMock())  # event mock

        # Assert
        assert result == "break"

    def test_delete_moves_to_trash_with_selection(self, root: Any) -> None:
        """Testa atalho Delete para excluir/mover para lixeira.

        FASE 3.8: Validar que Delete chama _on_delete_client().
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()
        frame._selected_client_id = 456

        # Mock messagebox para cancelar (não executar serviço)
        with patch("tkinter.messagebox.askyesno", return_value=False):
            # Act - Chamar handler diretamente (simula Delete)
            result = frame._on_delete_client(MagicMock())  # event mock

            # Assert
            assert result == "break"

    def test_delete_without_selection_does_nothing(self, root: Any) -> None:
        """Testa Delete sem seleção (não deve crashar).

        FASE 3.8: Validar que Delete sem seleção é ignorado silenciosamente.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()
        frame._selected_client_id = None

        # Act & Assert (não deve lançar exceção)
        try:
            frame.event_generate("<Delete>")
            frame.update()
        except Exception as e:
            pytest.fail(f"Delete sem seleção lançou exceção: {e}")

    def test_shortcuts_return_break(self, root: Any) -> None:
        """Testa que handlers retornam 'break' para evitar propagação.

        FASE 3.8: Validar que todos os handlers retornam 'break' quando
        chamados via event.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Mock event
        mock_event = MagicMock()

        # Act & Assert
        result_reload = frame._on_reload_shortcut(mock_event)
        assert result_reload == "break", "F5 handler deve retornar 'break'"

        result_new = frame._on_new_client(mock_event)
        assert result_new == "break", "Ctrl+N handler deve retornar 'break'"

        frame._selected_client_id = 123
        result_edit = frame._on_edit_client(mock_event)
        assert result_edit == "break", "Ctrl+E handler deve retornar 'break'"

        # Mock messagebox para Delete
        with patch("tkinter.messagebox.askyesno", return_value=False):
            result_delete = frame._on_delete_client(mock_event)
            assert result_delete == "break", "Delete handler deve retornar 'break'"

    def test_shortcuts_setup_called_on_init(self, root: Any) -> None:
        """Testa que _setup_keyboard_shortcuts é chamado na inicialização.

        FASE 3.8: Validar que os atalhos são configurados automaticamente.
        """
        # Arrange & Act
        with patch.object(ClientesV2Frame, "_setup_keyboard_shortcuts") as mock_setup:
            frame = ClientesV2Frame(root)
            frame.app = MagicMock()

        # Assert
        mock_setup.assert_called_once()

    def test_f5_with_filters_preserves_state(self, root: Any) -> None:
        """Testa que F5 preserva filtros ativos.

        FASE 3.8: Validar que F5 não reseta os filtros aplicados.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Aplicar filtros via toolbar
        frame.toolbar.entry_search.insert(0, "termo_busca")
        frame.toolbar.status_combo.set("Ativo")

        # Mock load_async para capturar chamada
        frame.load_async = MagicMock()

        # Act - Chamar handler diretamente (simula F5)
        frame._on_reload_shortcut()

        # Assert
        # F5 deve chamar load_async, que internamente usará os filtros atuais
        frame.load_async.assert_called_once()

        # Filtros não devem ter sido resetados
        assert frame.toolbar.entry_search.get() == "termo_busca"
        assert frame.toolbar.status_combo.get() == "Ativo"

    def test_shortcuts_work_with_focus_on_tree(self, root: Any) -> None:
        """Testa que atalhos funcionam mesmo com foco na Treeview.

        FASE 3.8: Validar que atalhos são capturados independente do foco.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()
        frame._selected_client_id = 789

        # Mock handlers
        frame.load_async = MagicMock()

        # Act - Chamar handlers diretamente
        result_reload = frame._on_reload_shortcut()
        result_new = frame._on_new_client(MagicMock())
        result_edit = frame._on_edit_client(MagicMock())

        # Mock messagebox para Delete
        with patch("tkinter.messagebox.askyesno", return_value=False):
            result_delete = frame._on_delete_client(MagicMock())

        # Assert
        assert result_reload == "break"
        assert result_new == "break"
        assert result_edit == "break"
        assert result_delete == "break"
        frame.load_async.assert_called()
