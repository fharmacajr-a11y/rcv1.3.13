"""
Testes unitários para FIX-CLIENTES-002 e FIX-CLIENTES-005 - UX do modo seleção de clientes.

Valida que:
1. Entrar no pick mode desativa ações perigosas (novo/editar/lixeira/etc)
2. Sair do pick mode restaura o estado original
3. Duplo clique chama on_pick com cliente selecionado
4. Botão Selecionar chama o mesmo fluxo
5. Botão Cancelar NÃO chama on_pick, apenas return_to
6. FIX-CLIENTES-005: Menus superiores (Conversor PDF) são desabilitados
"""

from __future__ import annotations

from unittest.mock import Mock, patch
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass


class TestPickModeEnterExitUI:
    """Testa que entrar/sair do pick mode gerencia estados de botões corretamente."""

    def test_enter_pick_mode_disables_dangerous_actions(self) -> None:
        """Ao entrar no pick mode, botões perigosos (novo/editar/etc) devem ser desabilitados."""
        # Arrange
        frame = Mock(spec=["footer", "btn_lixeira", "_update_main_buttons_state", "app", "_pick_mode_manager"])

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        mock_manager.enter_pick_mode = Mock(return_value=mock_snapshot)
        frame._pick_mode_manager = mock_manager

        footer = Mock()
        footer.enter_pick_mode = Mock()  # FIX-CLIENTES-007: footer agora tem método enter_pick_mode
        frame.footer = footer
        frame.btn_lixeira = Mock()
        frame.btn_lixeira.__getitem__ = Mock(return_value="normal")  # Estado inicial

        # Mock app para set_pick_mode_active
        mock_app = Mock()
        mock_topbar = Mock()
        mock_topbar.set_pick_mode_active = Mock()
        mock_app.topbar = mock_topbar
        frame.app = mock_app

        # Act
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._enter_pick_mode_ui(frame)

        # Assert - FIX-CLIENTES-007: footer.enter_pick_mode() deve ser chamado
        footer.enter_pick_mode.assert_called_once()
        frame.btn_lixeira.configure.assert_called_with(state="disabled")
        mock_topbar.set_pick_mode_active.assert_called_once_with(True)

    def test_leave_pick_mode_restores_state(self) -> None:
        """Ao sair do pick mode, deve chamar _update_main_buttons_state para restaurar."""
        # Arrange
        frame = Mock(
            spec=[
                "footer",
                "_update_main_buttons_state",
                "app",
                "btn_lixeira",
                "_pick_mode_manager",
                "_rebind_double_click_handler",
            ]
        )

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=False,
            should_disable_trash_button=False,
            should_disable_topbar_menus=False,
            should_show_pick_banner=False,
            should_disable_crud_buttons=False,
        )
        mock_manager.exit_pick_mode = Mock(return_value=mock_snapshot)
        mock_manager.get_saved_trash_button_state = Mock(return_value="normal")
        frame._pick_mode_manager = mock_manager

        footer = Mock()
        footer.leave_pick_mode = Mock()  # FIX-CLIENTES-007: footer agora tem método leave_pick_mode
        frame.footer = footer
        frame._update_main_buttons_state = Mock()
        frame._rebind_double_click_handler = Mock()  # MS-23: Mock para _rebind_double_click_handler
        frame.btn_lixeira = Mock()

        # Mock app para set_pick_mode_active
        mock_app = Mock()
        mock_topbar = Mock()
        mock_topbar.set_pick_mode_active = Mock()
        mock_app.topbar = mock_topbar
        frame.app = mock_app

        # Act
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._leave_pick_mode_ui(frame)

        # Assert - FIX-CLIENTES-007: footer.leave_pick_mode() deve ser chamado
        footer.leave_pick_mode.assert_called_once()
        frame._update_main_buttons_state.assert_called_once()
        mock_topbar.set_pick_mode_active.assert_called_once_with(False)

    def test_enter_pick_mode_without_footer_does_not_crash(self) -> None:
        """Se o frame não tiver footer, não deve crashar."""
        # Arrange
        frame = Mock(spec=["_update_main_buttons_state", "app", "_pick_mode_manager"])
        frame.app = None

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        mock_manager.enter_pick_mode = Mock(return_value=mock_snapshot)
        frame._pick_mode_manager = mock_manager

        # Act & Assert (não deve lançar exceção)
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._enter_pick_mode_ui(frame)

    def test_enter_pick_mode_without_lixeira_button_does_not_crash(self) -> None:
        """Se o frame não tiver btn_lixeira, não deve crashar."""
        # Arrange
        frame = Mock(spec=["footer", "_update_main_buttons_state", "app", "_pick_mode_manager"])

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        mock_manager.enter_pick_mode = Mock(return_value=mock_snapshot)
        frame._pick_mode_manager = mock_manager

        frame.footer = Mock()
        frame.footer.btn_novo = Mock()
        frame.footer.btn_editar = Mock()
        frame.footer.btn_subpastas = Mock()
        frame.app = None

        # Act & Assert (não deve lançar exceção)
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._enter_pick_mode_ui(frame)


