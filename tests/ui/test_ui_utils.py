"""Testes unitários para src.ui.utils.

Módulo testado: funções utilitárias e mixin de diálogo (OkCancelMixin).
Cobertura esperada: 95%+ (uso de objetos fake, sem Tkinter real).
"""

from unittest.mock import Mock, patch
from src.ui.utils import OkCancelMixin, center_window, center_on_parent, safe_destroy


class TestSafeDestroy:
    """Testes de safe_destroy() - destruição segura de widgets."""

    def test_safe_destroy_none_does_nothing(self):
        """safe_destroy(None) não faz nada."""
        safe_destroy(None)  # não deve lançar exceção

    def test_safe_destroy_widget_not_exists(self):
        """Widget que não existe mais não chama destroy."""
        win = Mock()
        win.winfo_exists.return_value = False

        safe_destroy(win)

        win.winfo_exists.assert_called_once()
        win.destroy.assert_not_called()

    def test_safe_destroy_widget_exists_calls_destroy(self):
        """Widget existente chama destroy."""
        win = Mock()
        win.winfo_exists.return_value = True

        safe_destroy(win)

        win.winfo_exists.assert_called_once()
        win.destroy.assert_called_once()

    def test_safe_destroy_winfo_exists_raises_continues(self):
        """Se winfo_exists lança exceção, ainda tenta destroy."""
        win = Mock()
        win.winfo_exists.side_effect = Exception("winfo_exists error")

        safe_destroy(win)

        # Deve tentar destroy mesmo assim
        win.destroy.assert_called_once()

    def test_safe_destroy_destroy_raises_is_caught(self):
        """Exceção em destroy() é capturada e engolida."""
        win = Mock()
        win.winfo_exists.return_value = True
        win.destroy.side_effect = Exception("destroy error")

        # Não deve lançar exceção
        safe_destroy(win)

        win.destroy.assert_called_once()

    def test_safe_destroy_no_winfo_exists_method(self):
        """Objeto sem winfo_exists ainda tenta destroy."""
        win = Mock(spec=["destroy"])

        safe_destroy(win)

        win.destroy.assert_called_once()

    def test_safe_destroy_no_destroy_method(self):
        """Objeto sem destroy não faz nada."""
        win = Mock(spec=[])

        safe_destroy(win)  # não deve lançar exceção


class TestCenterWindow:
    """Testes de center_window() - centralização na tela."""

    def test_center_window_success(self):
        """Caminho feliz: centraliza janela na tela."""
        win = Mock()
        win.winfo_screenwidth.return_value = 1920
        win.winfo_screenheight.return_value = 1080

        center_window(win, w=800, h=600)

        win.update_idletasks.assert_called_once()
        win.winfo_screenwidth.assert_called_once()
        win.winfo_screenheight.assert_called_once()

        # x = (1920 - 800) // 2 = 560
        # y = (1080 - 600) // 2 = 240
        win.geometry.assert_called_once_with("800x600+560+240")

    def test_center_window_default_size(self):
        """Usa tamanho padrão 1200x500."""
        win = Mock()
        win.winfo_screenwidth.return_value = 1920
        win.winfo_screenheight.return_value = 1080

        center_window(win)

        # x = (1920 - 1200) // 2 = 360
        # y = (1080 - 500) // 2 = 290
        win.geometry.assert_called_once_with("1200x500+360+290")

    def test_center_window_update_fails_fallback(self):
        """Se update_idletasks falha, usa geometria simples."""
        win = Mock()
        win.update_idletasks.side_effect = Exception("update failed")

        center_window(win, w=800, h=600)

        # Deve tentar geometria sem posição
        win.geometry.assert_called_once_with("800x600")

    def test_center_window_geometry_fails_is_caught(self):
        """Se geometry também falha no fallback, engole exceção."""
        win = Mock()
        win.update_idletasks.side_effect = Exception("update failed")
        win.geometry.side_effect = Exception("geometry failed")

        # Não deve lançar exceção
        center_window(win, w=800, h=600)

    def test_center_window_small_screen(self):
        """Tela pequena 1366x768."""
        win = Mock()
        win.winfo_screenwidth.return_value = 1366
        win.winfo_screenheight.return_value = 768

        center_window(win, w=1000, h=700)

        # x = (1366 - 1000) // 2 = 183
        # y = (768 - 700) // 2 = 34
        win.geometry.assert_called_once_with("1000x700+183+34")


