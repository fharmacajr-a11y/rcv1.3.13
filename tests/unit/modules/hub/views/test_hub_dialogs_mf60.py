# -*- coding: utf-8 -*-
"""MF-60: Testes headless para hub_dialogs.py.

Testa wrappers de messagebox e diálogo de edição de notas com patches completos,
sem instanciar Tk real. Meta: 100% coverage.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Module under test
import src.modules.hub.views.hub_dialogs as hub_dialogs


# =============================================================================
# FAKES
# =============================================================================


class FakeWidget:
    """Widget fake para simular parent."""

    def __init__(self) -> None:
        self.destroyed = False

    def winfo_rootx(self) -> int:
        return 100

    def winfo_rooty(self) -> int:
        return 200

    def winfo_width(self) -> int:
        return 800

    def winfo_height(self) -> int:
        return 600


class FakeToplevel(FakeWidget):
    """Toplevel fake para simular diálogo."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__()
        self.parent = parent
        self.title_text = ""
        self.geometry_str = ""
        self.transient_parent = None
        self.grab_set_called = False
        self.bindings: dict[str, Any] = {}
        self.wait_window_called = False

    def title(self, text: str) -> None:
        self.title_text = text

    def geometry(self, geom: str) -> None:
        self.geometry_str = geom

    def transient(self, parent: Any) -> None:
        self.transient_parent = parent

    def grab_set(self) -> None:
        self.grab_set_called = True

    def update_idletasks(self) -> None:
        pass

    def bind(self, event: str, callback: Any) -> None:
        self.bindings[event] = callback

    def wait_window(self) -> None:
        self.wait_window_called = True

    def destroy(self) -> None:
        self.destroyed = True


class FakeFrame(FakeWidget):
    """Frame fake."""

    def pack(self, **kwargs: Any) -> None:  # noqa: ARG002
        pass


class FakeLabel(FakeWidget):
    """Label fake."""

    def __init__(self, parent: Any, **kwargs: Any) -> None:  # noqa: ARG002
        super().__init__()

    def pack(self, **kwargs: Any) -> None:  # noqa: ARG002
        pass


class FakeScrollbar(FakeWidget):
    """Scrollbar fake."""

    def __init__(self, parent: Any) -> None:
        super().__init__()

    def pack(self, **kwargs: Any) -> None:  # noqa: ARG002
        pass

    def config(self, **kwargs: Any) -> None:  # noqa: ARG002
        pass

    def set(self, *_args: Any) -> None:
        """Método set usado por yscrollcommand."""
        pass


class FakeText:
    """Text widget fake."""

    def __init__(self, *_args: Any, **kwargs: Any) -> None:
        self.content = ""
        self.focused = False

    def pack(self, **kwargs: Any) -> None:  # noqa: ARG002
        pass

    def insert(self, _index: str, text: str) -> None:
        self.content = text

    def get(self, _start: str, _end: str) -> str:
        return self.content

    def mark_set(self, _mark: str, _index: str) -> None:
        pass

    def focus_set(self) -> None:
        self.focused = True

    def yview(self, *_args: Any) -> None:
        """Método yview usado pela scrollbar."""
        pass


class FakeButton(FakeWidget):
    """Button fake."""

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        super().__init__()
        self.command = kwargs.get("command")

    def pack(self, **kwargs: Any) -> None:  # noqa: ARG002
        pass


# =============================================================================
# TEST: show_note_editor
# =============================================================================


