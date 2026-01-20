"""
Smoke tests para validar Microfase 4.3: Treeview Heading Skin + WhatsApp.

Testa:
- Heading customizado com background/foreground/padding da paleta
- Coluna WhatsApp com anchor consistente entre heading e column
- tree_heading_bg_active presente nas paletas

Filosofia: Validar estrutura/propriedades sem criar GUI completa.
"""

import inspect
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Adicionar src ao path
src_dir = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(src_dir))

# Detectar se ttkbootstrap está disponível
try:
    import ttkbootstrap as tb  # noqa: F401

    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False


# =========================================================================
# GRUPO 1: PALETA - VALIDAR tree_heading_bg_active
# =========================================================================
def test_light_palette_has_tree_heading_bg_active() -> None:
    """Validar que LIGHT_PALETTE tem tree_heading_bg_active."""
    from src.modules.clientes.appearance import LIGHT_PALETTE

    assert (
        "tree_heading_bg_active" in LIGHT_PALETTE
    ), "LIGHT_PALETTE deve ter tree_heading_bg_active"
    assert isinstance(
        LIGHT_PALETTE["tree_heading_bg_active"], str
    ), "tree_heading_bg_active deve ser string (hex color)"
    assert LIGHT_PALETTE["tree_heading_bg_active"].startswith(
        "#"
    ), "tree_heading_bg_active deve ser cor hex"


def test_dark_palette_has_tree_heading_bg_active() -> None:
    """Validar que DARK_PALETTE tem tree_heading_bg_active."""
    from src.modules.clientes.appearance import DARK_PALETTE

    assert (
        "tree_heading_bg_active" in DARK_PALETTE
    ), "DARK_PALETTE deve ter tree_heading_bg_active"
    assert isinstance(
        DARK_PALETTE["tree_heading_bg_active"], str
    ), "tree_heading_bg_active deve ser string (hex color)"
    assert DARK_PALETTE["tree_heading_bg_active"].startswith(
        "#"
    ), "tree_heading_bg_active deve ser cor hex"


def test_light_palette_heading_bg_active_darker_than_heading_bg() -> None:
    """Validar que tree_heading_bg_active é mais escuro que tree_heading_bg no tema claro."""
    from src.modules.clientes.appearance import LIGHT_PALETTE

    # Converter hex para int para comparar luminosidade aproximada
    def hex_to_brightness(hex_color: str) -> int:
        """Calcula brightness aproximado de cor hex."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r + g + b) // 3

    bg_brightness = hex_to_brightness(LIGHT_PALETTE["tree_heading_bg"])
    active_brightness = hex_to_brightness(
        LIGHT_PALETTE["tree_heading_bg_active"]
    )

    assert (
        active_brightness < bg_brightness
    ), "tree_heading_bg_active deve ser mais escuro no tema claro (hover)"


def test_dark_palette_heading_bg_active_lighter_than_heading_bg() -> None:
    """Validar que tree_heading_bg_active é mais claro que tree_heading_bg no tema escuro."""
    from src.modules.clientes.appearance import DARK_PALETTE

    # Converter hex para int para comparar luminosidade aproximada
    def hex_to_brightness(hex_color: str) -> int:
        """Calcula brightness aproximado de cor hex."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r + g + b) // 3

    bg_brightness = hex_to_brightness(DARK_PALETTE["tree_heading_bg"])
    active_brightness = hex_to_brightness(
        DARK_PALETTE["tree_heading_bg_active"]
    )

    assert (
        active_brightness > bg_brightness
    ), "tree_heading_bg_active deve ser mais claro no tema escuro (hover)"


