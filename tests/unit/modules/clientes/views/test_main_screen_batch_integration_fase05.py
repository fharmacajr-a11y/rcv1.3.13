"""Testes de integração da Fase 05 - Integration Layer para Batch Operations.

Módulo: src.modules.clientes.views.main_screen
Fase: 05 - Integration Layer (Selection + Batch Buttons)

NOTA (FEATURE-CLIENTES-001): Os botões de batch foram removidos da tela principal.
Este arquivo foi adaptado para testar:
- _get_selected_ids: centralização da leitura de seleção
- _update_batch_buttons_state: atualização de estados (lida graciosamente com ausência de botões)
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_frame() -> Mock:
    """Fixture que cria um mock do MainScreenFrame para testes."""
    from src.modules.clientes.views.main_screen import MainScreenFrame

    # Cria mock do frame sem inicialização completa
    frame = Mock(spec=MainScreenFrame)
    frame.client_list = Mock()

    # Injeta os métodos reais que queremos testar
    frame._get_selected_ids = MainScreenFrame._get_selected_ids.__get__(frame)
    frame._update_batch_buttons_state = MainScreenFrame._update_batch_buttons_state.__get__(frame)

    return frame


class TestGetSelectedIds:
    """Testes para _get_selected_ids (centralização de seleção)."""

    def test_empty_selection_returns_empty_set(self, mock_frame: Mock) -> None:
        """Seleção vazia deve retornar set vazio."""
        # Arrange
        mock_frame.client_list.selection.return_value = ()

        # Act
        result = mock_frame._get_selected_ids()

        # Assert
        assert result == set()
        assert isinstance(result, set)

    def test_single_selection_returns_set_with_one_id(self, mock_frame: Mock) -> None:
        """Seleção com 1 item deve retornar set com 1 ID."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("item1",)

        # Act
        result = mock_frame._get_selected_ids()

        # Assert
        assert result == {"item1"}
        assert isinstance(result, set)

    def test_multiple_selection_returns_set_with_all_ids(self, mock_frame: Mock) -> None:
        """Seleção com múltiplos itens deve retornar set com todos IDs."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("item1", "item2", "item3")

        # Act
        result = mock_frame._get_selected_ids()

        # Assert
        assert result == {"item1", "item2", "item3"}
        assert isinstance(result, set)

    def test_exception_returns_empty_set(self, mock_frame: Mock) -> None:
        """Exceção ao ler seleção deve retornar set vazio."""
        # Arrange
        mock_frame.client_list.selection.side_effect = Exception("Test error")

        # Act
        result = mock_frame._get_selected_ids()

        # Assert
        assert result == set()
        assert isinstance(result, set)


class TestUpdateBatchButtonsStateWithoutButtons:
    """Testes para _update_batch_buttons_state sem botões presentes."""

    @patch("src.modules.clientes.views.main_screen.get_supabase_state")
    def test_update_batch_buttons_state_without_buttons_does_not_crash(
        self, mock_get_state: MagicMock, mock_frame: Mock
    ) -> None:
        """Sem botões batch, método não deve crashar."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("item1", "item2")
        mock_get_state.return_value = ("online", None)

        # Não cria atributos btn_batch_* (simula tela sem botões)

        # Act - não deve lançar exceção
        mock_frame._update_batch_buttons_state()

        # Assert - se chegou aqui, passou
        assert True

    @patch("src.modules.clientes.views.main_screen.get_supabase_state")
    def test_update_batch_buttons_state_with_none_buttons_does_not_crash(
        self, mock_get_state: MagicMock, mock_frame: Mock
    ) -> None:
        """Com botões batch = None, método não deve crashar."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("item1", "item2")
        mock_get_state.return_value = ("online", None)

        # Cria atributos btn_batch_* = None (simula FooterButtons.batch_* = None)
        mock_frame.btn_batch_delete = None
        mock_frame.btn_batch_restore = None
        mock_frame.btn_batch_export = None

        # Act - não deve lançar exceção
        mock_frame._update_batch_buttons_state()

        # Assert - se chegou aqui, passou
        assert True


class TestUpdateBatchButtonsStateWithButtons:
    """Testes para _update_batch_buttons_state COM botões (para outras telas)."""

    @patch("src.modules.clientes.views.main_screen.get_supabase_state")
    def test_no_selection_disables_all_batch_buttons(self, mock_get_state: MagicMock, mock_frame: Mock) -> None:
        """Sem seleção, todos botões de batch devem estar desabilitados."""
        # Arrange
        mock_frame.client_list.selection.return_value = ()
        mock_get_state.return_value = ("online", None)

        # Cria botões fake
        mock_frame.btn_batch_delete = Mock()
        mock_frame.btn_batch_restore = Mock()
        mock_frame.btn_batch_export = Mock()

        # Act
        mock_frame._update_batch_buttons_state()

        # Assert
        mock_frame.btn_batch_delete.configure.assert_called_once_with(state="disabled")
        mock_frame.btn_batch_restore.configure.assert_called_once_with(state="disabled")
        mock_frame.btn_batch_export.configure.assert_called_once_with(state="disabled")

    @patch("src.modules.clientes.views.main_screen.get_supabase_state")
    def test_main_screen_online_enables_delete_and_export(self, mock_get_state: MagicMock, mock_frame: Mock) -> None:
        """Na lista principal, online, Delete e Export habilitados, Restore não."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("item1", "item2")
        mock_get_state.return_value = ("online", None)

        # Cria botões fake
        mock_frame.btn_batch_delete = Mock()
        mock_frame.btn_batch_restore = Mock()
        mock_frame.btn_batch_export = Mock()

        # Act
        mock_frame._update_batch_buttons_state()

        # Assert
        mock_frame.btn_batch_delete.configure.assert_called_once_with(state="normal")
        mock_frame.btn_batch_restore.configure.assert_called_once_with(state="disabled")
        mock_frame.btn_batch_export.configure.assert_called_once_with(state="normal")

    @patch("src.modules.clientes.views.main_screen.get_supabase_state")
    def test_offline_only_export_enabled(self, mock_get_state: MagicMock, mock_frame: Mock) -> None:
        """Offline, apenas Export deve estar habilitado."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("item1", "item2")
        mock_get_state.return_value = ("offline", None)

        # Cria botões fake
        mock_frame.btn_batch_delete = Mock()
        mock_frame.btn_batch_restore = Mock()
        mock_frame.btn_batch_export = Mock()

        # Act
        mock_frame._update_batch_buttons_state()

        # Assert
        mock_frame.btn_batch_delete.configure.assert_called_once_with(state="disabled")
        mock_frame.btn_batch_restore.configure.assert_called_once_with(state="disabled")
        mock_frame.btn_batch_export.configure.assert_called_once_with(state="normal")

    @patch("src.modules.clientes.views.main_screen.get_supabase_state")
    def test_large_selection_without_limit_enables_operations(
        self, mock_get_state: MagicMock, mock_frame: Mock
    ) -> None:
        """Grande seleção sem limite deve habilitar operações."""
        # Arrange
        large_selection = tuple(f"item{i}" for i in range(100))
        mock_frame.client_list.selection.return_value = large_selection
        mock_get_state.return_value = ("online", None)

        # Cria botões fake
        mock_frame.btn_batch_delete = Mock()
        mock_frame.btn_batch_export = Mock()

        # Act
        mock_frame._update_batch_buttons_state()

        # Assert - max_items=None, então permite qualquer quantidade
        mock_frame.btn_batch_delete.configure.assert_called_once_with(state="normal")
        mock_frame.btn_batch_export.configure.assert_called_once_with(state="normal")


class TestBatchOperationsConsistency:
    """Testes de consistência entre helpers e UI."""

    def test_get_selected_ids_returns_same_as_direct_selection(self, mock_frame: Mock) -> None:
        """_get_selected_ids deve retornar mesmo conteúdo que selection()."""
        # Arrange
        test_cases = [
            (),
            ("item1",),
            ("item1", "item2"),
            ("a", "b", "c", "d", "e"),
        ]

        for selection_tuple in test_cases:
            # Arrange
            mock_frame.client_list.selection.return_value = selection_tuple

            # Act
            result = mock_frame._get_selected_ids()
            expected = set(selection_tuple)

            # Assert
            assert result == expected, f"Failed for {selection_tuple}"
