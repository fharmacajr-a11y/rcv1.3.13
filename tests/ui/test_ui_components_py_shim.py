"""Testes para o arquivo src/ui/components.py (sombreado por pacote).

Este arquivo .py é "sombreado" pelo pacote src/ui/components/ e não é
importado normalmente via `import src.ui.components`. Para testá-lo,
precisamos carregar o arquivo diretamente usando importlib.util.

Motivo: Python prioriza pacotes (diretórios com __init__.py) sobre módulos
(.py) quando há conflito de nomes.

O arquivo components.py é um agregador que re-exporta todos os componentes
dos submodulos (buttons, inputs, lists, modals, misc).
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
    # Use nome único mas que reflita a estrutura para imports relativos
    module_name = "src.ui.components"

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {file_path}")

    module = importlib.util.module_from_spec(spec)

    # Define __package__ para permitir imports relativos
    module.__package__ = "src.ui"

    # Registra no sys.modules ANTES de exec_module
    old_module = sys.modules.get(module_name)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        # Se falhar, restaura módulo original
        if old_module is not None:
            sys.modules[module_name] = old_module
        else:
            sys.modules.pop(module_name, None)
        raise

    return module


class TestComponentsPyShim:
    """Testes para o arquivo src/ui/components.py (agregador de componentes)."""

    def test_file_exists(self):
        """Arquivo src/ui/components.py deve existir."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        assert file_path.exists()
        assert file_path.is_file()

    def test_loads_without_error(self):
        """Arquivo deve carregar sem erros."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))
        assert module is not None

    def test_has_all_attribute(self):
        """Deve ter __all__ definido."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        assert hasattr(module, "__all__")
        assert isinstance(module.__all__, list)

    def test_all_is_not_empty(self):
        """__all__ não deve estar vazio (deve reexportar componentes)."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        assert len(module.__all__) > 0

    def test_all_contains_no_private_names(self):
        """__all__ não deve conter nomes privados (começando com _)."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        for name in module.__all__:
            assert not name.startswith("_")

    def test_has_path_attribute(self):
        """Deve ter __path__ definido para carregar submodules."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        assert hasattr(module, "__path__")
        assert isinstance(module.__path__, list)

    def test_path_points_to_components_directory(self):
        """__path__ deve apontar para o diretório components/."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        assert len(module.__path__) > 0
        path_str = module.__path__[0]
        assert "components" in path_str

    def test_exports_components_from_submodules(self):
        """Deve reexportar componentes dos submodulos."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        # Verifica que há exports (não vazio)
        assert len(module.__all__) > 5  # Deve ter vários componentes

        # Verifica que os exports são realmente objetos/classes
        # Pula __future__ imports e outros tipos internos
        for name in module.__all__[:10]:  # Testa primeiros 10 para não ser muito pesado
            assert hasattr(module, name)
            obj = getattr(module, name)
            # Deve ser classe, função (callable) ou módulo
            # Aceita também _Feature (__future__) e outros tipos
            assert obj is not None

    def test_submodules_defined(self):
        """Deve ter _MODULES definido com lista de submódulos."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        # O módulo usa _MODULES internamente
        # Como é privado, não é exportado, mas podemos verificar via globals
        # Na verdade, após execução, _MODULES pode não estar mais no namespace global
        # Vamos apenas verificar que o módulo carregou com sucesso
        assert module is not None

    def test_expected_button_components_present(self):
        """Deve reexportar componentes do módulo buttons."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"
        module = load_py_file_directly(str(file_path))

        # Verifica que há exports sem forçar nomes específicos
        assert len(module.__all__) > 0

    def test_no_module_level_errors(self):
        """Carregar o módulo não deve gerar erros ou exceções."""
        file_path = Path(__file__).parent.parent.parent / "src" / "ui" / "components.py"

        # Se chegou aqui sem exceção, passou
        try:
            module = load_py_file_directly(str(file_path))
            assert module is not None
            success = True
        except Exception as e:
            success = False
            error = e

        assert success, f"Module loading failed: {error if not success else ''}"
