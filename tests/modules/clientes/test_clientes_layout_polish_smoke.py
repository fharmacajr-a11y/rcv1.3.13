"""
Smoke tests para validar ajustes de layout da Microfase 4.2 (Clientes).

Testa:
- Campo Pesquisar com wrapper CTkFrame (elimina borda dupla)
- ActionBar com botões padronizados (mesma height/corner_radius/font/pady)
- Coluna WhatsApp com heading anchor="w" (alinhado à esquerda)

Filosofia: Validar estrutura/propriedades sem criar GUI completa.
"""

import inspect
import sys
from pathlib import Path
from typing import Any

import pytest

# Adicionar src ao path
src_dir = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(src_dir))

# Importar HAS_CUSTOMTKINTER da fonte oficial (appearance.py)
# Fix Microfase 16: Evita reportConstantRedefinition do Pylance
from src.modules.clientes.appearance import HAS_CUSTOMTKINTER

pytestmark = pytest.mark.skipif(
    not HAS_CUSTOMTKINTER, reason="No module named 'customtkinter'"
)


# =========================================================================
# GRUPO 1: TOOLBAR - VALIDAR WRAPPER DO SEARCH
# =========================================================================
def test_toolbar_imports_without_crash() -> None:
    """Validar que toolbar_ctk pode ser importado sem erro."""
    from src.modules.clientes.views import toolbar_ctk

    assert hasattr(toolbar_ctk, "ClientesToolbarCtk")


def test_toolbar_has_entry_busca_attribute() -> None:
    """Validar que ClientesToolbarCtk tem atributo entry_busca."""
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    # Verificar se __init__ menciona entry_busca
    init_sig = inspect.signature(ClientesToolbarCtk.__init__)
    assert init_sig is not None

    # Verificar se classe tem atributo entry_busca no código-fonte
    source = inspect.getsource(ClientesToolbarCtk)
    assert "self.entry_busca" in source, "entry_busca deve existir no código"


def test_toolbar_search_uses_wrapper_pattern() -> None:
    """Validar que Toolbar usa wrapper CTkFrame para eliminar borda dupla."""
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    source = inspect.getsource(ClientesToolbarCtk)

    # Procurar evidências do wrapper pattern
    assert (
        "search_wrapper" in source
    ), "Deve criar search_wrapper CTkFrame"
    assert (
        "border_width=1" in source
    ), "Wrapper deve ter border_width=1"
    assert (
        'border_width=0' in source or 'border_width = 0' in source
    ), "Entry deve ter border_width=0"
    assert (
        "fg_color=toolbar_bg" in source
    ), "Wrapper deve usar fg_color=toolbar_bg"


# =========================================================================
# GRUPO 2: ACTIONBAR - VALIDAR PADRONIZAÇÃO DE BOTÕES
# =========================================================================
def test_actionbar_imports_without_crash() -> None:
    """Validar que actionbar_ctk pode ser importado sem erro."""
    from src.modules.clientes.views import actionbar_ctk

    assert hasattr(actionbar_ctk, "ClientesActionBarCtk")


def test_actionbar_has_button_attributes() -> None:
    """Validar que ActionBar tem atributos dos 4 botões."""
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    source = inspect.getsource(ClientesActionBarCtk)
    assert "self.btn_novo" in source
    assert "self.btn_editar" in source
    assert "self.btn_subpastas" in source
    assert "self.btn_excluir" in source


def test_actionbar_buttons_use_standardized_constants() -> None:
    """Validar que ActionBar usa constantes padronizadas para botões."""
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    source = inspect.getsource(ClientesActionBarCtk)

    # Procurar constantes de padronização
    assert "BTN_HEIGHT" in source, "Deve definir BTN_HEIGHT"
    assert "BTN_CORNER" in source, "Deve definir BTN_CORNER"
    assert "BTN_PADX" in source, "Deve definir BTN_PADX"
    assert "BTN_PADY" in source, "Deve definir BTN_PADY"
    assert "BTN_FONT" in source, "Deve definir BTN_FONT"

    # Verificar que constantes são usadas nos botões
    assert (
        "height=BTN_HEIGHT" in source
    ), "Botões devem usar height=BTN_HEIGHT"
    assert (
        "corner_radius=BTN_CORNER" in source
    ), "Botões devem usar corner_radius=BTN_CORNER"
    assert (
        "padx=BTN_PADX" in source
    ), "Botões devem usar padx=BTN_PADX"
    assert (
        "pady=BTN_PADY" in source
    ), "Botões devem usar pady=BTN_PADY"
    assert "font=BTN_FONT" in source, "Botões devem usar font=BTN_FONT"


def test_actionbar_buttons_have_same_height() -> None:
    """Validar que todos os botões da ActionBar têm mesma altura (36)."""
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    source = inspect.getsource(ClientesActionBarCtk)

    # Contar ocorrências de BTN_HEIGHT (deve aparecer 4 vezes: novo, editar, arquivos, excluir)
    btn_height_count = source.count("height=BTN_HEIGHT")
    assert (
        btn_height_count >= 4
    ), f"Esperado 4 botões com height=BTN_HEIGHT, encontrado {btn_height_count}"


# =========================================================================
# GRUPO 3: TREEVIEW - VALIDAR COLUNA WHATSAPP ALINHADA
# =========================================================================
def test_lists_imports_without_crash() -> None:
    """Validar que lists.py pode ser importado sem erro."""
    from src.ui.components import lists

    assert hasattr(lists, "create_clients_treeview")
    assert hasattr(lists, "CLIENTS_COL_ANCHOR")