class TestPickModeDoubleClickAndSelectButton:
    """Testa que duplo clique e botão Selecionar funcionam corretamente."""

    def test_double_click_calls_on_pick_with_selected_client(self) -> None:
        """Duplo clique deve chamar on_pick com os dados do cliente selecionado."""
        # Arrange
        mock_callback = Mock()
        mock_return = Mock()

        frame = Mock()
        frame._saved_toolbar_state = {}  # Dict vazio para evitar erro de iteração
        frame.client_list = Mock()
        frame.client_list.selection.return_value = ("selected_id",)

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = True
        controller._callback = mock_callback
        controller._return_to = mock_return

        # Mockar _get_selected_client_dict para retornar dados
        controller._get_selected_client_dict = Mock(
            return_value={"id": "123", "razao_social": "Empresa Teste", "cnpj": "12345678000199"}
        )

        # Act
        with patch.object(controller, "_ensure_pick_ui"):
            controller.confirm_pick()

        # Assert
        assert mock_callback.called
        call_args = mock_callback.call_args[0][0]
        assert call_args["id"] == "123"
        assert call_args["razao_social"] == "Empresa Teste"
        assert "cnpj" in call_args
        mock_return.assert_called_once()

    def test_select_button_calls_same_flow_as_double_click(self) -> None:
        """Botão Selecionar deve chamar o mesmo fluxo que duplo clique."""
        # Arrange
        mock_callback = Mock()
        mock_return = Mock()

        frame = Mock()
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()
        frame.client_list.selection.return_value = ("selected_id",)

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = True
        controller._callback = mock_callback
        controller._return_to = mock_return

        # Mockar _get_selected_client_dict para retornar dados
        controller._get_selected_client_dict = Mock(
            return_value={"id": "456", "razao_social": "Outra Empresa", "cnpj": "98765432000100"}
        )

        # Act
        with patch.object(controller, "_ensure_pick_ui"):
            controller.confirm_pick()  # Mesmo método chamado pelo botão

        # Assert
        assert mock_callback.called
        call_args = mock_callback.call_args[0][0]
        assert call_args["id"] == "456"
        assert call_args["razao_social"] == "Outra Empresa"
        mock_return.assert_called_once()

    def test_confirm_pick_without_selection_shows_warning(self) -> None:
        """Se não houver seleção, deve mostrar warning e não chamar callback."""
        # Arrange
        mock_callback = Mock()

        frame = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = True
        controller._callback = mock_callback

        # Mockar _get_selected_client_dict para retornar None (sem seleção)
        controller._get_selected_client_dict = Mock(return_value=None)

        # Act
        with patch("tkinter.messagebox.showwarning") as mock_warning:
            controller.confirm_pick()

        # Assert
        mock_warning.assert_called_once()
        mock_callback.assert_not_called()

    def test_confirm_pick_when_not_active_does_nothing(self) -> None:
        """Se pick mode não estiver ativo, confirm_pick não faz nada."""
        # Arrange
        mock_callback = Mock()

        frame = Mock()
        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = False
        controller._callback = mock_callback

        # Act
        controller.confirm_pick()

        # Assert
        mock_callback.assert_not_called()