class TestCenterOnParent:
    """Testes de center_on_parent() - centralização sobre parent."""

    def test_center_on_parent_with_explicit_parent(self):
        """Caminho feliz: centraliza sobre parent explícito."""
        win = Mock()
        win.winfo_width.return_value = 400
        win.winfo_height.return_value = 300

        parent = Mock()
        parent.winfo_rootx.return_value = 100
        parent.winfo_rooty.return_value = 50
        parent.winfo_width.return_value = 800
        parent.winfo_height.return_value = 600

        result = center_on_parent(win, parent=parent)

        # x = 100 + (800 - 400) // 2 = 100 + 200 = 300
        # y = 50 + (600 - 300) // 2 = 50 + 150 = 200
        win.geometry.assert_called_once_with("+300+200")
        assert result is win

    def test_center_on_parent_with_pad(self):
        """Centralização com padding mínimo."""
        win = Mock()
        win.winfo_width.return_value = 400
        win.winfo_height.return_value = 300

        parent = Mock()
        parent.winfo_rootx.return_value = 5
        parent.winfo_rooty.return_value = 5
        parent.winfo_width.return_value = 450
        parent.winfo_height.return_value = 350

        center_on_parent(win, parent=parent, pad=50)

        # x_calc = 5 + (450 - 400) // 2 = 5 + 25 = 30
        # y_calc = 5 + (350 - 300) // 2 = 5 + 25 = 30
        # Mas pad=50, então max(50, 30) = 50 para ambos
        win.geometry.assert_called_once_with("+50+50")

    def test_center_on_parent_none_uses_master(self):
        """parent=None usa win.master."""
        win = Mock()
        win.winfo_width.return_value = 400
        win.winfo_height.return_value = 300

        master = Mock()
        master.winfo_rootx.return_value = 200
        master.winfo_rooty.return_value = 100
        master.winfo_width.return_value = 800
        master.winfo_height.return_value = 600
        win.master = master

        center_on_parent(win, parent=None)

        # x = 200 + (800 - 400) // 2 = 400
        # y = 100 + (600 - 300) // 2 = 250
        win.geometry.assert_called_once_with("+400+250")

    def test_center_on_parent_none_uses_toplevel(self):
        """parent=None sem master usa winfo_toplevel."""
        win = Mock(
            spec=[
                "update_idletasks",
                "winfo_width",
                "winfo_height",
                "geometry",
                "winfo_toplevel",
                "winfo_screenwidth",
                "winfo_screenheight",
            ]
        )
        win.winfo_width.return_value = 400
        win.winfo_height.return_value = 300

        toplevel = Mock()
        toplevel.winfo_rootx.return_value = 300
        toplevel.winfo_rooty.return_value = 150
        toplevel.winfo_width.return_value = 1000
        toplevel.winfo_height.return_value = 700
        win.winfo_toplevel.return_value = toplevel

        center_on_parent(win, parent=None)

        # x = 300 + (1000 - 400) // 2 = 600
        # y = 150 + (700 - 300) // 2 = 350
        win.geometry.assert_called_once_with("+600+350")

    def test_center_on_parent_fallback_to_screen(self):
        """Falha em parent, usa screen como fallback."""
        win = Mock()
        win.master = None
        win.winfo_toplevel.side_effect = Exception("no toplevel")
        win.winfo_screenwidth.return_value = 1920
        win.winfo_screenheight.return_value = 1080
        win.winfo_width.return_value = 600
        win.winfo_height.return_value = 400

        center_on_parent(win, parent=None)

        # x = (1920 - 600) // 2 = 660
        # y = (1080 - 400) // 2 = 340
        win.geometry.assert_called_with("+660+340")

    def test_center_on_parent_fallback_with_pad(self):
        """Fallback para screen com padding."""
        win = Mock()
        win.update_idletasks.side_effect = Exception("update failed")
        win.winfo_screenwidth.return_value = 1920
        win.winfo_screenheight.return_value = 1080
        win.winfo_width.return_value = 600
        win.winfo_height.return_value = 400

        center_on_parent(win, parent=None, pad=100)

        # x_calc = (1920 - 600) // 2 = 660 -> max(100, 660) = 660
        # y_calc = (1080 - 400) // 2 = 340 -> max(100, 340) = 340
        win.geometry.assert_called_with("+660+340")

    def test_center_on_parent_all_fails(self):
        """Falha completa não lança exceção."""
        win = Mock()
        win.update_idletasks.side_effect = Exception("update failed")
        win.winfo_screenwidth.side_effect = Exception("screen failed")

        # Não deve lançar exceção
        result = center_on_parent(win)
        assert result is win


