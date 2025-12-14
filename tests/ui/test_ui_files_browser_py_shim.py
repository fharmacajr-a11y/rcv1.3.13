"""Testes para o arquivo src/ui/files_browser.py (sombreado por pacote).

Este arquivo .py é "sombreado" pelo pacote src/ui/files_browser/ e não é
importado normalmente via `import src.ui.files_browser`. Para testá-lo,
precisamos carregar o arquivo diretamente usando importlib.util.

Motivo: Python prioriza pacotes (diretórios com __init__.py) sobre módulos
(.py) quando há conflito de nomes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_py_file_directly(file_path: str):
    """Carrega um módulo .py diretamente pelo caminho do arquivo.

    Estratégia baseada em:
    https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

    Args:
        file_path: Caminho absoluto para o arquivo .py

    Returns:
        Módulo carregado
    """
    path = Path(file_path)
    # Usa o nome completo do módulo que deveria ter se não fosse sombreado
    module_name = "src.ui.files_browser"

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


class TestFileBrowserPyShim:
    """Testes para o arquivo src/ui/files_browser.py (shim de compatibilidade)."""

    def test_file_exists(self):
        """Arquivo src/ui/files_browser.py deve existir."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        assert file_path.exists()
        assert file_path.is_file()

    def test_loads_without_error(self):
        """Arquivo deve carregar sem erros."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))
        assert module is not None

    def test_exports_open_files_browser(self):
        """Deve reexportar open_files_browser."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        assert hasattr(module, "open_files_browser")
        assert callable(module.open_files_browser)

    def test_exports_format_cnpj_for_display(self):
        """Deve reexportar format_cnpj_for_display."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        assert hasattr(module, "format_cnpj_for_display")
        assert callable(module.format_cnpj_for_display)

    def test_has_all_attribute(self):
        """Deve ter __all__ definido."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        assert hasattr(module, "__all__")
        assert isinstance(module.__all__, list)

    def test_all_contains_expected_names(self):
        """__all__ deve conter os nomes esperados."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        expected = {"open_files_browser", "format_cnpj_for_display"}
        actual = set(module.__all__)
        assert expected == actual

    def test_open_files_browser_is_from_uploads(self):
        """open_files_browser deve ser o mesmo objeto do módulo uploads."""
        from src.modules.uploads import open_files_browser as expected_func

        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        # Deve ser o mesmo objeto (identity check)
        assert module.open_files_browser is expected_func

    def test_format_cnpj_for_display_is_from_helpers(self):
        """format_cnpj_for_display deve ser o mesmo objeto do módulo helpers."""
        from src.modules.uploads.components.helpers import format_cnpj_for_display as expected_func

        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        # Deve ser o mesmo objeto (identity check)
        assert module.format_cnpj_for_display is expected_func

    def test_module_has_deprecation_notice(self):
        """Módulo deve ter aviso de deprecação no docstring."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "files_browser.py"
        module = load_py_file_directly(str(file_path))

        assert module.__doc__ is not None
        assert "DEPRECATED" in module.__doc__ or "deprecated" in module.__doc__.lower()
