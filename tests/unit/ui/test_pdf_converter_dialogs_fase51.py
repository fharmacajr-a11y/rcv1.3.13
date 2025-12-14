"""
Testes para src/ui/dialogs/pdf_converter_dialogs.py

Valida apply_app_icon() e wrappers ask_delete_images() e show_conversion_result().
"""

from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock


def _stub_tkinter_modules(monkeypatch):
    """Instala stubs de tkinter/ttk antes do import do módulo."""
    tk_module = types.ModuleType("tkinter")
    ttk_module = types.ModuleType("tkinter.ttk")

    # Classes principais
    class TkStub:
        pass

    class ToplevelStub:
        def __init__(self, parent):
            self.parent = parent
            self._icon_bitmap = None
            self._rc_icon_img = None
            self._withdrawn = False
            self._title = ""
            self._transient_parent = None
            self._resizable_state = (True, True)
            self._protocol_handlers = {}
            self._bindings = {}
            self._grab_set_called = False
            self._focus_force_called = False

        def withdraw(self):
            self._withdrawn = True

        def title(self, text=None):
            if text is not None:
                self._title = text
            return self._title

        def transient(self, parent):
            self._transient_parent = parent

        def resizable(self, width, height):
            self._resizable_state = (width, height)

        def iconbitmap(self, path=None):
            if path is not None:
                self._icon_bitmap = path
            return self._icon_bitmap

        def iconphoto(self, default, *images):
            pass

        def protocol(self, name, handler):
            self._protocol_handlers[name] = handler

        def bind(self, sequence, handler):
            self._bindings[sequence] = handler

        def update_idletasks(self):
            pass

        def grab_set(self):
            self._grab_set_called = True

        def focus_force(self):
            self._focus_force_called = True

        def destroy(self):
            pass

        def wait_window(self, window):
            pass

    class PhotoImageStub:
        def __init__(self, file=None):
            if not file:
                raise ValueError("No file provided")

    class FrameStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent

        def pack(self, **kwargs):
            pass

        def grid(self, **kwargs):
            pass

        def columnconfigure(self, index, **kwargs):
            pass

    class LabelStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self._text = kwargs.get("text", "")

        def pack(self, **kwargs):
            pass

        def grid(self, **kwargs):
            pass

        def configure(self, **kwargs):
            if "text" in kwargs:
                self._text = kwargs["text"]

    class ButtonStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.command = kwargs.get("command")

        def pack(self, **kwargs):
            pass

        def focus_set(self):
            pass

    tk_module.Tk = TkStub
    tk_module.Toplevel = ToplevelStub
    tk_module.PhotoImage = PhotoImageStub
    tk_module.Misc = object

    ttk_module.Frame = FrameStub
    ttk_module.Label = LabelStub
    ttk_module.Button = ButtonStub

    monkeypatch.setitem(sys.modules, "tkinter", tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk_module)

    return tk_module, ttk_module


def _stub_dependencies(monkeypatch):
    """Stub dos módulos auxiliares usados por pdf_converter_dialogs."""
    # Stub de window_utils
    window_utils_module = types.ModuleType("src.ui.window_utils")
    window_utils_module.show_centered = MagicMock()
    monkeypatch.setitem(sys.modules, "src.ui.window_utils", window_utils_module)

    # Stub de constants
    constants_module = types.ModuleType("src.modules.main_window.views.constants")
    constants_module.APP_ICON_PATH = "rc.ico"
    monkeypatch.setitem(sys.modules, "src.modules.main_window.views.constants", constants_module)

    # Stub de helpers
    helpers_module = types.ModuleType("src.modules.main_window.views.helpers")
    helpers_module.resource_path = MagicMock(return_value="path/to/rc.ico")
    monkeypatch.setitem(sys.modules, "src.modules.main_window.views.helpers", helpers_module)

    return window_utils_module, constants_module, helpers_module


