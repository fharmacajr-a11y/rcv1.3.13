"""
Testes para FIX-CLIENTES-001 - Correção do erro de layout no modo pick.

Objetivo: Garantir que o modo pick funciona independente do gerenciador
de layout usado (pack ou grid) para evitar o erro:
"window ...treeview isn't packed"
"""

from __future__ import annotations

import tkinter as tk
from unittest.mock import Mock, patch

import pytest

from src.modules.clientes.views.pick_mode import PickModeController


class TestPickModeBannerPositioning:
    """Testes para posicionamento do banner em diferentes layouts."""

    def test_position_banner_with_grid_layout(self):
        """Banner deve ser posicionado corretamente quando client_list usa grid."""
        # Arrange: mock estrutura sem criar widgets reais
        frame = Mock()

        client_list = Mock()
        client_list.winfo_manager.return_value = "grid"

        container = Mock()
        container.winfo_manager.return_value = "pack"
        container.pack = Mock()

        banner = Mock()
        banner.pack = Mock()

        frame.client_list = client_list
        frame.client_list_container = container
        frame._pick_banner_frame = banner

        controller = PickModeController(frame=frame)

        # Act: posicionar banner
        controller._position_pick_banner()

        # Assert: banner.pack deve ter sido chamado com before=container
        banner.pack.assert_called_once()
        call_kwargs = banner.pack.call_args[1]
        assert call_kwargs.get("before") == container, "Banner deve estar antes do container"

    def test_position_banner_with_pack_layout(self):
        """Banner deve ser posicionado corretamente quando client_list usa pack."""
        # Arrange
        frame = Mock()

        client_list = Mock()
        client_list.winfo_manager.return_value = "pack"

        banner = Mock()
        banner.pack = Mock()

        frame.client_list = client_list
        frame._pick_banner_frame = banner

        controller = PickModeController(frame=frame)

        # Act
        controller._position_pick_banner()

        # Assert: banner.pack deve ter sido chamado com before=client_list
        banner.pack.assert_called_once()
        call_kwargs = banner.pack.call_args[1]
        assert call_kwargs.get("before") == client_list, "Banner deve estar antes do client_list"

    def test_position_banner_handles_tcl_error_gracefully(self):
        """Banner deve tratar TclError sem quebrar o app."""
        # Arrange
        frame = Mock()

        # Simula client_list que causa TclError
        client_list = Mock()
        client_list.winfo_manager.side_effect = tk.TclError("Erro simulado")

        banner = Mock()
        banner.pack = Mock()

        frame.client_list = client_list
        frame._pick_banner_frame = banner

        controller = PickModeController(frame=frame)

        # Act & Assert: não deve propagar exception
        try:
            controller._position_pick_banner()
            # Deve chamar pack como fallback
            assert banner.pack.called, "Fallback pack deve ser chamado"
        except tk.TclError:
            pytest.fail("_position_pick_banner não deve propagar TclError")

    def test_position_banner_with_unknown_manager(self):
        """Banner deve usar fallback pack quando gerenciador é desconhecido."""
        # Arrange
        frame = Mock()

        client_list = Mock()
        client_list.winfo_manager.return_value = ""  # gerenciador vazio

        banner = Mock()
        banner.pack = Mock()

        frame.client_list = client_list
        frame._pick_banner_frame = banner

        controller = PickModeController(frame=frame)

        # Act
        controller._position_pick_banner()

        # Assert: deve usar pack simples sem before
        banner.pack.assert_called_once()
        call_kwargs = banner.pack.call_args[1]
        assert "before" not in call_kwargs, "Não deve usar 'before' com gerenciador desconhecido"


class TestPickModeStartWithDifferentLayouts:
    """Testes de integração do start_pick com diferentes layouts."""

    @patch.object(PickModeController, "_position_pick_banner")
    def test_start_pick_calls_position_banner(self, mock_position):
        """start_pick deve chamar _position_pick_banner."""
        # Arrange
        frame = Mock()
        frame._pick_mode = False
        frame._on_pick = None
        frame._return_to = None
        frame._pick_banner_frame = Mock()
        frame._saved_toolbar_state = {}  # Dict real, não Mock
        frame.carregar = Mock()
        frame._update_main_buttons_state = Mock()
        frame.bind_all = Mock()
        frame.client_list = Mock()
        frame.client_list.unbind = Mock()
        frame.client_list.bind = Mock()

        # Atributos de botões (footer não existe, então não salvará nada)
        frame.footer = None
        frame.btn_novo = None
        frame.btn_editar = None
        frame.btn_subpastas = None
        frame.btn_lixeira = None

        controller = PickModeController(frame=frame)
        mock_callback = Mock()

        # Act
        controller.start_pick(on_pick=mock_callback, return_to=None)

        # Assert
        mock_position.assert_called_once()
        assert controller.is_active(), "Pick mode deve estar ativo"
        assert frame._pick_mode is True, "Frame deve estar em pick mode"
        frame.carregar.assert_called_once()

    def test_stop_pick_hides_banner(self):
        """Desativar pick mode deve esconder o banner."""
        # Arrange
        frame = Mock()
        frame._pick_mode = True
        frame._on_pick = Mock()
        frame._return_to = None
        frame._saved_toolbar_state = {}

        banner = Mock()
        banner.pack_forget = Mock()
        frame._pick_banner_frame = banner

        frame.carregar = Mock()
        frame._update_main_buttons_state = Mock()
        frame.bind_all = Mock()
        frame.unbind_all = Mock()
        frame.client_list = Mock()
        frame.client_list.unbind = Mock()
        frame.client_list.bind = Mock()

        controller = PickModeController(frame=frame, _active=True, _callback=Mock())

        # Act: desativar pick mode
        controller.cancel_pick()

        # Assert
        assert not controller.is_active(), "Pick mode deve estar inativo"
        assert frame._pick_mode is False, "Frame não deve estar em pick mode"
        banner.pack_forget.assert_called_once()


