"""
Testes para src/ui/progress/pdf_batch_progress.py

Valida update_progress() com cálculos de % e tempo, _on_close() e is_closed.
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

    class TkStub:
        pass

    class ToplevelStub:
        def __init__(self, parent):
            self.parent = parent
            self._withdrawn = False
            self._title = ""
            self._transient_parent = None
            self._resizable_state = (True, True)
            self._protocol_handlers = {}
            self._destroyed = False

        def withdraw(self):
            self._withdrawn = True

        def title(self, text=None):
            if text is not None:
                self._title = text
            return self._title

        def resizable(self, width, height):
            self._resizable_state = (width, height)

        def transient(self, parent):
            self._transient_parent = parent

        def protocol(self, name, handler):
            self._protocol_handlers[name] = handler

        def destroy(self):
            self._destroyed = True

        def update_idletasks(self):
            pass

        def grab_set(self):
            pass

        def focus_force(self):
            pass

        def winfo_exists(self):
            return not self._destroyed

    class ProgressbarStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self._value = 0.0

        def __setitem__(self, key, value):
            if key == "value":
                self._value = float(value)

        def __getitem__(self, key):
            if key == "value":
                return self._value
            return None

        def pack(self, **kwargs):
            pass

    class LabelStub:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self._text = kwargs.get("text", "")

        def configure(self, **kwargs):
            if "text" in kwargs:
                self._text = kwargs["text"]

        def pack(self, **kwargs):
            pass

    tk_module.Tk = TkStub
    tk_module.Toplevel = ToplevelStub
    tk_module.TclError = Exception

    ttk_module.Progressbar = ProgressbarStub
    ttk_module.Label = LabelStub

    monkeypatch.setitem(sys.modules, "tkinter", tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk_module)

    return tk_module, ttk_module


def _stub_dependencies(monkeypatch):
    """Stub dos módulos auxiliares usados por pdf_batch_progress."""
    window_utils_module = types.ModuleType("src.ui.window_utils")
    window_utils_module.show_centered = MagicMock()
    monkeypatch.setitem(sys.modules, "src.ui.window_utils", window_utils_module)

    paths_module = types.ModuleType("src.utils.paths")
    paths_module.resource_path = MagicMock(return_value="")
    monkeypatch.setitem(sys.modules, "src.utils.paths", paths_module)

    return window_utils_module, paths_module


def test_update_progress_calcula_porcentagem_corretamente(monkeypatch):
    """Valida que update_progress() calcula % corretamente."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    # Stub de time.monotonic
    monkeypatch.setattr("time.monotonic", lambda: 10.0)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    parent = tk_module.Toplevel(None)

    # Cria dialog via __new__ para evitar inicialização completa
    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False
    dialog.start_time = 5.0  # 5 segundos atrás
    dialog.progress = ttk_module.Progressbar(parent)
    dialog.label_subdir = ttk_module.Label(parent, text="")
    dialog.label_bytes = ttk_module.Label(parent, text="")
    dialog.label_eta = ttk_module.Label(parent, text="")
    dialog.update_idletasks = MagicMock()  # Adiciona método necessário

    # Adiciona is_closed property
    @property
    def is_closed_prop(self):
        return self._closed

    type(dialog).is_closed = is_closed_prop

    # Simula progresso: 500KB de 1000KB
    dialog.update_progress(
        processed_bytes=512000,
        total_bytes=1024000,
        current_index=1,
        total_subdirs=2,
        current_subdir=None,
        current_image=None,
    )

    # Verifica que a porcentagem foi calculada corretamente (~50%)
    assert abs(dialog.progress["value"] - 50.0) < 0.1


def test_update_progress_calcula_tempo_estimado(monkeypatch):
    """Valida que update_progress() calcula tempo estimado corretamente."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    # Stub de time.monotonic que simula passagem de tempo
    monkeypatch.setattr("time.monotonic", lambda: 10.0)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    parent = tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False
    dialog.start_time = 5.0  # 5 segundos atrás
    dialog.progress = ttk_module.Progressbar(parent)
    dialog.label_subdir = ttk_module.Label(parent, text="")
    dialog.label_bytes = ttk_module.Label(parent, text="")
    dialog.label_eta = ttk_module.Label(parent, text="")
    dialog.update_idletasks = MagicMock()

    # Adiciona property is_closed ao dialog
    type(dialog).is_closed = property(lambda self: self._closed)

    # Simula: 512KB processados em 5s → velocidade = 102.4 KB/s
    # Restante: 512KB → ETA = ~5 segundos
    dialog.update_progress(
        processed_bytes=512000,
        total_bytes=1024000,
        current_index=1,
        total_subdirs=2,
        current_subdir=None,
        current_image=None,
    )

    # Verifica que o ETA foi atualizado no label
    assert "Tempo estimado:" in dialog.label_eta._text
    assert "00:" in dialog.label_eta._text  # Formato mm:ss


def test_update_progress_atualiza_textos_de_labels(monkeypatch):
    """Valida que update_progress() atualiza textos de Subpasta e KB."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    monkeypatch.setattr("time.monotonic", lambda: 10.0)

    import src.ui.progress.pdf_batch_progress as pdf_progress
    from pathlib import Path

    importlib.reload(pdf_progress)

    parent = tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False
    dialog.start_time = 5.0
    dialog.progress = ttk_module.Progressbar(parent)
    dialog.label_subdir = ttk_module.Label(parent, text="")
    dialog.label_bytes = ttk_module.Label(parent, text="")
    dialog.label_eta = ttk_module.Label(parent, text="")
    dialog.update_idletasks = MagicMock()

    # Adiciona property is_closed ao dialog
    type(dialog).is_closed = property(lambda self: self._closed)

    current_subdir = Path("C:/test/subdir1")

    dialog.update_progress(
        processed_bytes=512000,
        total_bytes=1024000,
        current_index=1,
        total_subdirs=2,
        current_subdir=current_subdir,
        current_image=None,
    )

    # Verifica texto da subpasta
    assert "Subpasta 1/2" in dialog.label_subdir._text
    assert "subdir1" in dialog.label_subdir._text

    # Verifica texto dos bytes
    assert "500 KB de 1000 KB" in dialog.label_bytes._text
    assert "50.0%" in dialog.label_bytes._text