class TestPickModeCancelButton:
    """Testa que botão Cancelar funciona corretamente."""

    def test_cancel_pick_does_not_call_on_pick(self) -> None:
        """Cancelar NÃO deve chamar on_pick."""
        # Arrange
        mock_callback = Mock()
        mock_return = Mock()

        frame = Mock()
        frame._pick_mode = True
        frame._on_pick = mock_callback
        frame._return_to = mock_return
        frame._pick_banner_frame = Mock()
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = True
        controller._callback = mock_callback
        controller._return_to = mock_return

        # Act
        with patch.object(controller, "_ensure_pick_ui"):
            controller.cancel_pick()

        # Assert
        mock_callback.assert_not_called()
        mock_return.assert_called_once()

    def test_cancel_pick_calls_return_to(self) -> None:
        """Cancelar deve chamar return_to para voltar à tela anterior."""
        # Arrange
        mock_return = Mock()

        frame = Mock()
        frame._pick_mode = True
        frame._return_to = mock_return
        frame._pick_banner_frame = Mock()
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = True
        controller._return_to = mock_return

        # Act
        with patch.object(controller, "_ensure_pick_ui"):
            controller.cancel_pick()

        # Assert
        mock_return.assert_called_once()

    def test_cancel_pick_when_not_active_does_nothing(self) -> None:
        """Se pick mode não estiver ativo, cancel_pick não faz nada."""
        # Arrange
        mock_return = Mock()

        frame = Mock()
        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)
        controller._active = False
        controller._return_to = mock_return

        # Act
        controller.cancel_pick()

        # Assert
        mock_return.assert_not_called()


class TestPickModeUIIntegration:
    """Testa integração entre PickModeController e _enter/_leave_pick_mode_ui."""

    def test_ensure_pick_ui_enable_calls_enter_pick_mode_ui(self) -> None:
        """_ensure_pick_ui(True) deve chamar enter_pick_mode (API pública).

        MS-21: Atualizado para verificar chamada à API pública enter_pick_mode.
        """
        # Arrange
        frame = Mock()
        frame.enter_pick_mode = Mock()  # MS-21: API pública
        # Não definir _pick_banner_frame para que hasattr retorne False
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()
        frame._update_main_buttons_state = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)

        # Act
        controller._ensure_pick_ui(True)

        # Assert - MS-21: Deve chamar API pública enter_pick_mode
        frame.enter_pick_mode.assert_called_once()

    def test_ensure_pick_ui_disable_calls_leave_pick_mode_ui(self) -> None:
        """_ensure_pick_ui(False) deve chamar exit_pick_mode (API pública).

        MS-21: Atualizado para verificar chamada à API pública exit_pick_mode.
        """
        # Arrange
        frame = Mock()
        frame.exit_pick_mode = Mock()  # MS-21: API pública
        frame._pick_banner_frame = Mock()
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()
        frame._update_main_buttons_state = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)

        # Act
        controller._ensure_pick_ui(False)

        # Assert - MS-21: Deve chamar API pública exit_pick_mode
        frame.exit_pick_mode.assert_called_once()

    def test_ensure_pick_ui_without_enter_method_does_not_crash(self) -> None:
        """Se frame não tiver _enter_pick_mode_ui, não deve crashar."""
        # Arrange
        frame = Mock(spec=["_saved_toolbar_state", "client_list", "_update_main_buttons_state"])
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()
        frame._update_main_buttons_state = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)

        # Act & Assert (não deve lançar exceção)
        controller._ensure_pick_ui(True)

    def test_ensure_pick_ui_without_leave_method_does_not_crash(self) -> None:
        """Se frame não tiver _leave_pick_mode_ui, não deve crashar."""
        # Arrange
        frame = Mock(spec=["_saved_toolbar_state", "client_list", "_update_main_buttons_state", "_pick_banner_frame"])
        frame._saved_toolbar_state = {}
        frame.client_list = Mock()
        frame._update_main_buttons_state = Mock()
        frame._pick_banner_frame = Mock()

        from src.modules.clientes.views.pick_mode import PickModeController

        controller = PickModeController(frame=frame)

        # Act & Assert (não deve lançar exceção)
        controller._ensure_pick_ui(False)