# =========================================================================
# GRUPO 2: REAPPLY STYLE - VALIDAR heading_bg_active
# =========================================================================
@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_style_signature_includes_heading_bg_active() -> None:
    """Validar que reapply_clientes_treeview_style aceita heading_bg_active."""
    from src.ui.components.lists import reapply_clientes_treeview_style

    sig = inspect.signature(reapply_clientes_treeview_style)
    params = list(sig.parameters.keys())

    assert (
        "heading_bg_active" in params
    ), "reapply_clientes_treeview_style deve aceitar heading_bg_active"


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_style_uses_heading_bg_active_in_map() -> None:
    """Validar que reapply_clientes_treeview_style usa heading_bg_active no style.map."""
    from src.ui.components.lists import reapply_clientes_treeview_style

    mock_style = Mock()
    mock_style.configure = Mock()
    mock_style.map = Mock()

    reapply_clientes_treeview_style(
        mock_style,
        base_bg="#FFFFFF",
        base_fg="#000000",
        field_bg="#FFFFFF",
        heading_bg="#E0E0E0",
        heading_fg="#000000",
        heading_bg_active="#C8C8C8",
        selected_bg="#0078D7",
        selected_fg="#FFFFFF",
    )

    # Verificar que style.map foi chamado para Heading
    map_calls = mock_style.map.call_args_list
    heading_map_calls = [
        call
        for call in map_calls
        if call[0] and "Heading" in str(call[0][0])
    ]

    assert len(heading_map_calls) > 0, "Deve chamar style.map para Heading"


# =========================================================================
# GRUPO 3: HEADING STYLE - VALIDAR PADDING
# =========================================================================
@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_style_configures_heading_padding() -> None:
    """Validar que reapply_clientes_treeview_style configura padding no heading."""
    from src.ui.components.lists import reapply_clientes_treeview_style

    source = inspect.getsource(reapply_clientes_treeview_style)

    # Procurar evidências de padding no heading
    assert "padding" in source, "Deve configurar padding no heading"
    assert (
        "8, 6" in source or "(8, 6)" in source or "8,6" in source
    ), "Deve usar padding=(8, 6)"


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_configure_clients_treeview_style_configures_heading_padding() -> None:
    """Validar que _configure_clients_treeview_style também configura padding."""
    from src.ui.components.lists import _configure_clients_treeview_style

    source = inspect.getsource(_configure_clients_treeview_style)

    # Procurar evidências de padding no heading
    assert (
        "padding" in source
    ), "_configure_clients_treeview_style deve configurar padding"


# =========================================================================
# GRUPO 4: WHATSAPP - VALIDAR ANCHOR CONSISTENTE
# =========================================================================
def test_create_clients_treeview_whatsapp_column_exists() -> None:
    """Validar que coluna WhatsApp existe nas definições."""
    from src.ui.components.lists import create_clients_treeview

    source = inspect.getsource(create_clients_treeview)

    # Procurar definição da coluna WhatsApp
    assert (
        '"WhatsApp"' in source or "'WhatsApp'" in source
    ), "Deve definir coluna WhatsApp"
    assert (
        "columns =" in source
    ), "Deve ter tupla columns com definições"


def test_create_clients_treeview_whatsapp_heading_anchor_matches_column() -> None:
    """Validar que heading e column de WhatsApp usam mesmo anchor."""
    from src.ui.components.lists import (
        CLIENTS_COL_ANCHOR,
        create_clients_treeview,
    )

    # Verificar CLIENTS_COL_ANCHOR
    assert (
        "WhatsApp" in CLIENTS_COL_ANCHOR
    ), "CLIENTS_COL_ANCHOR deve ter WhatsApp"
    whatsapp_anchor = CLIENTS_COL_ANCHOR["WhatsApp"]

    # Verificar código de create_clients_treeview
    source = inspect.getsource(create_clients_treeview)

    # Deve ter lógica que aplica anchor no heading baseado na key
    assert (
        "heading_anchor" in source
    ), "Deve ter lógica de heading_anchor"
    assert (
        'key == "WhatsApp"' in source or "key == 'WhatsApp'" in source
    ), "Deve tratar WhatsApp especialmente"

    # Verificar que aplica o mesmo anchor (\"w\" ou \"center\")
    if whatsapp_anchor == "w":
        assert (
            '"w"' in source or "'w'" in source
        ), "Deve usar 'w' para WhatsApp"
    elif whatsapp_anchor == "center":
        assert (
            '"center"' in source or "'center'" in source
        ), "Deve usar 'center' para WhatsApp"