def test_lists_whatsapp_column_anchor_is_left() -> None:
    """Validar que CLIENTS_COL_ANCHOR define WhatsApp como 'w' (esquerda)."""
    from src.ui.components.lists import CLIENTS_COL_ANCHOR

    assert (
        "WhatsApp" in CLIENTS_COL_ANCHOR
    ), "WhatsApp deve estar em CLIENTS_COL_ANCHOR"
    assert (
        CLIENTS_COL_ANCHOR["WhatsApp"] == "w"
    ), "WhatsApp deve ter anchor='w' (esquerda)"


def test_lists_whatsapp_heading_anchor_is_left() -> None:
    """Validar que heading de WhatsApp usa anchor='w' (não 'center')."""
    from src.ui.components.lists import create_clients_treeview

    source = inspect.getsource(create_clients_treeview)

    # Procurar código que aplica anchor no heading
    assert (
        "heading_anchor" in source
    ), "Deve ter lógica para heading_anchor"
    assert (
        'key == "WhatsApp"' in source or "key == 'WhatsApp'" in source
    ), "Deve tratar WhatsApp especialmente"
    assert (
        '"w"' in source or "'w'" in source
    ), "Deve usar 'w' para anchor esquerda"


def test_lists_whatsapp_heading_uses_conditional_anchor() -> None:
    """Validar que heading de WhatsApp usa conditional anchor (não hardcoded 'center')."""
    from src.ui.components.lists import create_clients_treeview

    source = inspect.getsource(create_clients_treeview)

    # Verificar que NÃO usa anchor="center" para todos os headings
    # (versão antiga tinha: tree.heading(key, text=heading, anchor="center"))
    lines_with_heading = [
        line for line in source.split("\n") if "tree.heading" in line
    ]

    # Deve haver lógica de heading_anchor (não hardcoded)
    assert any(
        "heading_anchor" in line for line in lines_with_heading
    ), "Deve usar heading_anchor variável (não hardcoded 'center')"


# =========================================================================
# GRUPO 4: INTEGRAÇÃO - VALIDAR QUE MÓDULOS FUNCIONAM JUNTOS
# =========================================================================
def test_clientes_module_imports_toolbar_and_actionbar() -> None:
    """Validar que módulo Clientes importa Toolbar e ActionBar sem erro."""
    from src.modules.clientes.views import actionbar_ctk, toolbar_ctk

    assert hasattr(toolbar_ctk, "ClientesToolbarCtk")
    assert hasattr(actionbar_ctk, "ClientesActionBarCtk")


def test_clientes_frame_has_toolbar_and_actionbar() -> None:
    """Validar que ClientesFrame referencia toolbar e actionbar."""
    from src.modules.clientes.view import ClientesFrame

    source = inspect.getsource(ClientesFrame)
    assert "toolbar" in source or "Toolbar" in source
    assert "actionbar" in source or "ActionBar" in source


# =========================================================================
# GRUPO 5: CONSTANTES - VALIDAR VALORES PADRONIZADOS
# =========================================================================
def test_actionbar_btn_height_is_36() -> None:
    """Validar que BTN_HEIGHT é 36 (padrão recomendado)."""
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    source = inspect.getsource(ClientesActionBarCtk)
    assert "BTN_HEIGHT = 36" in source, "BTN_HEIGHT deve ser 36"


def test_actionbar_btn_corner_is_6() -> None:
    """Validar que BTN_CORNER é 6 (arredondamento padrão)."""
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    source = inspect.getsource(ClientesActionBarCtk)
    assert "BTN_CORNER = 6" in source, "BTN_CORNER deve ser 6"


def test_actionbar_btn_padx_is_uniform() -> None:
    """Validar que BTN_PADX é uniforme (8 ou 10)."""
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    source = inspect.getsource(ClientesActionBarCtk)
    assert (
        "BTN_PADX = " in source
    ), "Deve definir BTN_PADX como constante"
    # Verificar que valor é razoável (entre 5 e 15)
    import re

    match = re.search(r"BTN_PADX = (\d+)", source)
    assert match, "BTN_PADX deve ter valor numérico"
    padx_value = int(match.group(1))
    assert 5 <= padx_value <= 15, f"BTN_PADX deve estar entre 5 e 15, encontrado {padx_value}"


def test_toolbar_search_wrapper_corner_matches_entry() -> None:
    """Validar que corner_radius do wrapper e entry são iguais."""
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    source = inspect.getsource(ClientesToolbarCtk)

    # Extrair corner_radius do wrapper e entry
    import re

    wrapper_corners = re.findall(
        r"search_wrapper.*?corner_radius=(\d+)", source, re.DOTALL
    )
    entry_corners = re.findall(
        r"self\.entry_busca.*?corner_radius=(\d+)", source, re.DOTALL
    )

    assert (
        len(wrapper_corners) > 0
    ), "Wrapper deve ter corner_radius definido"
    assert (
        len(entry_corners) > 0
    ), "Entry deve ter corner_radius definido"
    assert (
        wrapper_corners[0] == entry_corners[0]
    ), f"corner_radius deve ser igual: wrapper={wrapper_corners[0]}, entry={entry_corners[0]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