class TestPickModeIntegrationWithPasswordsFlow:
    """Testes simulando o fluxo Senhas → Clientes Picker."""

    @patch("src.modules.clientes.views.pick_mode.log")
    def test_pick_mode_logs_errors_instead_of_crashing(self, mock_log):
        """Erros de layout devem ser logados, não propagados."""
        # Arrange
        frame = Mock()
        frame._pick_banner_frame = Mock()
        frame._pick_banner_frame.pack = Mock(side_effect=tk.TclError("Erro crítico"))
        frame.client_list = Mock()
        frame.client_list.winfo_manager.side_effect = tk.TclError("Erro de layout")

        controller = PickModeController(frame=frame)

        # Act
        controller._position_pick_banner()

        # Assert: deve ter logado a exception
        assert mock_log.exception.called or mock_log.error.called, "Erro deve ser logado"

    def test_pick_callback_receives_formatted_client_data(self):
        """Callback deve receber dados do cliente formatados corretamente."""
        # Arrange
        frame = Mock()
        frame._pick_mode = False
        frame._on_pick = None
        frame._return_to = None
        frame._saved_toolbar_state = {}

        # Mock treeview com cliente selecionado
        client_list = Mock()
        client_list.selection.return_value = ["item1"]
        # item() retorna dict com 'values' como chave
        client_list.item.return_value = {"values": ("123", "ACME LTDA", "12345678000190")}
        client_list.unbind = Mock()
        client_list.bind = Mock()

        frame.client_list = client_list
        frame._pick_banner_frame = Mock()
        frame.carregar = Mock()
        frame._update_main_buttons_state = Mock()
        frame.bind_all = Mock()
        frame.unbind_all = Mock()

        frame.btn_novo = None
        frame.btn_editar = None
        frame.btn_subpastas = None
        frame.btn_lixeira = None

        controller = PickModeController(frame=frame)
        mock_callback = Mock()

        with patch.object(controller, "_position_pick_banner"):
            controller.start_pick(on_pick=mock_callback, return_to=None)

        # Act: confirmar seleção
        # Mockar _get_selected_client_dict para retornar dados diretos
        with patch.object(
            controller,
            "_get_selected_client_dict",
            return_value={"id": "123", "razao_social": "ACME LTDA", "cnpj": "12345678000190"},
        ):
            controller.confirm_pick()

        # Assert: callback deve ter sido chamado com dados formatados
        assert mock_callback.called, "Callback deve ter sido chamado"
        call_args = mock_callback.call_args[0][0]
        assert call_args["id"] == "123"
        assert call_args["razao_social"] == "ACME LTDA"
        assert call_args["cnpj"] == "12.345.678/0001-90", "CNPJ deve estar formatado"


class TestPickModeCNPJFormatting:
    """Testes para formatação de CNPJ no modo pick."""

    def test_format_cnpj_valid(self):
        """CNPJ válido deve ser formatado corretamente."""
        result = PickModeController._format_cnpj_for_pick("12345678000190")
        assert result == "12.345.678/0001-90"

    def test_format_cnpj_already_formatted(self):
        """CNPJ já formatado deve ser mantido."""
        result = PickModeController._format_cnpj_for_pick("12.345.678/0001-90")
        assert result == "12.345.678/0001-90"

    def test_format_cnpj_invalid_length(self):
        """CNPJ com tamanho inválido deve retornar original."""
        result = PickModeController._format_cnpj_for_pick("123456")
        assert result == "123456"

    def test_format_cnpj_empty(self):
        """CNPJ vazio deve retornar string vazia."""
        result = PickModeController._format_cnpj_for_pick("")
        assert result == ""

    def test_format_cnpj_none(self):
        """CNPJ None deve retornar string vazia."""
        result = PickModeController._format_cnpj_for_pick(None)  # type: ignore[arg-type]
        assert result == ""


class TestPickModeEdgeCases:
    """Testes de casos extremos."""

    def test_position_banner_without_container_attribute(self):
        """Deve lidar graciosamente quando container não existe."""
        # Arrange
        frame = Mock(spec=[])

        client_list = Mock()
        client_list.winfo_manager.return_value = "grid"

        banner = Mock()
        banner.pack = Mock()

        frame.client_list = client_list
        frame._pick_banner_frame = banner
        # Explicitamente não adicionar client_list_container

        controller = PickModeController(frame=frame)

        # Act: não deve quebrar
        controller._position_pick_banner()

        # Assert: deve ter tentado pack como fallback (sem before)
        banner.pack.assert_called_once()
        call_kwargs = banner.pack.call_args[1]
        assert "before" not in call_kwargs, "Não deve usar 'before' quando container não existe"

    def test_confirm_pick_without_selection_shows_warning(self):
        """confirm_pick sem seleção deve mostrar aviso."""
        # Arrange
        frame = Mock()
        client_list = Mock()
        client_list.selection.return_value = []  # sem seleção

        frame.client_list = client_list
        frame._pick_mode = True

        controller = PickModeController(frame=frame, _active=True, _callback=Mock())

        # Act & Assert: deve mostrar messagebox
        with patch("src.modules.clientes.views.pick_mode.messagebox.showwarning") as mock_warn:
            controller.confirm_pick()
            mock_warn.assert_called_once()