class TestShowNoteEditor:
    """Testes para show_note_editor (diálogo modal de edição)."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Setup patches para todos os testes."""
        self.fake_parent = FakeWidget()
        self.fake_dialog = FakeToplevel()
        self.fake_text = FakeText()

    @patch("src.modules.hub.views.hub_dialogs.tk.Toplevel")
    @patch("src.modules.hub.views.hub_dialogs.tb.Frame")
    @patch("src.modules.hub.views.hub_dialogs.tb.Label")
    @patch("src.modules.hub.views.hub_dialogs.tb.Scrollbar")
    @patch("src.modules.hub.views.hub_dialogs.tk.Text")
    @patch("src.modules.hub.views.hub_dialogs.tb.Button")
    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_create_new_note_confirmed(
        self,
        mock_messagebox: MagicMock,
        mock_button: MagicMock,
        mock_text: MagicMock,
        mock_scrollbar: MagicMock,
        mock_label: MagicMock,
        mock_frame: MagicMock,
        mock_toplevel: MagicMock,
    ) -> None:
        """Criar nova nota e confirmar."""
        # Setup
        fake_dialog = self.fake_dialog
        fake_text = self.fake_text
        fake_text.content = "Nova nota de teste"

        mock_toplevel.return_value = fake_dialog
        mock_text.return_value = fake_text
        mock_frame.return_value = FakeFrame()
        mock_label.return_value = FakeLabel(None)
        mock_scrollbar.return_value = FakeScrollbar(None)

        # Capturar botões
        buttons_created = []

        def capture_button(parent: Any, **kwargs: Any) -> FakeButton:
            btn = FakeButton(parent, **kwargs)
            buttons_created.append(btn)
            return btn

        mock_button.side_effect = capture_button

        # Executar função (sem note_data = nova nota)
        hub_dialogs.show_note_editor(self.fake_parent, note_data=None)  # type: ignore[arg-type]

        # Simular confirmação
        confirm_btn = buttons_created[0]
        if confirm_btn.command:
            confirm_btn.command()

        # Verificações
        assert mock_toplevel.called
        assert fake_dialog.title_text == "Nova Nota"
        assert fake_dialog.wait_window_called

    @patch("src.modules.hub.views.hub_dialogs.tk.Toplevel")
    @patch("src.modules.hub.views.hub_dialogs.tb.Frame")
    @patch("src.modules.hub.views.hub_dialogs.tb.Label")
    @patch("src.modules.hub.views.hub_dialogs.tb.Scrollbar")
    @patch("src.modules.hub.views.hub_dialogs.tk.Text")
    @patch("src.modules.hub.views.hub_dialogs.tb.Button")
    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_edit_existing_note_confirmed(
        self,
        mock_messagebox: MagicMock,
        mock_button: MagicMock,
        mock_text: MagicMock,
        mock_scrollbar: MagicMock,
        mock_label: MagicMock,
        mock_frame: MagicMock,
        mock_toplevel: MagicMock,
    ) -> None:
        """Editar nota existente e confirmar."""
        # Setup
        fake_dialog = self.fake_dialog
        fake_text = self.fake_text
        fake_text.content = "Nota editada"

        mock_toplevel.return_value = fake_dialog
        mock_text.return_value = fake_text
        mock_frame.return_value = FakeFrame()
        mock_label.return_value = FakeLabel(None)
        mock_scrollbar.return_value = FakeScrollbar(None)

        note_data = {
            "id": "note-123",
            "body": "Texto original",
            "is_pinned": True,
            "is_done": False,
        }

        buttons_created = []

        def capture_button(parent: Any, **kwargs: Any) -> FakeButton:
            btn = FakeButton(parent, **kwargs)
            buttons_created.append(btn)
            return btn

        mock_button.side_effect = capture_button

        # Executar
        hub_dialogs.show_note_editor(self.fake_parent, note_data=note_data)  # type: ignore[arg-type]  # type: ignore[arg-type]

        # Simular confirmação
        confirm_btn = buttons_created[0]
        if confirm_btn.command:
            confirm_btn.command()

        # Verificações
        assert fake_dialog.title_text == "Editar Nota"
        assert fake_text.content == "Texto original"

    @patch("src.modules.hub.views.hub_dialogs.tk.Toplevel")
    @patch("src.modules.hub.views.hub_dialogs.tb.Frame")
    @patch("src.modules.hub.views.hub_dialogs.tb.Label")
    @patch("src.modules.hub.views.hub_dialogs.tb.Scrollbar")
    @patch("src.modules.hub.views.hub_dialogs.tk.Text")
    @patch("src.modules.hub.views.hub_dialogs.tb.Button")
    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_cancel_note_editor(
        self,
        mock_messagebox: MagicMock,
        mock_button: MagicMock,
        mock_text: MagicMock,
        mock_scrollbar: MagicMock,
        mock_label: MagicMock,
        mock_frame: MagicMock,
        mock_toplevel: MagicMock,
    ) -> None:
        """Cancelar edição de nota."""
        # Setup
        fake_dialog = self.fake_dialog
        mock_toplevel.return_value = fake_dialog
        mock_text.return_value = self.fake_text
        mock_frame.return_value = FakeFrame()
        mock_label.return_value = FakeLabel(None)
        mock_scrollbar.return_value = FakeScrollbar(None)

        buttons_created = []

        def capture_button(parent: Any, **kwargs: Any) -> FakeButton:
            btn = FakeButton(parent, **kwargs)
            buttons_created.append(btn)
            return btn

        mock_button.side_effect = capture_button

        # Executar
        hub_dialogs.show_note_editor(self.fake_parent, note_data=None)  # type: ignore[arg-type]

        # Simular cancelamento (segundo botão)
        cancel_btn = buttons_created[1]
        if cancel_btn.command:
            cancel_btn.command()

        # Deve retornar None
        # (não podemos verificar o retorno real porque wait_window é bloqueante,
        # mas podemos verificar que o dialog foi destruído)
        assert fake_dialog.destroyed

    @patch("src.modules.hub.views.hub_dialogs.tk.Toplevel")
    @patch("src.modules.hub.views.hub_dialogs.tb.Frame")
    @patch("src.modules.hub.views.hub_dialogs.tb.Label")
    @patch("src.modules.hub.views.hub_dialogs.tb.Scrollbar")
    @patch("src.modules.hub.views.hub_dialogs.tk.Text")
    @patch("src.modules.hub.views.hub_dialogs.tb.Button")
    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_empty_note_shows_warning(
        self,
        mock_messagebox: MagicMock,
        mock_button: MagicMock,
        mock_text: MagicMock,
        mock_scrollbar: MagicMock,
        mock_label: MagicMock,
        mock_frame: MagicMock,
        mock_toplevel: MagicMock,
    ) -> None:
        """Confirmar com texto vazio deve mostrar warning."""
        # Setup
        fake_dialog = self.fake_dialog
        fake_text = self.fake_text
        fake_text.content = "   "  # Somente espaços

        mock_toplevel.return_value = fake_dialog
        mock_text.return_value = fake_text
        mock_frame.return_value = FakeFrame()
        mock_label.return_value = FakeLabel(None)
        mock_scrollbar.return_value = FakeScrollbar(None)

        buttons_created = []

        def capture_button(parent: Any, **kwargs: Any) -> FakeButton:
            btn = FakeButton(parent, **kwargs)
            buttons_created.append(btn)
            return btn

        mock_button.side_effect = capture_button

        # Executar
        hub_dialogs.show_note_editor(self.fake_parent, note_data=None)  # type: ignore[arg-type]

        # Simular confirmação com texto vazio
        confirm_btn = buttons_created[0]
        if confirm_btn.command:
            confirm_btn.command()

        # Verificar que showwarning foi chamado
        mock_messagebox.showwarning.assert_called_once_with(
            "Campo vazio",
            "O texto da nota não pode estar vazio.",
            parent=fake_dialog,
        )
        # Dialog NÃO deve ser destruído (usuário precisa corrigir)
        assert not fake_dialog.destroyed

    @patch("src.modules.hub.views.hub_dialogs.tk.Toplevel")
    @patch("src.modules.hub.views.hub_dialogs.tb.Frame")
    @patch("src.modules.hub.views.hub_dialogs.tb.Label")
    @patch("src.modules.hub.views.hub_dialogs.tb.Scrollbar")
    @patch("src.modules.hub.views.hub_dialogs.tk.Text")
    @patch("src.modules.hub.views.hub_dialogs.tb.Button")
    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_keyboard_bindings_created(
        self,
        mock_messagebox: MagicMock,
        mock_button: MagicMock,
        mock_text: MagicMock,
        mock_scrollbar: MagicMock,
        mock_label: MagicMock,
        mock_frame: MagicMock,
        mock_toplevel: MagicMock,
    ) -> None:
        """Verificar que bindings de teclado são criados."""
        # Setup
        fake_dialog = self.fake_dialog
        mock_toplevel.return_value = fake_dialog
        mock_text.return_value = self.fake_text
        mock_frame.return_value = FakeFrame()
        mock_label.return_value = FakeLabel(None)
        mock_scrollbar.return_value = FakeScrollbar(None)
        mock_button.return_value = FakeButton(None)

        # Executar
        hub_dialogs.show_note_editor(self.fake_parent, note_data=None)  # type: ignore[arg-type]

        # Verificar bindings
        assert "<Control-Return>" in fake_dialog.bindings
        assert "<Escape>" in fake_dialog.bindings

    @patch("src.modules.hub.views.hub_dialogs.tk.Toplevel")
    @patch("src.modules.hub.views.hub_dialogs.tb.Frame")
    @patch("src.modules.hub.views.hub_dialogs.tb.Label")
    @patch("src.modules.hub.views.hub_dialogs.tb.Scrollbar")
    @patch("src.modules.hub.views.hub_dialogs.tk.Text")
    @patch("src.modules.hub.views.hub_dialogs.tb.Button")
    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_dialog_positioning(
        self,
        mock_messagebox: MagicMock,
        mock_button: MagicMock,
        mock_text: MagicMock,
        mock_scrollbar: MagicMock,
        mock_label: MagicMock,
        mock_frame: MagicMock,
        mock_toplevel: MagicMock,
    ) -> None:
        """Verificar que diálogo é posicionado corretamente."""
        # Setup
        fake_dialog = self.fake_dialog
        mock_toplevel.return_value = fake_dialog
        mock_text.return_value = self.fake_text
        mock_frame.return_value = FakeFrame()
        mock_label.return_value = FakeLabel(None)
        mock_scrollbar.return_value = FakeScrollbar(None)
        mock_button.return_value = FakeButton(None)

        # Executar
        hub_dialogs.show_note_editor(self.fake_parent, note_data=None)  # type: ignore[arg-type]

        # Verificar que geometry foi chamado duas vezes:
        # 1. Tamanho inicial: "500x350"
        # 2. Posicionamento: "+x+y"
        assert "500x350" in fake_dialog.geometry_str or "+" in fake_dialog.geometry_str