__all__ = [
    "TestPickModeEnterExitUI",
    "TestPickModeDoubleClickAndSelectButton",
    "TestPickModeCancelButton",
    "TestPickModeUIIntegration",
    "TestPickModeTextConstants",
    "TestPickModeBannerTextUsage",
    "TestPickModeButtonStatesInPickMode",
    "TestFooterPickModeMethods",
]


class TestFooterPickModeMethods:
    """FIX-CLIENTES-007: Testa métodos enter_pick_mode e leave_pick_mode do ClientesFooter."""

    def test_footer_enter_pick_mode_disables_all_buttons(self, tk_root) -> None:
        """enter_pick_mode deve salvar estados e desabilitar todos os botões do footer."""
        from src.modules.clientes.views.footer import ClientesFooter

        footer = ClientesFooter(
            master=tk_root,
            on_novo=lambda: None,
            on_editar=lambda: None,
            on_subpastas=lambda: None,
            on_batch_delete=lambda: None,
            on_batch_restore=lambda: None,
            on_batch_export=lambda: None,
        )
        footer.pack()
        tk_root.update_idletasks()

        # Garantir estados iniciais variados
        footer.btn_novo.configure(state="normal")
        footer.btn_editar.configure(state="disabled")
        footer.btn_subpastas.configure(state="normal")
        tk_root.update_idletasks()

        # Act
        footer.enter_pick_mode()
        tk_root.update_idletasks()

        # Assert - todos devem estar disabled
        assert str(footer.btn_novo["state"]) == "disabled"
        assert str(footer.btn_editar["state"]) == "disabled"
        assert str(footer.btn_subpastas["state"]) == "disabled"

        # Assert - estados foram salvos
        assert footer.btn_novo in footer._pick_prev_states
        assert footer._pick_prev_states[footer.btn_novo] == "normal"
        assert footer._pick_prev_states[footer.btn_editar] == "disabled"

    def test_footer_leave_pick_mode_restores_saved_states(self, tk_root) -> None:
        """leave_pick_mode deve restaurar os estados originais dos botões."""
        from src.modules.clientes.views.footer import ClientesFooter

        footer = ClientesFooter(
            master=tk_root,
            on_novo=lambda: None,
            on_editar=lambda: None,
            on_subpastas=lambda: None,
            on_batch_delete=lambda: None,
            on_batch_restore=lambda: None,
            on_batch_export=lambda: None,
        )
        footer.pack()
        tk_root.update_idletasks()

        # Configurar estados variados ANTES de entrar em pick mode
        footer.btn_novo.configure(state="normal")
        footer.btn_editar.configure(state="disabled")
        footer.btn_subpastas.configure(state="normal")
        tk_root.update_idletasks()

        # Entrar em pick mode (vai salvar os estados acima)
        footer.enter_pick_mode()
        tk_root.update_idletasks()

        # Verificar que TODOS ficaram disabled
        assert str(footer.btn_novo["state"]) == "disabled"
        assert str(footer.btn_editar["state"]) == "disabled"

        # Act - sair do pick mode
        footer.leave_pick_mode()
        tk_root.update_idletasks()

        # Assert - estados originais devem ser restaurados
        assert str(footer.btn_novo["state"]) == "normal", "btn_novo deve voltar a 'normal'"
        assert str(footer.btn_editar["state"]) == "disabled", "btn_editar deve continuar 'disabled'"
        assert str(footer.btn_subpastas["state"]) == "normal", "btn_subpastas deve voltar a 'normal'"

        # Assert - dicionário de estados foi limpo
        assert len(footer._pick_prev_states) == 0, "Estados salvos devem ser limpos após restauração"

    def test_footer_leave_pick_mode_without_enter_does_not_crash(self, tk_root) -> None:
        """leave_pick_mode sem enter_pick_mode prévio não deve crashar."""
        from src.modules.clientes.views.footer import ClientesFooter

        footer = ClientesFooter(
            master=tk_root,
            on_novo=lambda: None,
            on_editar=lambda: None,
            on_subpastas=lambda: None,
            on_batch_delete=lambda: None,
            on_batch_restore=lambda: None,
            on_batch_export=lambda: None,
        )
        footer.pack()
        tk_root.update_idletasks()

        # Act & Assert - não deve lançar exceção
        footer.leave_pick_mode()
        tk_root.update_idletasks()

    def test_footer_enter_pick_mode_multiple_times_keeps_first_state(self, tk_root) -> None:
        """Chamar enter_pick_mode múltiplas vezes deve preservar o estado original."""
        from src.modules.clientes.views.footer import ClientesFooter

        footer = ClientesFooter(
            master=tk_root,
            on_novo=lambda: None,
            on_editar=lambda: None,
            on_subpastas=lambda: None,
            on_batch_delete=lambda: None,
            on_batch_restore=lambda: None,
            on_batch_export=lambda: None,
        )
        footer.pack()
        tk_root.update_idletasks()

        # Estado inicial
        footer.btn_novo.configure(state="normal")
        tk_root.update_idletasks()

        # Act - entrar em pick mode duas vezes
        footer.enter_pick_mode()
        tk_root.update_idletasks()

        # Verificar que estado foi salvo
        first_saved = footer._pick_prev_states.get(footer.btn_novo)
        assert first_saved == "normal"

        # Modificar estado (simular mudança externa)
        footer.btn_novo.configure(state="active")

        # Entrar novamente
        footer.enter_pick_mode()
        tk_root.update_idletasks()

        # Assert - deve preservar o PRIMEIRO estado salvo
        assert footer._pick_prev_states[footer.btn_novo] == "normal", (
            "Deve manter o estado original (normal), não o intermediário (active)"
        )

        # Sair do pick mode
        footer.leave_pick_mode()
        tk_root.update_idletasks()

        # Assert - deve restaurar para o primeiro estado
        assert str(footer.btn_novo["state"]) == "normal"


