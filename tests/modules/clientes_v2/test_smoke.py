"""Smoke tests para ClientesV2 - garantir que não quebra na inicialização.

FASE 3.1: Testes de fumaça para validar imports e métodos essenciais.
"""

import pytest


def test_clientesv2_imports():
    """Test que ClientesV2Frame pode ser importado."""
    from src.modules.clientes_v2 import ClientesV2Frame

    assert ClientesV2Frame is not None, "ClientesV2Frame não pode ser None"


def test_clientesv2_has_required_methods():
    """Test que ClientesV2Frame tem métodos essenciais."""
    from src.modules.clientes_v2 import ClientesV2Frame

    required_methods = [
        "force_redraw",
        "_build_ui",
        "_setup_theme_integration",
        "_initial_load",
        "_on_search",
        "_on_clear_search",
        "_on_order_changed",
    ]

    for method in required_methods:
        assert hasattr(ClientesV2Frame, method), f"Método {method} não encontrado em ClientesV2Frame"


def test_clientesv2_has_required_attributes(clientes_v2_frame):
    """Test que ClientesV2Frame possui atributos esperados após construção."""
    frame = clientes_v2_frame

    # Verificar atributos essenciais
    assert hasattr(frame, "toolbar"), "Toolbar não encontrado"
    assert hasattr(frame, "tree_widget"), "tree_widget não encontrado"
    assert hasattr(frame, "_vm"), "ViewModel não encontrado"

    # Verificar que ViewModel está instanciado
    assert frame._vm is not None, "ViewModel não foi instanciado"


def test_clientesv2_toolbar_exists(clientes_v2_frame):
    """Test que toolbar é criado corretamente."""
    frame = clientes_v2_frame

    # Verificar que toolbar existe e é do tipo correto
    assert frame.toolbar is not None, "Toolbar é None"
    assert hasattr(frame.toolbar, "pack_info"), "Toolbar não foi empacotado"


def test_clientesv2_treeview_exists(clientes_v2_frame):
    """Test que Treeview é criado corretamente."""
    frame = clientes_v2_frame

    # Verificar que tree_widget existe
    assert frame.tree_widget is not None, "tree_widget é None"

    # Verificar que é um Treeview (ttk)
    from tkinter import ttk

    assert isinstance(
        frame.tree_widget, ttk.Treeview
    ), f"tree_widget deveria ser ttk.Treeview, mas é {type(frame.tree_widget)}"


def test_clientesv2_viewmodel_initialized(clientes_v2_frame):
    """Test que ViewModel é inicializado com configurações corretas."""
    frame = clientes_v2_frame

    # Verificar que ViewModel tem métodos necessários
    assert hasattr(frame._vm, "refresh_from_service"), "ViewModel não tem refresh_from_service"
    assert hasattr(frame._vm, "set_search_text"), "ViewModel não tem set_search_text"
    assert hasattr(frame._vm, "get_rows"), "ViewModel não tem get_rows"
    assert hasattr(frame._vm, "get_status_choices"), "ViewModel não tem get_status_choices"
    assert hasattr(frame._vm, "set_order_label"), "ViewModel não tem set_order_label"


@pytest.mark.skipif(
    not hasattr(__import__("src.ui.ctk_config", fromlist=["ctk"]), "ctk"), reason="CustomTkinter não disponível"
)
def test_clientesv2_is_ctk_frame():
    """Test que ClientesV2Frame herda de CTkFrame."""
    from src.modules.clientes_v2 import ClientesV2Frame
    from src.ui.ctk_config import ctk

    # Verificar hierarquia de classes
    assert issubclass(ClientesV2Frame, ctk.CTkFrame), "ClientesV2Frame deveria herdar de CTkFrame"