def test_apply_app_icon_com_iconbitmap_sucesso(monkeypatch):
    """Valida que apply_app_icon usa window.iconbitmap quando resource_path retorna caminho válido."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    # Importa o módulo após stubs
    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    window = tk_module.Toplevel(None)
    parent = None

    pdf_dialogs.apply_app_icon(window, parent)

    assert window.iconbitmap() == "path/to/rc.ico"
    helpers.resource_path.assert_called_once_with("rc.ico")


def test_apply_app_icon_fallback_iconphoto_quando_iconbitmap_falha(monkeypatch):
    """Valida que apply_app_icon tenta iconphoto quando iconbitmap falha."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    # Força iconbitmap a falhar na primeira tentativa
    original_iconbitmap = tk_module.Toplevel.iconbitmap

    def failing_iconbitmap(self, path=None):
        if path is not None:
            raise Exception("iconbitmap failed")
        return original_iconbitmap(self, path)

    monkeypatch.setattr(tk_module.Toplevel, "iconbitmap", failing_iconbitmap)

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    window = tk_module.Toplevel(None)
    parent = None

    # Deve chamar iconphoto como fallback sem erro
    pdf_dialogs.apply_app_icon(window, parent)

    # Verifica que _rc_icon_img foi setado
    assert hasattr(window, "_rc_icon_img")


def test_apply_app_icon_sem_icon_path_usa_parent(monkeypatch):
    """Valida que apply_app_icon tenta reaproveitar icone do parent quando resource_path falha."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    # resource_path retorna vazio
    helpers.resource_path.side_effect = Exception("No icon")

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    parent = tk_module.Toplevel(None)
    parent._icon_bitmap = "parent_icon.ico"

    window = tk_module.Toplevel(None)

    pdf_dialogs.apply_app_icon(window, parent)

    # Deve tentar reaproveitar icone do parent
    assert window.iconbitmap() == "parent_icon.ico"


def test_apply_app_icon_sem_icon_e_sem_parent_nao_levanta_erro(monkeypatch):
    """Valida que apply_app_icon não levanta erro quando não há ícone disponível."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    helpers.resource_path.return_value = ""

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    window = tk_module.Toplevel(None)
    parent = None

    # Não deve levantar erro
    pdf_dialogs.apply_app_icon(window, parent)


def test_ask_delete_images_retorna_resultado_do_dialog(monkeypatch):
    """Valida que ask_delete_images() retorna o resultado vindo do dialog.show()."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    parent = tk_module.Toplevel(None)

    # Simula o retorno do dialog
    monkeypatch.setattr(pdf_dialogs.PDFDeleteImagesConfirmDialog, "show", lambda self: "yes")

    result = pdf_dialogs.ask_delete_images(parent)

    assert result == "yes"


def test_show_conversion_result_chama_wait_window(monkeypatch):
    """Valida que show_conversion_result() chama parent.wait_window(dialog)."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    parent = tk_module.Toplevel(None)
    wait_window_mock = MagicMock()
    parent.wait_window = wait_window_mock

    pdf_dialogs.show_conversion_result(parent, "Test message")

    # Verifica que wait_window foi chamado com o dialog
    wait_window_mock.assert_called_once()


def test_pdf_delete_images_dialog_retorna_yes_quando_botao_sim_clicado(monkeypatch):
    """Valida que PDFDeleteImagesConfirmDialog retorna 'yes' quando botão Sim é clicado."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    parent = tk_module.Toplevel(None)
    dialog = pdf_dialogs.PDFDeleteImagesConfirmDialog(parent)

    # Simula clique no botão Sim
    dialog.on_yes()

    # wait_window não é executado em teste, então acessamos _result diretamente
    assert dialog._result == "yes"


def test_pdf_delete_images_dialog_retorna_no_quando_botao_nao_clicado(monkeypatch):
    """Valida que PDFDeleteImagesConfirmDialog retorna 'no' quando botão Não é clicado."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    parent = tk_module.Toplevel(None)
    dialog = pdf_dialogs.PDFDeleteImagesConfirmDialog(parent)

    dialog.on_no()

    assert dialog._result == "no"


def test_pdf_delete_images_dialog_retorna_cancel_quando_botao_cancelar_clicado(monkeypatch):
    """Valida que PDFDeleteImagesConfirmDialog retorna 'cancel' quando botão Cancelar é clicado."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, constants, helpers = _stub_dependencies(monkeypatch)

    import src.ui.dialogs.pdf_converter_dialogs as pdf_dialogs

    importlib.reload(pdf_dialogs)

    parent = tk_module.Toplevel(None)
    dialog = pdf_dialogs.PDFDeleteImagesConfirmDialog(parent)

    dialog.on_cancel()

    assert dialog._result == "cancel"