class TestOkCancelMixin:
    """Testes de OkCancelMixin - mixin para diálogos OK/Cancel."""

    def test_mixin_init(self):
        """Inicialização define _cancel_result."""

        class DummyDialog(OkCancelMixin):
            pass

        dialog = DummyDialog()
        assert dialog._cancel_result is None

    def test_ok_without_finalize(self):
        """_ok() sem _finalize_ok define result e destrói."""

        class DummyDialog(OkCancelMixin):
            def __init__(self):
                super().__init__()
                self.result = None

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy") as mock_destroy:
            dialog._ok(value=42)

            assert dialog.result == 42
            mock_destroy.assert_called_once_with(dialog)

    def test_ok_with_finalize(self):
        """_ok() com _finalize_ok chama finalize e destrói."""

        class DummyDialog(OkCancelMixin):
            def __init__(self):
                super().__init__()
                self.result = None
                self.finalize_called = False

            def _finalize_ok(self, value):
                self.finalize_called = True

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy") as mock_destroy:
            dialog._ok(value="success")

            assert dialog.finalize_called is True
            assert dialog.result == "success"
            mock_destroy.assert_called_once_with(dialog)

    def test_ok_finalize_raises_exception(self):
        """_ok() com _finalize_ok lançando exceção ainda fecha."""

        class DummyDialog(OkCancelMixin):
            def __init__(self):
                super().__init__()
                self.result = None

            def _finalize_ok(self, value):
                raise ValueError("finalize error")

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy") as mock_destroy:
            # Não deve lançar exceção
            dialog._ok(value="data")

            # result ainda deve ser definido
            assert dialog.result == "data"
            mock_destroy.assert_called_once_with(dialog)

    def test_ok_result_assignment_fails(self):
        """_ok() onde atribuição de result falha ainda chama destroy."""

        class DummyDialog(OkCancelMixin):
            @property
            def result(self):
                raise RuntimeError("no result allowed")

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy") as mock_destroy:
            # Não deve lançar exceção
            dialog._ok(value=123)

            mock_destroy.assert_called_once_with(dialog)

    def test_ok_default_value(self):
        """_ok() sem argumento usa True como padrão."""

        class DummyDialog(OkCancelMixin):
            def __init__(self):
                super().__init__()
                self.result = None

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy"):
            dialog._ok()
            assert dialog.result is True

    def test_cancel_sets_result_false(self):
        """_cancel() define result=False e _cancel_result=False."""

        class DummyDialog(OkCancelMixin):
            def __init__(self):
                super().__init__()
                self.result = None

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy") as mock_destroy:
            dialog._cancel()

            assert dialog.result is False
            assert dialog._cancel_result is False
            mock_destroy.assert_called_once_with(dialog)

    def test_cancel_result_assignment_fails(self):
        """_cancel() onde atribuição de result falha ainda chama destroy."""

        class DummyDialog(OkCancelMixin):
            @property
            def result(self):
                raise RuntimeError("no result allowed")

        dialog = DummyDialog()

        with patch("src.ui.utils.safe_destroy") as mock_destroy:
            # Não deve lançar exceção
            dialog._cancel()

            assert dialog._cancel_result is False
            mock_destroy.assert_called_once_with(dialog)

    def test_mixin_with_multiple_inheritance(self):
        """OkCancelMixin funciona com herança múltipla."""

        class BaseWidget:
            def __init__(self):
                self.widget_init = True

        class CustomDialog(OkCancelMixin, BaseWidget):
            def __init__(self):
                super().__init__()
                self.result = None

        dialog = CustomDialog()
        assert dialog.widget_init is True
        assert dialog._cancel_result is None

        with patch("src.ui.utils.safe_destroy"):
            dialog._ok("test")
            assert dialog.result == "test"