class TestPickModeTextConstants:
    """Testa que as constantes de texto estão definidas corretamente."""

    def test_pick_mode_banner_text_is_defined(self) -> None:
        """Constante PICK_MODE_BANNER_TEXT deve estar definida com texto correto."""
        from src.modules.clientes.views.main_screen import PICK_MODE_BANNER_TEXT

        assert "Modo seleção" in PICK_MODE_BANNER_TEXT
        assert "duplo clique" in PICK_MODE_BANNER_TEXT
        assert "🔍" in PICK_MODE_BANNER_TEXT
        assert "dê" in PICK_MODE_BANNER_TEXT

    def test_pick_mode_cancel_text_is_defined(self) -> None:
        """Constante PICK_MODE_CANCEL_TEXT deve estar definida com texto correto."""
        from src.modules.clientes.views.main_screen import PICK_MODE_CANCEL_TEXT

        assert "Cancelar" in PICK_MODE_CANCEL_TEXT
        assert "✖" in PICK_MODE_CANCEL_TEXT

    def test_pick_mode_select_text_is_defined(self) -> None:
        """Constante PICK_MODE_SELECT_TEXT deve estar definida com texto correto."""
        from src.modules.clientes.views.main_screen import PICK_MODE_SELECT_TEXT

        assert "Selecionar" in PICK_MODE_SELECT_TEXT
        assert "✓" in PICK_MODE_SELECT_TEXT