def test_update_progress_retorna_sem_fazer_nada_se_closed(monkeypatch):
    """Valida que update_progress() retorna imediatamente se is_closed for True."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    monkeypatch.setattr("time.monotonic", lambda: 10.0)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    parent = tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = True  # Marcado como fechado
    dialog.start_time = 5.0
    dialog.progress = ttk_module.Progressbar(parent)
    dialog.label_subdir = ttk_module.Label(parent, text="Original")
    dialog.label_bytes = ttk_module.Label(parent, text="Original")
    dialog.label_eta = ttk_module.Label(parent, text="Original")
    dialog.update_idletasks = MagicMock()

    # Adiciona property is_closed ao dialog
    type(dialog).is_closed = property(lambda self: self._closed)

    dialog.update_progress(
        processed_bytes=512000,
        total_bytes=1024000,
        current_index=1,
        total_subdirs=2,
        current_subdir=None,
        current_image=None,
    )

    # Labels não devem ter sido alterados
    assert dialog.label_subdir._text == "Original"
    assert dialog.label_bytes._text == "Original"


def test_on_close_marca_closed_como_true(monkeypatch):
    """Valida que _on_close() marca _closed=True."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False

    # Mock do destroy
    dialog.destroy = MagicMock()

    dialog._on_close()

    assert dialog._closed is True
    dialog.destroy.assert_called_once()


def test_on_close_nao_destroi_se_ja_closed(monkeypatch):
    """Valida que _on_close() não chama destroy() se já estiver fechado."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = True

    dialog.destroy = MagicMock()

    dialog._on_close()

    # destroy não deve ser chamado
    dialog.destroy.assert_not_called()


def test_is_closed_retorna_true_se_closed(monkeypatch):
    """Valida que is_closed retorna True quando _closed=True."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = True

    assert dialog.is_closed is True


def test_is_closed_consulta_winfo_exists_se_nao_closed(monkeypatch):
    """Valida que is_closed consulta winfo_exists() quando _closed=False."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    parent = tk_module.Toplevel(None)
    toplevel = tk_module.Toplevel(parent)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False
    dialog.winfo_exists = toplevel.winfo_exists

    # Quando a janela existe
    assert dialog.is_closed is False

    # Quando a janela foi destruída
    toplevel.destroy()
    assert dialog.is_closed is True


def test_close_chama_on_close(monkeypatch):
    """Valida que close() chama _on_close()."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False
    dialog.destroy = MagicMock()

    dialog.close()

    assert dialog._closed is True


def test_update_progress_com_total_bytes_zero_nao_levanta_erro(monkeypatch):
    """Valida que update_progress() não falha quando total_bytes é 0."""
    tk_module, ttk_module = _stub_tkinter_modules(monkeypatch)
    window_utils, paths = _stub_dependencies(monkeypatch)

    monkeypatch.setattr("time.monotonic", lambda: 10.0)

    import src.ui.progress.pdf_batch_progress as pdf_progress

    importlib.reload(pdf_progress)

    parent = tk_module.Toplevel(None)

    dialog = object.__new__(pdf_progress.PDFBatchProgressDialog)
    dialog._closed = False
    dialog.start_time = 5.0
    dialog.progress = ttk_module.Progressbar(parent)
    dialog.label_subdir = ttk_module.Label(parent, text="")
    dialog.label_bytes = ttk_module.Label(parent, text="")
    dialog.label_eta = ttk_module.Label(parent, text="")
    dialog.update_idletasks = MagicMock()

    # Adiciona property is_closed ao dialog
    type(dialog).is_closed = property(lambda self: self._closed)

    # Não deve levantar erro
    dialog.update_progress(
        processed_bytes=0,
        total_bytes=0,
        current_index=0,
        total_subdirs=0,
        current_subdir=None,
        current_image=None,
    )

    # Porcentagem deve ser 0
    assert dialog.progress["value"] == 0.0
