"""Testes de integração da Fase 05 - Integration Layer para Batch Operations.

Módulo: src.modules.clientes.views.main_screen
Fase: 05 - Integration Layer (Selection + Batch Buttons)

NOTA (FEATURE-CLIENTES-001): Os botões de batch foram removidos da tela principal.
NOTA (MS-37): _update_batch_buttons_state foi removido (código morto). Testes desabilitados.
Este arquivo foi adaptado para testar:
- _get_selected_ids: centralização da leitura de seleção
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_frame() -> Mock:
    """Fixture que cria um mock do MainScreenFrame para testes."""
    from src.modules.clientes.views.main_screen import MainScreenFrame
    from src.modules.clientes.controllers.selection_manager import SelectionManager

    # Cria mock do frame sem inicialização completa
    frame = Mock(spec=MainScreenFrame)
    frame.client_list = Mock()

    # MS-24: Inicializa SelectionManager necessário
    frame._selection_manager = SelectionManager(all_clients=[])

    # Injeta os métodos reais que queremos testar
    frame._get_selected_ids = MainScreenFrame._get_selected_ids.__get__(frame)
    frame._build_selection_snapshot = MainScreenFrame._build_selection_snapshot.__get__(frame)

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
