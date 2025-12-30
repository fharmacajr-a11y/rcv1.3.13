"""Testes unitários para o protocolo de feedback UI.

Testa TkFeedback com mocks, sem abrir Tk real.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from src.ui.feedback import (
    BusyHandle,
    NullFeedback,
    ProgressHandle,
    TkFeedback,
    UIFeedback,
    get_ui_feedback,
)

if TYPE_CHECKING:
    pass


class TestProtocolCompliance:
    """Verifica que as classes implementam os protocolos."""

    def test_null_feedback_is_ui_feedback(self) -> None:
        """NullFeedback deve satisfazer o protocolo UIFeedback."""
        fb = NullFeedback()
        assert isinstance(fb, UIFeedback)

    def test_tk_feedback_is_ui_feedback(self) -> None:
        """TkFeedback deve satisfazer o protocolo UIFeedback."""
        fb = TkFeedback(parent=None, allow_toast=False)
        assert isinstance(fb, UIFeedback)

    def test_get_ui_feedback_returns_ui_feedback(self) -> None:
        """get_ui_feedback deve retornar UIFeedback."""
        fb = get_ui_feedback(parent=None)
        assert isinstance(fb, UIFeedback)


class TestNullFeedback:
    """Testes para NullFeedback (implementação no-op)."""

    def test_notify_logs_without_error(self) -> None:
        """notify deve executar sem erro."""
        fb = NullFeedback()
        fb.notify("info", "Título", "Mensagem")
        fb.notify("warning", "Aviso", "Cuidado")
        fb.notify("error", "Erro", "Falha")
        fb.notify("success", "Sucesso", "OK")

    def test_confirm_returns_false(self) -> None:
        """confirm deve sempre retornar False."""
        fb = NullFeedback()
        assert fb.confirm("Título", "Mensagem") is False

    def test_busy_returns_handle(self) -> None:
        """busy deve retornar um BusyHandle válido."""
        fb = NullFeedback()
        handle = fb.busy("Processando...")
        assert isinstance(handle, BusyHandle)
        # Métodos devem executar sem erro
        handle.set_text("Nova mensagem")
        handle.step(1)
        handle.close()

    def test_progress_returns_handle(self) -> None:
        """progress deve retornar um ProgressHandle válido."""
        fb = NullFeedback()
        handle = fb.progress(title="Aguarde", message="Carregando")
        assert isinstance(handle, ProgressHandle)
        # Métodos devem executar sem erro
        handle.set_message("Nova mensagem")
        handle.set_detail("Detalhe")
        handle.set_percent(50.0)
        handle.close()


class TestTkFeedbackMessagebox:
    """Testes para TkFeedback usando messagebox (mocked)."""

    @patch("src.ui.feedback.messagebox")
    def test_notify_info_uses_messagebox(self, mock_messagebox: MagicMock) -> None:
        """notify com kind='info' deve chamar messagebox.showinfo."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.notify("info", "Título Info", "Mensagem info", toast=False)

        mock_messagebox.showinfo.assert_called_once_with("Título Info", "Mensagem info", parent=None)

    @patch("src.ui.feedback.messagebox")
    def test_notify_warning_uses_messagebox(self, mock_messagebox: MagicMock) -> None:
        """notify com kind='warning' deve chamar messagebox.showwarning."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.notify("warning", "Título Aviso", "Mensagem aviso", toast=False)

        mock_messagebox.showwarning.assert_called_once_with("Título Aviso", "Mensagem aviso", parent=None)

    @patch("src.ui.feedback.messagebox")
    def test_notify_error_uses_messagebox(self, mock_messagebox: MagicMock) -> None:
        """notify com kind='error' deve chamar messagebox.showerror."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.notify("error", "Título Erro", "Mensagem erro", toast=False)

        mock_messagebox.showerror.assert_called_once_with("Título Erro", "Mensagem erro", parent=None)

    @patch("src.ui.feedback.messagebox")
    def test_notify_success_uses_showinfo(self, mock_messagebox: MagicMock) -> None:
        """notify com kind='success' deve usar showinfo (fallback)."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.notify("success", "Sucesso", "Operação OK", toast=False)

        mock_messagebox.showinfo.assert_called_once_with("Sucesso", "Operação OK", parent=None)

    @patch("src.ui.feedback.messagebox")
    def test_info_method_calls_showinfo(self, mock_messagebox: MagicMock) -> None:
        """Método info() deve chamar showinfo."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.info("Info", "Mensagem")

        mock_messagebox.showinfo.assert_called_once()

    @patch("src.ui.feedback.messagebox")
    def test_warning_method_calls_showwarning(self, mock_messagebox: MagicMock) -> None:
        """Método warning() deve chamar showwarning."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.warning("Aviso", "Mensagem")

        mock_messagebox.showwarning.assert_called_once()

    @patch("src.ui.feedback.messagebox")
    def test_error_method_calls_showerror(self, mock_messagebox: MagicMock) -> None:
        """Método error() deve chamar showerror."""
        feedback = TkFeedback(parent=None, allow_toast=False)
        feedback.error("Erro", "Mensagem")

        mock_messagebox.showerror.assert_called_once()

    @patch("src.ui.feedback.messagebox")
    def test_confirm_calls_askokcancel(self, mock_messagebox: MagicMock) -> None:
        """confirm deve chamar messagebox.askokcancel."""
        mock_messagebox.askokcancel.return_value = True

        feedback = TkFeedback(parent=None, allow_toast=False)
        result = feedback.confirm("Confirmar?", "Deseja continuar?")

        mock_messagebox.askokcancel.assert_called_once_with("Confirmar?", "Deseja continuar?", parent=None)
        assert result is True


class TestTkFeedbackToast:
    """Testes para TkFeedback usando toast (mocked)."""

    def test_toast_uses_toastnotification_when_available(self) -> None:
        """notify com toast=True deve usar ToastNotification quando disponível."""
        mock_toast_class = MagicMock()
        mock_toast_instance = MagicMock()
        mock_toast_class.return_value = mock_toast_instance

        with patch.dict(
            "sys.modules",
            {"ttkbootstrap.toast": MagicMock(ToastNotification=mock_toast_class)},
        ):
            # Reimport para pegar o mock
            with patch("src.ui.feedback.messagebox") as mock_msgbox:
                feedback = TkFeedback(parent=None, allow_toast=True)

                # Patch direto no método _try_show_toast para simular import
                def patched_try(
                    kind: str,
                    title: str,
                    message: str,
                    duration_ms: int,
                    bootstyle: str | None,
                ) -> bool:
                    try:
                        toast_obj = mock_toast_class(
                            title=title,
                            message=message,
                            duration=duration_ms,
                            bootstyle=bootstyle or "success",
                        )
                        toast_obj.show_toast()
                        return True
                    except Exception:
                        return False

                feedback._try_show_toast = patched_try  # type: ignore[method-assign]
                feedback.notify("success", "Título", "Mensagem", toast=True, duration_ms=1000)

                # Verifica que ToastNotification foi criado e show_toast chamado
                mock_toast_class.assert_called_once()
                mock_toast_instance.show_toast.assert_called_once()

                # Messagebox NÃO deve ser chamado
                mock_msgbox.showinfo.assert_not_called()

    @patch("src.ui.feedback.messagebox")
    def test_toast_fallback_to_modal_on_import_error(self, mock_messagebox: MagicMock) -> None:
        """Se ToastNotification não disponível, deve cair para modal."""
        feedback = TkFeedback(parent=None, allow_toast=True)

        # Force _try_show_toast a falhar
        feedback._try_show_toast = lambda *args, **kwargs: False  # type: ignore[method-assign]

        feedback.notify("info", "Título", "Mensagem", toast=True)

        # Deve cair para modal
        mock_messagebox.showinfo.assert_called_once()


class TestTkFeedbackBusy:
    """Testes para TkFeedback.busy (BusyDialog mocked)."""

    @patch("src.ui.components.progress_dialog.BusyDialog", autospec=False)
    def test_busy_calls_busydialog_and_close(self, mock_busy_dialog: MagicMock) -> None:
        """busy deve criar BusyDialog e close deve fechá-lo."""
        mock_dialog = MagicMock()
        mock_busy_dialog.return_value = mock_dialog

        # Simula um parent válido
        mock_parent = MagicMock()

        with patch.object(TkFeedback, "_resolve_parent", return_value=mock_parent):
            feedback = TkFeedback(parent=mock_parent, allow_toast=False)
            handle = feedback.busy("Carregando...")

            # BusyDialog deve ter sido criado
            mock_busy_dialog.assert_called_once_with(mock_parent, text="Carregando...")

            # set_text e step devem delegar para o dialog
            handle.set_text("Etapa 2")
            mock_dialog.set_text.assert_called_with("Etapa 2")

            handle.step(5)
            mock_dialog.step.assert_called_with(5)

            # close deve fechar o dialog
            handle.close()
            mock_dialog.close.assert_called_once()


class TestTkFeedbackProgress:
    """Testes para TkFeedback.progress (ProgressDialog mocked)."""

    @patch("src.ui.components.progress_dialog.ProgressDialog", autospec=False)
    def test_progress_calls_progressdialog_and_close(self, mock_progress_dialog: MagicMock) -> None:
        """progress deve criar ProgressDialog e close deve fechá-lo."""
        mock_dialog = MagicMock()
        mock_progress_dialog.return_value = mock_dialog

        mock_parent = MagicMock()
        on_cancel_cb = MagicMock()

        with patch.object(TkFeedback, "_resolve_parent", return_value=mock_parent):
            feedback = TkFeedback(parent=mock_parent, allow_toast=False)
            handle = feedback.progress(
                title="Enviando...",
                message="Arquivo 1/10",
                detail="arquivo.pdf",
                can_cancel=True,
                on_cancel=on_cancel_cb,
            )

            # ProgressDialog deve ter sido criado com os parâmetros corretos
            mock_progress_dialog.assert_called_once_with(
                mock_parent,
                title="Enviando...",
                message="Arquivo 1/10",
                detail="arquivo.pdf",
                can_cancel=True,
                on_cancel=on_cancel_cb,
            )

            # set_message, set_detail, set_percent devem delegar
            handle.set_message("Arquivo 2/10")
            mock_dialog.set_message.assert_called_with("Arquivo 2/10")

            handle.set_detail("outro.pdf")
            mock_dialog.set_detail.assert_called_with("outro.pdf")

            handle.set_percent(0.5)
            mock_dialog.set_progress.assert_called_with(0.5)

            # close deve fechar o dialog
            handle.close()
            mock_dialog.close.assert_called_once()


class TestTkFeedbackNoParent:
    """Testes para TkFeedback sem parent válido."""

    def test_busy_without_parent_returns_null_handle(self) -> None:
        """busy sem parent válido deve retornar NullBusyHandle."""
        feedback = TkFeedback(parent=None, allow_toast=False)

        with patch.object(TkFeedback, "_resolve_parent", return_value=None):
            handle = feedback.busy("Teste")

        # Deve ser um handle válido (NullBusyHandle)
        assert isinstance(handle, BusyHandle)
        # Métodos devem executar sem erro
        handle.set_text("X")
        handle.step()
        handle.close()

    def test_progress_without_parent_returns_null_handle(self) -> None:
        """progress sem parent válido deve retornar NullProgressHandle."""
        feedback = TkFeedback(parent=None, allow_toast=False)

        with patch.object(TkFeedback, "_resolve_parent", return_value=None):
            handle = feedback.progress(title="Teste")

        # Deve ser um handle válido (NullProgressHandle)
        assert isinstance(handle, ProgressHandle)
        # Métodos devem executar sem erro
        handle.set_message("X")
        handle.set_detail("Y")
        handle.set_percent(50)
        handle.close()