class TestPickModeBannerTextUsage:
    """FIX-CLIENTES-006: Valida que banner/botões usam as constantes corretas (sem mojibake)."""

    def test_pick_label_source_code_uses_banner_text_constant(self) -> None:
        """Código-fonte do banner label deve usar PICK_MODE_BANNER_TEXT (FIX-CLIENTES-006)."""
        # Verificar que o código-fonte usa a constante corretamente
        import inspect
        from src.modules.clientes.views.main_screen_ui_builder import build_pick_mode_banner

        source = inspect.getsource(build_pick_mode_banner)

        # Verificar que PICK_MODE_BANNER_TEXT é usado (não hardcoded)
        assert "text=PICK_MODE_BANNER_TEXT" in source, (
            "Código-fonte deve usar 'text=PICK_MODE_BANNER_TEXT' para o banner label"
        )

        # Verificar que NÃO há mojibake no código
        mojibake_patterns = [
            'text="ðŸ"',  # Emoji corrompido
            'text="Ã',  # Caracteres acentuados corrompidos
            'text="â',  # Checkmark corrompido
        ]
        for pattern in mojibake_patterns:
            assert pattern not in source, f"Código-fonte contém mojibake: {pattern}"

    def test_select_button_source_code_uses_select_text_constant(self) -> None:
        """Código-fonte do botão Selecionar deve usar PICK_MODE_SELECT_TEXT (FIX-CLIENTES-006)."""
        # MS-24: Após refatoração, o banner é criado no UI builder
        import inspect
        from src.modules.clientes.views.main_screen_ui_builder import build_pick_mode_banner

        source = inspect.getsource(build_pick_mode_banner)

        # Verificar que PICK_MODE_SELECT_TEXT é usado (não hardcoded)
        assert "text=PICK_MODE_SELECT_TEXT" in source, (
            "Código-fonte deve usar 'text=PICK_MODE_SELECT_TEXT' para o botão Selecionar"
        )

    def test_cancel_button_source_code_uses_cancel_text_constant(self) -> None:
        """Código-fonte do botão Cancelar deve usar PICK_MODE_CANCEL_TEXT (FIX-CLIENTES-006)."""
        # MS-24: Após refatoração, o banner é criado no UI builder
        import inspect
        from src.modules.clientes.views.main_screen_ui_builder import build_pick_mode_banner

        source = inspect.getsource(build_pick_mode_banner)

        # Verificar que PICK_MODE_CANCEL_TEXT é usado
        assert "text=PICK_MODE_CANCEL_TEXT" in source, (
            "Código-fonte deve usar 'text=PICK_MODE_CANCEL_TEXT' para o botão Cancelar"
        )

    def test_banner_text_is_valid_utf8_no_mojibake(self) -> None:
        """Banner text não deve conter mojibake (FIX-CLIENTES-006)."""
        from src.modules.clientes.views.main_screen import PICK_MODE_BANNER_TEXT

        # Validar que não contém caracteres mojibake comuns
        mojibake_indicators = ["Ã", "Â", "Ã§", "Ã£", "Ãª", "ðŸ", "âœ"]
        for indicator in mojibake_indicators:
            assert indicator not in PICK_MODE_BANNER_TEXT, (
                f"Texto do banner contém mojibake: {indicator!r} em {PICK_MODE_BANNER_TEXT!r}"
            )

        # Validar que contém caracteres UTF-8 corretos
        assert "🔍" in PICK_MODE_BANNER_TEXT, "Deve conter emoji de lupa corretamente"
        assert "seleção" in PICK_MODE_BANNER_TEXT, "Deve conter 'seleção' com ç correto"
        assert "dê" in PICK_MODE_BANNER_TEXT, "Deve conter 'dê' com ê correto"

    def test_select_button_text_is_valid_utf8_no_mojibake(self) -> None:
        """Botão Selecionar não deve conter mojibake (FIX-CLIENTES-006)."""
        from src.modules.clientes.views.main_screen import PICK_MODE_SELECT_TEXT

        # Validar que não contém caracteres mojibake
        mojibake_indicators = ["Ã", "Â", "âœ"]
        for indicator in mojibake_indicators:
            assert indicator not in PICK_MODE_SELECT_TEXT, f"Texto do botão Selecionar contém mojibake: {indicator!r}"

        # Validar que contém caracteres UTF-8 corretos
        assert "✓" in PICK_MODE_SELECT_TEXT, "Deve conter checkmark correto"
        assert "Selecionar" in PICK_MODE_SELECT_TEXT, "Deve conter 'Selecionar'"


