# -*- coding: utf-8 -*-
"""Testes de lógica de batch operations para MainScreenFrame.

Valida que os callbacks _on_batch_*_clicked:
- Respeitam seleção/estado (não chamam nada se não puder)
- Chamam as funções corretas do ViewModel quando permitidos
- Honram o resultado da confirmação (não prosseguem quando usuário clica "Não")
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest


# ============================================================================ #
# Fixtures
# ============================================================================ #


@pytest.fixture
def mock_frame() -> Mock:
    """Cria mock de MainScreenFrame com métodos batch injetados."""
    frame = Mock()

    # Mock do viewmodel
    frame._vm = Mock()
    frame._vm.delete_clientes_batch = Mock(return_value=(3, []))
    frame._vm.restore_clientes_batch = Mock()
    frame._vm.export_clientes_batch = Mock()

    # MS-13: Mock do coordenador de batch operations
    from src.modules.clientes.controllers.batch_operations import BatchOperationsCoordinator

    frame._batch_coordinator = BatchOperationsCoordinator(frame._vm)

    # Mock de métodos auxiliares
    frame._get_selected_ids = Mock(return_value={"1", "2", "3"})
    frame.carregar = Mock()
    frame._invoke_safe = Mock(side_effect=lambda fn: fn())

    # Injetar os callbacks reais
    from src.modules.clientes.views.main_screen import MainScreenFrame

    frame._on_batch_delete_clicked = lambda: MainScreenFrame._on_batch_delete_clicked(frame)
    frame._on_batch_restore_clicked = lambda: MainScreenFrame._on_batch_restore_clicked(frame)
    frame._on_batch_export_clicked = lambda: MainScreenFrame._on_batch_export_clicked(frame)

    return frame


# ============================================================================ #
# Testes: Batch Delete
# ============================================================================ #


class TestBatchDelete:
    """Testes para _on_batch_delete_clicked."""

    def test_batch_delete_without_selection_does_nothing(self, mock_frame: Mock) -> None:
        """Sem seleção, não deve chamar viewmodel nem mostrar dialogs."""
        mock_frame._get_selected_ids.return_value = set()

        with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
            mock_frame._on_batch_delete_clicked()

        mock_frame._vm.delete_clientes_batch.assert_not_called()
        mock_msg.askyesno.assert_not_called()

    def test_batch_delete_when_helper_disallows_shows_warning(self, mock_frame: Mock) -> None:
        """Quando helper bloqueia, deve mostrar warning e não prosseguir."""
        # MS-13: Agora can_batch_delete está no coordenador, não no main_screen
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete", return_value=False):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_frame._on_batch_delete_clicked()

        mock_msg.showwarning.assert_called_once()
        mock_frame._vm.delete_clientes_batch.assert_not_called()

    def test_batch_delete_user_cancels_confirmation(self, mock_frame: Mock) -> None:
        """Quando usuário cancela confirmação, não deve chamar viewmodel."""
        # MS-13: Agora can_batch_delete está no coordenador
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = False

                mock_frame._on_batch_delete_clicked()

        mock_msg.askyesno.assert_called_once()
        mock_frame._vm.delete_clientes_batch.assert_not_called()

    def test_batch_delete_happy_path_calls_viewmodel_and_reload(self, mock_frame: Mock) -> None:
        """Happy path: deve chamar viewmodel, reload e mostrar sucesso."""
        selected = {"1", "2", "3"}
        mock_frame._get_selected_ids.return_value = selected

        # MS-13: Agora can_batch_delete está no coordenador
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = True

                mock_frame._on_batch_delete_clicked()

        # Verificar chamadas
        mock_msg.askyesno.assert_called_once()
        mock_frame._vm.delete_clientes_batch.assert_called_once_with(selected)
        mock_frame.carregar.assert_called_once()
        mock_msg.showinfo.assert_called_once()

    def test_batch_delete_with_errors_shows_partial_warning(self, mock_frame: Mock) -> None:
        """Com erros parciais, deve mostrar warning com detalhes."""
        selected = {"1", "2", "3"}
        mock_frame._get_selected_ids.return_value = selected
        mock_frame._vm.delete_clientes_batch.return_value = (2, [(3, "Storage error")])

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = True

                mock_frame._on_batch_delete_clicked()

        # Deve mostrar warning (não showinfo)
        mock_msg.showwarning.assert_called_once()
        assert "2/3" in str(mock_msg.showwarning.call_args)

    def test_batch_delete_exception_shows_error_dialog(self, mock_frame: Mock) -> None:
        """Exceção durante delete deve mostrar error dialog."""
        mock_frame._vm.delete_clientes_batch.side_effect = Exception("DB error")

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = True

                mock_frame._on_batch_delete_clicked()

        mock_msg.showerror.assert_called_once()


# ============================================================================ #
# Testes: Batch Restore
# ============================================================================ #


class TestBatchRestore:
    """Testes para _on_batch_restore_clicked."""

    def test_batch_restore_without_selection_does_nothing(self, mock_frame: Mock) -> None:
        """Sem seleção, não deve chamar viewmodel."""
        mock_frame._get_selected_ids.return_value = set()

        with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
            mock_frame._on_batch_restore_clicked()

        mock_frame._vm.restore_clientes_batch.assert_not_called()
        mock_msg.askyesno.assert_not_called()

    def test_batch_restore_when_helper_disallows_shows_warning(self, mock_frame: Mock) -> None:
        """Quando helper bloqueia (ex.: não é lixeira), deve mostrar warning."""
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_restore", return_value=False):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_frame._on_batch_restore_clicked()

        mock_msg.showwarning.assert_called_once()
        mock_frame._vm.restore_clientes_batch.assert_not_called()

    def test_batch_restore_user_cancels_confirmation(self, mock_frame: Mock) -> None:
        """Quando usuário cancela, não deve chamar viewmodel."""
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_restore", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = False

                mock_frame._on_batch_restore_clicked()

        mock_msg.askyesno.assert_called_once()
        mock_frame._vm.restore_clientes_batch.assert_not_called()

    def test_batch_restore_happy_path_calls_viewmodel_and_reload(self, mock_frame: Mock) -> None:
        """Happy path: deve chamar viewmodel, reload e mostrar sucesso."""
        selected = {"1", "2", "3"}
        mock_frame._get_selected_ids.return_value = selected

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_restore", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = True

                mock_frame._on_batch_restore_clicked()

        # Verificar chamadas
        mock_msg.askyesno.assert_called_once()
        mock_frame._vm.restore_clientes_batch.assert_called_once_with(selected)
        mock_frame.carregar.assert_called_once()
        mock_msg.showinfo.assert_called_once()

    def test_batch_restore_exception_shows_error_dialog(self, mock_frame: Mock) -> None:
        """Exceção durante restore deve mostrar error dialog."""
        mock_frame._vm.restore_clientes_batch.side_effect = Exception("DB error")

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_restore", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = True

                mock_frame._on_batch_restore_clicked()

        mock_msg.showerror.assert_called_once()


# ============================================================================ #
# Testes: Batch Export
# ============================================================================ #


class TestBatchExport:
    """Testes para _on_batch_export_clicked."""

    def test_batch_export_without_selection_does_nothing(self, mock_frame: Mock) -> None:
        """Sem seleção, não deve chamar viewmodel."""
        mock_frame._get_selected_ids.return_value = set()

        with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
            mock_frame._on_batch_export_clicked()

        mock_frame._vm.export_clientes_batch.assert_not_called()
        # Export não usa confirmação (não destrutivo)
        mock_msg.askyesno.assert_not_called()

    def test_batch_export_when_helper_disallows_shows_warning(self, mock_frame: Mock) -> None:
        """Quando helper bloqueia, deve mostrar warning."""
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_export", return_value=False):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_frame._on_batch_export_clicked()

        mock_msg.showwarning.assert_called_once()
        mock_frame._vm.export_clientes_batch.assert_not_called()

    def test_batch_export_calls_viewmodel_on_happy_path(self, mock_frame: Mock) -> None:
        """Happy path: deve chamar viewmodel e mostrar info."""
        selected = {"1", "2"}
        mock_frame._get_selected_ids.return_value = selected

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_export", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_frame._on_batch_export_clicked()

        # Verificar chamadas
        mock_frame._vm.export_clientes_batch.assert_called_once_with(selected)
        mock_msg.showinfo.assert_called_once()
        # Export não pede confirmação
        mock_msg.askyesno.assert_not_called()

    def test_batch_export_exception_shows_error_dialog(self, mock_frame: Mock) -> None:
        """Exceção durante export deve mostrar error dialog."""
        mock_frame._vm.export_clientes_batch.side_effect = Exception("Export error")

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_export", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_frame._on_batch_export_clicked()

        mock_msg.showerror.assert_called_once()


# ============================================================================ #
# Testes: Integração com helpers e estado
# ============================================================================ #


class TestBatchLogicIntegration:
    """Testes de integração da lógica batch com helpers e estado."""

    def test_batch_delete_respects_online_state(self, mock_frame: Mock) -> None:
        """Delete deve respeitar estado online do Supabase."""
        with patch("src.modules.clientes.views.main_screen_batch.get_supabase_state", return_value=("offline", None)):
            with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete") as mock_helper:
                mock_helper.return_value = False

                with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                    mock_frame._on_batch_delete_clicked()

                # Deve ter chamado helper com is_online=False
                assert any(call_args.kwargs.get("is_online") is False for call_args in mock_helper.call_args_list)
                mock_msg.showwarning.assert_called_once()

    def test_batch_restore_respects_trash_screen_flag(self, mock_frame: Mock) -> None:
        """Restore deve respeitar is_trash_screen (MainScreenFrame é False)."""
        with patch("src.modules.clientes.controllers.batch_operations.can_batch_restore") as mock_helper:
            mock_helper.return_value = False

            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_frame._on_batch_restore_clicked()

            # Deve ter chamado helper com is_trash_screen=False
            assert any(call_args.kwargs.get("is_trash_screen") is False for call_args in mock_helper.call_args_list)
            mock_msg.showwarning.assert_called_once()

    def test_batch_operations_use_invoke_safe(self, mock_frame: Mock) -> None:
        """Todos callbacks batch devem usar _invoke_safe."""
        mock_frame._invoke_safe.reset_mock()

        with patch("src.modules.clientes.controllers.batch_operations.can_batch_delete", return_value=True):
            with patch("src.modules.clientes.views.main_screen_batch.messagebox") as mock_msg:
                mock_msg.askyesno.return_value = True
                mock_frame._on_batch_delete_clicked()

        # _invoke_safe deve ter sido chamado
        assert mock_frame._invoke_safe.call_count > 0
