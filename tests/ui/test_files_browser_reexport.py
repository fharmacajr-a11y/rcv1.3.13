"""Testes de re-export para src.ui.files_browser.

Módulo testado: arquivo de compatibilidade que re-exporta funções de uploads.
Cobertura esperada: 100% (apenas imports e re-exports).

Nota: importa diretamente o arquivo .py, não o pacote files_browser/.
"""

import importlib.util
from pathlib import Path


# Carrega o módulo files_browser.py diretamente (não o pacote files_browser/)
def _load_files_browser_module():
    """Carrega src/ui/files_browser.py diretamente."""
    files_browser_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
    spec = importlib.util.spec_from_file_location("src.ui.files_browser_compat", files_browser_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {files_browser_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFileBrowserReexport:
    """Testes de re-export de funções deprecated."""

    def test_open_files_browser_is_reexported(self):
        """open_files_browser é re-exportado corretamente."""
        module = _load_files_browser_module()

        import src.modules.uploads

        assert hasattr(module, "open_files_browser")
        assert module.open_files_browser is src.modules.uploads.open_files_browser

    def test_format_cnpj_for_display_is_reexported(self):
        """format_cnpj_for_display é re-exportado corretamente."""
        module = _load_files_browser_module()

        from src.modules.uploads.components.helpers import format_cnpj_for_display

        assert hasattr(module, "format_cnpj_for_display")
        assert module.format_cnpj_for_display is format_cnpj_for_display

    def test_all_exports(self):
        """__all__ contém os exports esperados."""
        module = _load_files_browser_module()

        assert hasattr(module, "__all__")
        assert "open_files_browser" in module.__all__
        assert "format_cnpj_for_display" in module.__all__
        assert len(module.__all__) == 2

    def test_module_docstring(self):
        """Módulo tem docstring indicando deprecação."""
        module = _load_files_browser_module()

        assert module.__doc__ is not None
        assert "DEPRECATED" in module.__doc__.upper()