# =============================================================================
# TEST: Wrappers de messagebox
# =============================================================================


class TestMessageboxWrappers:
    """Testes para wrappers de messagebox (show_error, show_info, etc.)."""

    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_confirm_delete_note_yes(self, mock_messagebox: MagicMock) -> None:
        """confirm_delete_note retorna True quando usuário confirma."""
        mock_messagebox.askyesno.return_value = True
        parent = FakeWidget()
        note_data = {"body": "Nota para deletar"}

        result = hub_dialogs.confirm_delete_note(parent, note_data)  # type: ignore[arg-type]  # type: ignore[arg-type]

        assert result is True
        mock_messagebox.askyesno.assert_called_once()
        call_args = mock_messagebox.askyesno.call_args
        assert call_args[0][0] == "Confirmar exclusão"
        assert "Nota para deletar" in call_args[0][1]

    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_confirm_delete_note_no(self, mock_messagebox: MagicMock) -> None:
        """confirm_delete_note retorna False quando usuário cancela."""
        mock_messagebox.askyesno.return_value = False
        parent = FakeWidget()
        note_data = {"body": "Outra nota"}

        result = hub_dialogs.confirm_delete_note(parent, note_data)  # type: ignore[arg-type]

        assert result is False

    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_confirm_delete_note_long_body_truncated(self, mock_messagebox: MagicMock) -> None:
        """confirm_delete_note trunca body longo com '...'."""
        mock_messagebox.askyesno.return_value = True
        parent = FakeWidget()
        long_body = "A" * 100  # 100 caracteres
        note_data = {"body": long_body}

        hub_dialogs.confirm_delete_note(parent, note_data)  # type: ignore[arg-type]

        call_args = mock_messagebox.askyesno.call_args
        assert "..." in call_args[0][1]
        # Deve truncar em 50 caracteres
        assert long_body[:50] in call_args[0][1]

    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_show_error(self, mock_messagebox: MagicMock) -> None:
        """show_error chama showerror com argumentos corretos."""
        parent = FakeWidget()
        title = "Erro"
        message = "Algo deu errado"

        hub_dialogs.show_error(parent, title, message)  # type: ignore[arg-type]

        mock_messagebox.showerror.assert_called_once_with(title, message, parent=parent)

    @patch("src.modules.hub.views.hub_dialogs.messagebox")
    def test_show_info(self, mock_messagebox: MagicMock) -> None:
        """show_info chama showinfo com argumentos corretos."""
        parent = FakeWidget()
        title = "Informação"
        message = "Operação concluída"

        hub_dialogs.show_info(parent, title, message)  # type: ignore[arg-type]

        mock_messagebox.showinfo.assert_called_once_with(title, message, parent=parent)


# =============================================================================
# TEST: Estrutura de importação
# =============================================================================


class TestImportStructure:
    """Testes para estrutura de importação do módulo."""

    def test_module_imports(self) -> None:
        """Verificar que imports necessários estão disponíveis."""
        assert hasattr(hub_dialogs, "tk")
        assert hasattr(hub_dialogs, "messagebox")
        assert hasattr(hub_dialogs, "tb")

    def test_module_functions_exported(self) -> None:
        """Verificar que funções principais estão exportadas."""
        assert callable(hub_dialogs.show_note_editor)
        assert callable(hub_dialogs.confirm_delete_note)
        assert callable(hub_dialogs.show_error)
        assert callable(hub_dialogs.show_info)

    def test_module_docstring(self) -> None:
        """Verificar que módulo tem docstring."""
        assert hub_dialogs.__doc__ is not None
        assert "HubDialogs" in hub_dialogs.__doc__
