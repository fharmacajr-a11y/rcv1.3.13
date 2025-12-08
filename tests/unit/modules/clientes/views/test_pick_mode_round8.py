# -*- coding: utf-8 -*-

"""Testes unitários para PickModeController.

Round 8: Cobertura de testes para o fluxo de Pick Mode de clientes.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.modules.clientes.views.pick_mode import PickModeController


@pytest.fixture
def mock_frame() -> Mock:
    """Fixture que cria um mock do MainScreenFrame para testes."""
    frame = Mock()
    frame.client_list = Mock()
    frame._pick_mode = False
    frame._on_pick = None
    frame._return_to = None
    frame._saved_toolbar_state = {}

    # Simular métodos opcionais
    frame._enter_pick_mode_ui = Mock()
    frame._leave_pick_mode_ui = Mock()
    frame._update_main_buttons_state = Mock()
    frame.carregar = Mock()

    return frame


@pytest.fixture
def pick_controller(mock_frame: Mock) -> PickModeController:
    """Fixture que cria um PickModeController com frame mockado."""
    controller = PickModeController(frame=mock_frame)
    return controller


class TestPickModeActivation:
    """Testes para ativação e desativação do modo pick."""

    def test_start_pick_activates_mode(self, pick_controller: PickModeController, mock_frame: Mock) -> None:
        """start_pick deve ativar o modo e configurar callbacks."""
        # Arrange
        callback = Mock()
        return_callback = Mock()

        # Act
        pick_controller.start_pick(on_pick=callback, return_to=return_callback)

        # Assert
        assert pick_controller.is_active() is True
        assert pick_controller._callback == callback
        assert pick_controller._return_to == return_callback
        assert mock_frame._pick_mode is True
        mock_frame.carregar.assert_called_once()

    def test_cancel_pick_deactivates_mode(self, pick_controller: PickModeController, mock_frame: Mock) -> None:
        """cancel_pick deve desativar o modo e chamar return_to."""
        # Arrange
        callback = Mock()
        return_callback = Mock()
        pick_controller.start_pick(on_pick=callback, return_to=return_callback)

        # Act
        pick_controller.cancel_pick()

        # Assert
        assert pick_controller.is_active() is False


class TestPickModeBannerText:
    """Testes para o texto do banner em diferentes contextos."""

    def test_start_pick_updates_banner_with_custom_text(
        self,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        mock_label = Mock()
        mock_frame._pick_label = mock_label
        mock_frame._pick_banner_default_text = "texto padrão"

        callback = Mock()
        return_callback = Mock()

        pick_controller.start_pick(on_pick=callback, return_to=return_callback, banner_text="Contexto específico")

        mock_label.configure.assert_called_with(text="Contexto específico")

    def test_start_pick_without_banner_uses_default(
        self,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        mock_label = Mock()
        mock_frame._pick_label = mock_label
        mock_frame._pick_banner_default_text = "texto padrão"

        callback = Mock()
        return_callback = Mock()

        pick_controller.start_pick(on_pick=callback, return_to=return_callback, banner_text="Outro contexto")
        pick_controller.cancel_pick()

        mock_label.configure.assert_called_with(text="Outro contexto")
        mock_label.configure.reset_mock()

        pick_controller.start_pick(on_pick=callback, return_to=return_callback)
        mock_label.configure.assert_called_with(text="texto padrão")
        return_callback.assert_called_once()

    def test_cancel_pick_when_not_active_does_nothing(self, pick_controller: PickModeController) -> None:
        """cancel_pick quando não ativo não deve fazer nada."""
        # Arrange (controller já começa inativo)

        # Act
        pick_controller.cancel_pick()

        # Assert
        assert pick_controller.is_active() is False


class TestPickModeSelectionFlow:
    """Testes para o fluxo de seleção no modo pick."""

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_confirm_pick_with_no_selection_shows_warning(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """confirm_pick sem seleção deve exibir warning e não chamar callback."""
        # Arrange
        callback = Mock()
        pick_controller.start_pick(on_pick=callback)

        # Simular treeview sem seleção
        mock_frame.client_list.selection.return_value = ()

        # validate_single_selection retorna inválido para seleção vazia
        mock_validate.return_value = (False, None, "none_selected")

        # Act
        pick_controller.confirm_pick()

        # Assert
        mock_validate.assert_called_once_with(set())
        mock_showwarning.assert_called_once_with("Atenção", "Selecione um cliente primeiro.", parent=mock_frame)
        callback.assert_not_called()
        # Modo continua ativo porque não houve seleção válida
        assert pick_controller.is_active() is True

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_confirm_pick_with_single_selection_calls_callback(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """confirm_pick com 1 item selecionado deve chamar callback com dados do cliente."""
        # Arrange
        callback = Mock()
        return_callback = Mock()
        pick_controller.start_pick(on_pick=callback, return_to=return_callback)

        # Simular treeview com 1 item selecionado
        mock_frame.client_list.selection.return_value = ("client_123",)

        # validate_single_selection retorna válido
        mock_validate.return_value = (True, "client_123", None)

        # Simular dados do cliente na treeview - item(id, "values") retorna tupla
        mock_frame.client_list.item = Mock(return_value=("client_123", "Empresa Teste LTDA", "12345678000190"))

        # Act
        pick_controller.confirm_pick()

        # Assert
        mock_validate.assert_called_once_with({"client_123"})
        mock_showwarning.assert_not_called()

        # Verificar que callback foi chamado com dados formatados
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["id"] == "client_123"
        assert call_args["razao_social"] == "Empresa Teste LTDA"
        assert "cnpj" in call_args

        # Modo foi desativado após confirmação
        assert pick_controller.is_active() is False
        return_callback.assert_called_once()

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_confirm_pick_with_multiple_selection_shows_warning(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """confirm_pick com múltiplos itens deve exibir warning."""
        # Arrange
        callback = Mock()
        pick_controller.start_pick(on_pick=callback)

        # Simular treeview com múltiplos itens
        mock_frame.client_list.selection.return_value = ("client_1", "client_2")

        # validate_single_selection retorna inválido para múltipla seleção
        mock_validate.return_value = (False, None, "multiple_selected")

        # Act
        pick_controller.confirm_pick()

        # Assert
        mock_validate.assert_called_once_with({"client_1", "client_2"})
        mock_showwarning.assert_called_once_with("Atenção", "Selecione um cliente primeiro.", parent=mock_frame)
        callback.assert_not_called()

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_confirm_pick_when_not_active_does_nothing(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
    ) -> None:
        """confirm_pick quando modo não está ativo não deve fazer nada."""
        # Arrange (controller começa inativo)

        # Act
        pick_controller.confirm_pick()

        # Assert
        mock_validate.assert_not_called()
        mock_showwarning.assert_not_called()

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_confirm_pick_with_data_retrieval_error_shows_warning(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """confirm_pick com erro ao obter dados deve exibir warning."""
        # Arrange
        callback = Mock()
        pick_controller.start_pick(on_pick=callback)

        # Simular treeview com 1 item
        mock_frame.client_list.selection.return_value = ("client_123",)
        mock_validate.return_value = (True, "client_123", None)

        # Simular erro ao obter dados (valores insuficientes)
        mock_frame.client_list.item.return_value = {"values": ("client_123",)}

        # Act
        pick_controller.confirm_pick()

        # Assert
        mock_showwarning.assert_called_with("Atenção", "Erro ao obter dados do cliente.", parent=mock_frame)
        callback.assert_not_called()


class TestPickModeIntegrationWithHelpers:
    """Testes de integração com helpers de seleção."""

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_confirm_pick_uses_validate_single_selection_helper(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """confirm_pick deve usar validate_single_selection do main_screen_helpers."""
        # Simular diferentes cenários de seleção
        test_cases = [
            ((), set(), (False, None, "none_selected")),  # Sem seleção
            (("id1",), {"id1"}, (True, "id1", None)),  # Seleção válida
            (("id1", "id2"), {"id1", "id2"}, (False, None, "multiple_selected")),  # Múltipla
        ]

        for selection_tuple, expected_ids, validate_result in test_cases:
            # Reativar modo pick para cada caso de teste
            callback = Mock()
            pick_controller.start_pick(on_pick=callback)

            mock_validate.reset_mock()
            mock_frame.client_list.selection.return_value = selection_tuple
            mock_validate.return_value = validate_result

            # Mockar dados do cliente (necessário para seleção válida)
            if validate_result[0]:  # Se válido
                mock_frame.client_list.item = Mock(return_value=("id1", "Empresa", "12345678000190"))

            # Act
            pick_controller.confirm_pick()

            # Assert
            mock_validate.assert_called_once_with(expected_ids)


class TestGetSelectedClientDict:
    """Testes para _get_selected_client_dict."""

    def test_get_selected_client_dict_with_valid_data(
        self,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """_get_selected_client_dict deve retornar dict com dados do cliente."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("client_123",)
        mock_frame.client_list.item = Mock(return_value=("client_123", "Empresa ABC", "12345678000190", "extra_data"))

        # Act
        result = pick_controller._get_selected_client_dict()

        # Assert
        assert result is not None
        assert result["id"] == "client_123"
        assert result["razao_social"] == "Empresa ABC"
        assert result["cnpj"] == "12345678000190"

    def test_get_selected_client_dict_with_no_selection(
        self,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """_get_selected_client_dict sem seleção deve retornar None."""
        # Arrange
        mock_frame.client_list.selection.return_value = ()

        # Act
        result = pick_controller._get_selected_client_dict()

        # Assert
        assert result is None

    def test_get_selected_client_dict_with_insufficient_values(
        self,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """_get_selected_client_dict com dados insuficientes deve retornar None."""
        # Arrange
        mock_frame.client_list.selection.return_value = ("client_123",)
        mock_frame.client_list.item = Mock(return_value=("client_123", "Empresa"))  # Faltando cnpj

        # Act
        result = pick_controller._get_selected_client_dict()

        # Assert
        assert result is None

    def test_get_selected_client_dict_with_exception(
        self,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """_get_selected_client_dict com exceção deve retornar None."""
        # Arrange
        mock_frame.client_list.selection.side_effect = Exception("Test error")

        # Act
        result = pick_controller._get_selected_client_dict()

        # Assert
        assert result is None


class TestFormatCnpjForPick:
    """Testes para _format_cnpj_for_pick."""

    def test_format_cnpj_with_valid_14_digits(self, pick_controller: PickModeController) -> None:
        """_format_cnpj_for_pick com 14 dígitos deve formatar corretamente."""
        # Arrange
        cnpj = "12345678000190"

        # Act
        result = pick_controller._format_cnpj_for_pick(cnpj)

        # Assert
        assert result == "12.345.678/0001-90"

    def test_format_cnpj_with_already_formatted(self, pick_controller: PickModeController) -> None:
        """_format_cnpj_for_pick com CNPJ já formatado deve formatar."""
        # Arrange
        cnpj = "12.345.678/0001-90"

        # Act
        result = pick_controller._format_cnpj_for_pick(cnpj)

        # Assert
        assert result == "12.345.678/0001-90"

    def test_format_cnpj_with_invalid_length(self, pick_controller: PickModeController) -> None:
        """_format_cnpj_for_pick com tamanho inválido deve retornar original."""
        # Arrange
        cnpj = "123456"

        # Act
        result = pick_controller._format_cnpj_for_pick(cnpj)

        # Assert
        assert result == "123456"

    def test_format_cnpj_with_empty_string(self, pick_controller: PickModeController) -> None:
        """_format_cnpj_for_pick com string vazia deve retornar vazia."""
        # Arrange
        cnpj = ""

        # Act
        result = pick_controller._format_cnpj_for_pick(cnpj)

        # Assert
        assert result == ""

    def test_format_cnpj_with_none(self, pick_controller: PickModeController) -> None:
        """_format_cnpj_for_pick com None deve retornar string vazia."""
        # Arrange
        cnpj = None

        # Act
        result = pick_controller._format_cnpj_for_pick(cnpj)

        # Assert
        assert result == ""


class TestPickModeWorkflow:
    """Testes de workflow completo do modo pick."""

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_complete_pick_workflow_success(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """Teste de workflow completo: start → selecionar → confirmar → callback."""
        # Arrange
        picked_client = None

        def on_pick(client: dict) -> None:
            nonlocal picked_client
            picked_client = client

        return_callback = Mock()

        # Act 1: Iniciar modo pick
        pick_controller.start_pick(on_pick=on_pick, return_to=return_callback)
        assert pick_controller.is_active() is True

        # Act 2: Simular seleção de cliente
        mock_frame.client_list.selection.return_value = ("client_456",)
        mock_validate.return_value = (True, "client_456", None)
        mock_frame.client_list.item = Mock(return_value=("client_456", "Empresa XYZ LTDA", "98765432000100"))

        # Act 3: Confirmar seleção
        pick_controller.confirm_pick()

        # Assert
        assert picked_client is not None
        assert picked_client["id"] == "client_456"
        assert picked_client["razao_social"] == "Empresa XYZ LTDA"
        assert picked_client["cnpj"] == "98.765.432/0001-00"
        assert pick_controller.is_active() is False
        return_callback.assert_called_once()

    @patch("src.modules.clientes.views.pick_mode.messagebox.showwarning")
    @patch("src.modules.clientes.views.pick_mode.validate_single_selection")
    def test_complete_pick_workflow_cancel(
        self,
        mock_validate: Mock,
        mock_showwarning: Mock,
        pick_controller: PickModeController,
        mock_frame: Mock,
    ) -> None:
        """Teste de workflow completo: start → cancelar → return_to."""
        # Arrange
        callback = Mock()
        return_callback = Mock()

        # Act 1: Iniciar modo pick
        pick_controller.start_pick(on_pick=callback, return_to=return_callback)
        assert pick_controller.is_active() is True

        # Act 2: Cancelar
        pick_controller.cancel_pick()

        # Assert
        callback.assert_not_called()
        return_callback.assert_called_once()
        assert pick_controller.is_active() is False
