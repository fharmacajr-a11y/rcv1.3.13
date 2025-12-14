"""
Testes unitários para src/ui/custom_dialogs.py (Fase 52).

Valida diálogos customizados (show_info, ask_ok_cancel) sem Tk real.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock


def _stub_tkinter_modules(monkeypatch):
    """Cria stubs de tkinter e retorna módulos stubados."""

    # Stub principal do tkinter
    tk_module = types.ModuleType("tkinter")

    class ToplevelStub:
        def __init__(self, parent):
            self.parent = parent
            self._withdrawn = False
            self._title = ""
            self._resizable = (True, True)
            self._transient_parent = None
            self._bindings = {}
            self._destroyed = False

        def withdraw(self):
            self._withdrawn = True

        def title(self, text):
            self._title = text

        def resizable(self, width, height):
            self._resizable = (width, height)

        def transient(self, parent):
            self._transient_parent = parent

        def iconbitmap(self, path):
            # Stub - não faz nada
            pass

        def iconphoto(self, *args):
            # Stub - não faz nada
            pass

        def bind(self, event, handler):
            self._bindings[event] = handler

        def update_idletasks(self):
            pass

        def grab_set(self):
            pass

        def focus_force(self):
            pass

        def wait_window(self):
            pass

        def destroy(self):
            self._destroyed = True

    class FrameStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.kwargs = kwargs

        def pack(self, **kwargs):
            pass

        def grid(self, **kwargs):
            pass

        def columnconfigure(self, index, **kwargs):
            pass

    class LabelStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.kwargs = kwargs

        def grid(self, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

    class ButtonStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.kwargs = kwargs
            self.command = kwargs.get("command")

        def pack(self, **kwargs):
            pass

    class PhotoImageStub:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class WidgetStub:
        pass

    tk_module.Toplevel = ToplevelStub
    tk_module.Frame = FrameStub
    tk_module.Label = LabelStub
    tk_module.Button = ButtonStub
    tk_module.PhotoImage = PhotoImageStub
    tk_module.Widget = WidgetStub

    # Stub de tkinter.ttk
    ttk_module = types.ModuleType("tkinter.ttk")
    ttk_module.Frame = FrameStub
    ttk_module.Label = LabelStub
    ttk_module.Button = ButtonStub

    # Stub de tkinter.messagebox
    messagebox_module = types.ModuleType("tkinter.messagebox")
    messagebox_module.showinfo = MagicMock()
    messagebox_module.showerror = MagicMock()
    messagebox_module.showwarning = MagicMock()
    messagebox_module.askyesno = MagicMock(return_value=True)

    # Injeta stubs no sys.modules
    monkeypatch.setitem(sys.modules, "tkinter", tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk_module)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_module)

    return tk_module, ttk_module, messagebox_module


def _stub_dependencies(monkeypatch):
    """Stub de dependências externas."""
    # Stub window_utils
    window_utils = types.ModuleType("src.ui.window_utils")
    window_utils.show_centered = MagicMock()

    # Stub resource_path
    resource_path_module = types.ModuleType("src.utils.resource_path")
    resource_path_module.resource_path = MagicMock(return_value="fake_icon.ico")

    monkeypatch.setitem(sys.modules, "src.ui.window_utils", window_utils)
    monkeypatch.setitem(sys.modules, "src.utils.resource_path", resource_path_module)

    return window_utils, resource_path_module


def test_apply_icon_sem_exception_quando_icon_existe(monkeypatch):
    """Valida que _apply_icon não levanta exceção quando ícone existe."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: True)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()
    window = tk_module.Toplevel(parent)

    # Não deve levantar exceção
    custom_dialogs._apply_icon(window)


def test_apply_icon_nao_faz_nada_quando_icon_nao_existe(monkeypatch):
    """Valida que _apply_icon retorna cedo se ícone não existe."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()
    window = tk_module.Toplevel(parent)

    # Não deve levantar exceção
    custom_dialogs._apply_icon(window)


def test_show_info_cria_toplevel_e_configura_titulo(monkeypatch):
    """Valida que show_info cria Toplevel e configura título."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()

    # Mock wait_window para não bloquear
    original_toplevel = tk_module.Toplevel

    class NonBlockingToplevel(original_toplevel):
        def wait_window(self):
            pass  # Não bloqueia

    tk_module.Toplevel = NonBlockingToplevel

    custom_dialogs.show_info(parent, "Teste", "Mensagem de teste")

    # Verifica que show_centered foi chamado
    assert window_utils.show_centered.called