def test_clients_col_anchor_whatsapp_is_left_aligned() -> None:
    """Validar que WhatsApp usa alinhamento à esquerda (decisão do projeto)."""
    from src.ui.components.lists import CLIENTS_COL_ANCHOR

    # Decisão do projeto: WhatsApp alinhado à esquerda
    assert (
        CLIENTS_COL_ANCHOR["WhatsApp"] == "w"
    ), "WhatsApp deve usar anchor='w' (esquerda)"


def test_create_clients_treeview_whatsapp_heading_uses_left_anchor() -> None:
    """Validar que heading de WhatsApp usa 'w' (esquerda)."""
    from src.ui.components.lists import create_clients_treeview

    source = inspect.getsource(create_clients_treeview)

    # Verificar que heading de WhatsApp usa "w"
    # Código deve ter: heading_anchor = "w" if key == "WhatsApp" else "center"
    lines = source.split("\n")
    heading_anchor_lines = [
        line for line in lines if "heading_anchor" in line
    ]

    assert (
        len(heading_anchor_lines) > 0
    ), "Deve ter linha que define heading_anchor"

    # Verificar que lógica usa "w" para WhatsApp
    heading_anchor_logic = "\n".join(heading_anchor_lines)
    assert (
        '"w"' in heading_anchor_logic or "'w'" in heading_anchor_logic
    ), "Deve usar 'w' no heading_anchor"


# =========================================================================
# GRUPO 5: INTEGRAÇÃO - VALIDAR view.py USA tree_heading_bg_active
# =========================================================================
def test_clientes_view_calls_reapply_with_heading_bg_active() -> None:
    """Validar que ClientesFrame passa heading_bg_active para reapply."""
    from src.modules.clientes.view import ClientesFrame

    source = inspect.getsource(ClientesFrame)

    # Procurar chamada de reapply_clientes_treeview_style
    assert (
        "reapply_clientes_treeview_style" in source
    ), "ClientesFrame deve chamar reapply_clientes_treeview_style"
    assert (
        "heading_bg_active" in source
    ), "ClientesFrame deve passar heading_bg_active"


def test_clientes_view_gets_heading_bg_active_from_palette() -> None:
    """Validar que ClientesFrame obtém heading_bg_active da paleta."""
    from src.modules.clientes.view import ClientesFrame

    source = inspect.getsource(ClientesFrame)

    # Deve obter tree_heading_bg_active da paleta
    assert (
        "tree_heading_bg_active" in source
    ), "Deve buscar tree_heading_bg_active na paleta"
    assert (
        'palette.get("tree_heading_bg_active"' in source
        or 'palette["tree_heading_bg_active"]' in source
    ), "Deve acessar tree_heading_bg_active via palette"


# =========================================================================
# GRUPO 6: CONSTANTES - VALIDAR VALORES ESPERADOS
# =========================================================================
def test_light_palette_tree_heading_bg_is_gray() -> None:
    """Validar que tree_heading_bg no tema claro é cinza (não branco)."""
    from src.modules.clientes.appearance import LIGHT_PALETTE

    # Converter para int para validar que não é branco puro
    bg = LIGHT_PALETTE["tree_heading_bg"]
    assert bg.startswith("#"), "Deve ser cor hex"

    # Branco puro seria #FFFFFF ou similar
    assert (
        bg.lower() != "#ffffff"
    ), "tree_heading_bg não deve ser branco puro"
    assert (
        bg.lower() != "#fff"
    ), "tree_heading_bg não deve ser branco puro"


def test_dark_palette_tree_heading_bg_is_dark_gray() -> None:
    """Validar que tree_heading_bg no tema escuro é cinza escuro (não preto)."""
    from src.modules.clientes.appearance import DARK_PALETTE

    # Converter para int para validar que não é preto puro
    bg = DARK_PALETTE["tree_heading_bg"]
    assert bg.startswith("#"), "Deve ser cor hex"

    # Preto puro seria #000000
    assert (
        bg.lower() != "#000000"
    ), "tree_heading_bg não deve ser preto puro"
    assert bg.lower() != "#000", "tree_heading_bg não deve ser preto puro"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