class TestPickModeButtonStatesInPickMode:
    """FIX-CLIENTES-006: Valida que botões estão desabilitados durante pick mode."""

    def test_footer_buttons_are_disabled_in_pick_mode(self) -> None:
        """Botões do footer devem estar desabilitados em pick mode (FIX-CLIENTES-006/007)."""
        # Arrange
        frame = Mock(spec=["footer", "btn_lixeira", "_update_main_buttons_state", "app", "_pick_mode_manager"])

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        mock_manager.enter_pick_mode = Mock(return_value=mock_snapshot)
        frame._pick_mode_manager = mock_manager

        footer = Mock()
        footer.enter_pick_mode = Mock()  # FIX-CLIENTES-007: novo método
        frame.footer = footer
        frame.btn_lixeira = Mock()
        frame.btn_lixeira.__getitem__ = Mock(return_value="normal")  # Estado inicial
        mock_app = Mock()
        mock_topbar = Mock()
        mock_topbar.set_pick_mode_active = Mock()
        mock_app.topbar = mock_topbar
        frame.app = mock_app

        # Act
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._enter_pick_mode_ui(frame)

        # Assert - footer.enter_pick_mode() deve ter sido chamado
        footer.enter_pick_mode.assert_called_once()
        # Assert - topbar.set_pick_mode_active(True) deve ter sido chamado
        mock_topbar.set_pick_mode_active.assert_called_once_with(True)

    def test_lixeira_button_is_disabled_in_pick_mode(self) -> None:
        """Botão Lixeira deve estar desabilitado em pick mode (FIX-CLIENTES-007)."""
        # Arrange
        frame = Mock(spec=["footer", "btn_lixeira", "_update_main_buttons_state", "app", "_pick_mode_manager"])

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        mock_manager.enter_pick_mode = Mock(return_value=mock_snapshot)
        frame._pick_mode_manager = mock_manager

        footer = Mock()
        footer.btn_novo = Mock()
        footer.btn_editar = Mock()
        footer.btn_subpastas = Mock()
        frame.footer = footer
        frame.btn_lixeira = Mock()
        frame.btn_lixeira.__getitem__ = Mock(return_value="normal")  # Estado inicial
        mock_app = Mock()
        mock_app.set_pick_mode_active = Mock()
        frame.app = mock_app

        # Act
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._enter_pick_mode_ui(frame)

        # Assert - botão Lixeira deve estar desabilitado (FIX-CLIENTES-007: visível mas disabled)
        frame.btn_lixeira.configure.assert_called_with(state="disabled")

    def test_conversor_pdf_menu_is_disabled_in_pick_mode(self) -> None:
        """Menu Conversor PDF deve estar desabilitado em pick mode (FIX-CLIENTES-006/007)."""
        # Arrange
        frame = Mock(spec=["footer", "btn_lixeira", "_update_main_buttons_state", "app", "_pick_mode_manager"])

        # MS-21: Mock do PickModeManager
        from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot

        mock_manager = Mock()
        mock_snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        mock_manager.enter_pick_mode = Mock(return_value=mock_snapshot)
        frame._pick_mode_manager = mock_manager

        footer = Mock()
        footer.enter_pick_mode = Mock()  # FIX-CLIENTES-007: novo método
        frame.footer = footer
        frame.btn_lixeira = Mock()
        frame.btn_lixeira.__getitem__ = Mock(return_value="normal")  # Estado inicial
        mock_app = Mock()
        mock_topbar = Mock()
        mock_topbar.set_pick_mode_active = Mock()
        mock_app.topbar = mock_topbar
        frame.app = mock_app

        # Act
        from src.modules.clientes.views.main_screen import MainScreenFrame

        MainScreenFrame._enter_pick_mode_ui(frame)

        # Assert - topbar.set_pick_mode_active(True) deve ter sido chamado para desabilitar Conversor PDF
        mock_topbar.set_pick_mode_active.assert_called_once_with(True)