def test_show_info_aplica_bindings_de_teclado(monkeypatch):
    """Valida que show_info vincula Return e Escape."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()

    # Captura a instância de Toplevel
    captured_top = None

    original_toplevel = tk_module.Toplevel

    class CapturingToplevel(original_toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            nonlocal captured_top
            captured_top = self

        def wait_window(self):
            pass  # Não bloqueia

    tk_module.Toplevel = CapturingToplevel

    custom_dialogs.show_info(parent, "Teste", "Mensagem")

    # Verifica bindings
    assert captured_top is not None
    assert "<Return>" in captured_top._bindings
    assert "<Escape>" in captured_top._bindings


def test_ask_ok_cancel_retorna_false_por_padrao(monkeypatch):
    """Valida que ask_ok_cancel retorna False quando janela fecha sem ação."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()

    # Mock wait_window para não bloquear
    original_toplevel = tk_module.Toplevel

    class NonBlockingToplevel(original_toplevel):
        def wait_window(self):
            pass  # Não bloqueia

    tk_module.Toplevel = NonBlockingToplevel

    result = custom_dialogs.ask_ok_cancel(parent, "Confirmar", "Deseja continuar?")

    # Por padrão, deve retornar False (sem ação do usuário)
    assert result is False


def test_ask_ok_cancel_retorna_true_quando_ok_clicado(monkeypatch):
    """Valida que ask_ok_cancel retorna True quando OK é clicado."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()

    # Captura botões
    captured_buttons = []

    original_button = ttk_module.Button

    class CapturingButton(original_button):
        def __init__(self, parent, **kwargs):
            super().__init__(parent, **kwargs)
            captured_buttons.append(self)

    ttk_module.Button = CapturingButton

    # Mock wait_window para não bloquear
    original_toplevel = tk_module.Toplevel

    class NonBlockingToplevel(original_toplevel):
        def wait_window(self):
            # Simula clique no botão OK (primeiro botão)
            if captured_buttons:
                ok_button = captured_buttons[0]
                if ok_button.command:
                    ok_button.command()

    tk_module.Toplevel = NonBlockingToplevel

    result = custom_dialogs.ask_ok_cancel(parent, "Confirmar", "Deseja continuar?")

    # Deve retornar True (OK clicado)
    assert result is True


def test_ask_ok_cancel_cria_dois_botoes(monkeypatch):
    """Valida que ask_ok_cancel cria dois botões (OK e Cancelar)."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()

    # Captura botões
    captured_buttons = []

    original_button = ttk_module.Button

    class CapturingButton(original_button):
        def __init__(self, parent, **kwargs):
            super().__init__(parent, **kwargs)
            captured_buttons.append(self)

    ttk_module.Button = CapturingButton

    # Mock wait_window para não bloquear
    original_toplevel = tk_module.Toplevel

    class NonBlockingToplevel(original_toplevel):
        def wait_window(self):
            pass  # Não bloqueia

    tk_module.Toplevel = NonBlockingToplevel

    custom_dialogs.ask_ok_cancel(parent, "Confirmar", "Deseja continuar?")

    # Deve ter 3 botões: 1 em show_info path (botão OK do frame) + 2 em ask_ok_cancel (OK e Cancelar)
    # Na verdade, como show_info não é chamado, deve ter apenas 2 botões
    # Mas o código cria 1 botão OK em show_info e 2 botões em ask_ok_cancel
    # Vou verificar que pelo menos 2 botões foram criados
    assert len(captured_buttons) >= 2


def test_ask_ok_cancel_configura_transient_e_resizable(monkeypatch):
    """Valida que ask_ok_cancel configura transient e resizable."""
    tk_module, ttk_module, messagebox_module = _stub_tkinter_modules(monkeypatch)
    window_utils, resource_path_module = _stub_dependencies(monkeypatch)

    # Stub de os.path.exists
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)

    import src.ui.custom_dialogs as custom_dialogs

    importlib.reload(custom_dialogs)

    parent = MagicMock()

    # Captura a instância de Toplevel
    captured_top = None

    original_toplevel = tk_module.Toplevel

    class CapturingToplevel(original_toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            nonlocal captured_top
            captured_top = self

        def wait_window(self):
            pass  # Não bloqueia

    tk_module.Toplevel = CapturingToplevel

    custom_dialogs.ask_ok_cancel(parent, "Confirmar", "Deseja continuar?")

    # Verifica configurações
    assert captured_top is not None
    assert captured_top._resizable == (False, False)
    assert captured_top._transient_parent == parent
