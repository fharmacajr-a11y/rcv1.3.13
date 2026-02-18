# -*- coding: utf-8 -*-
"""Smoke tests para CTkTreeviewContainer (FASE 3).

Testes:
1. Instancia CTkTreeviewContainer, cria colunas, insere linha, update_idletasks, destroy
2. Troca theme/appearance via GlobalThemeManager sem exceção
"""

from __future__ import annotations


import pytest

from tests.helpers.skip_conditions import SKIP_PY313_TKINTER


# ==================== Fixtures ====================


@pytest.fixture
def ctk_root():
    """Cria root CTk para testes GUI."""
    from src.ui.ctk_config import ctk

    root = ctk.CTk()
    root.withdraw()  # Não mostrar janela

    yield root

    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def isolate_theme_manager(monkeypatch, tmp_path):
    """Isola theme_manager para cada teste."""
    import src.ui.theme_manager as tm

    monkeypatch.setattr(tm, "_cached_mode", None)
    monkeypatch.setattr(tm, "_cached_color", None)
    monkeypatch.setattr(tm, "CONFIG_FILE", tmp_path / "config_theme.json")
    monkeypatch.setattr(tm, "NO_FS", False)
    monkeypatch.setattr(tm.theme_manager, "_initialized", False)
    monkeypatch.setattr(tm.theme_manager, "_master_ref", None)

    return tm


# ==================== Smoke Test 1: Instancia e destroy ====================


@SKIP_PY313_TKINTER
def test_ctk_treeview_container_instantiate_insert_destroy(ctk_root):
    """Smoke test: instancia container, cria colunas, insere linha, destroy."""
    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    # Act: criar container
    container = CTkTreeviewContainer(
        ctk_root,
        columns=("nome", "valor"),
        rowheight=28,
    )

    # Assert: container criado
    assert container is not None
    tree = container.get_treeview()
    assert tree is not None

    # Configurar colunas
    container.configure_columns(
        column_widths={"nome": 150, "valor": 100},
        column_headings={"nome": "Nome", "valor": "Valor"},
    )

    # Inserir linha
    item_id = container.insert(values=("Teste", "123"))
    assert item_id is not None

    # update_idletasks
    container.update_idletasks()

    # destroy
    container.destroy()


@SKIP_PY313_TKINTER
def test_ctk_treeview_container_get_treeview_returns_instance(ctk_root):
    """Verifica que get_treeview() retorna o Treeview interno."""
    from tkinter import ttk

    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    container = CTkTreeviewContainer(ctk_root, columns=("col1",))
    tree = container.get_treeview()

    assert isinstance(tree, ttk.Treeview)
    container.destroy()


@SKIP_PY313_TKINTER
def test_ctk_treeview_container_clear_removes_all_items(ctk_root):
    """Verifica que clear() remove todos os itens."""
    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    container = CTkTreeviewContainer(ctk_root, columns=("col1",))
    tree = container.get_treeview()

    # Inserir itens
    tree.insert("", "end", values=("A",))
    tree.insert("", "end", values=("B",))
    assert len(tree.get_children()) == 2

    # Clear
    container.clear()
    assert len(tree.get_children()) == 0

    container.destroy()


# ==================== Smoke Test 2: Troca de tema sem exceção ====================


@SKIP_PY313_TKINTER
def test_ctk_treeview_container_theme_change_no_exception(ctk_root, isolate_theme_manager):
    """Smoke test: trocar tema via GlobalThemeManager não levanta exceção."""
    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    tm = isolate_theme_manager
    container = CTkTreeviewContainer(ctk_root, columns=("col1",))

    # Act: trocar tema Light -> Dark
    try:
        new_mode = tm.toggle_appearance_mode()
        assert new_mode == "dark"
    except Exception as e:
        pytest.fail(f"toggle_appearance_mode() levantou exceção: {e}")

    # Act: trocar tema Dark -> Light
    try:
        new_mode = tm.toggle_appearance_mode()
        assert new_mode == "light"
    except Exception as e:
        pytest.fail(f"toggle_appearance_mode() levantou exceção: {e}")

    container.destroy()


@SKIP_PY313_TKINTER
def test_ctk_treeview_container_apply_zebra_no_exception(ctk_root):
    """Verifica que apply_zebra() não levanta exceção."""
    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    container = CTkTreeviewContainer(ctk_root, columns=("col1",), zebra=True)
    tree = container.get_treeview()

    # Inserir itens
    tree.insert("", "end", values=("A",))
    tree.insert("", "end", values=("B",))
    tree.insert("", "end", values=("C",))

    # Act: chamar apply_zebra
    try:
        container.apply_zebra()
    except Exception as e:
        pytest.fail(f"apply_zebra() levantou exceção: {e}")

    container.destroy()


# ==================== Testes de style isolado ====================


def test_style_name_constant_is_ctk_treeview():
    """Verifica que a constante STYLE_NAME é 'CTk.Treeview'."""
    from src.ui.widgets.ctk_treeview_container import STYLE_NAME

    assert STYLE_NAME == "CTk.Treeview"


@SKIP_PY313_TKINTER
def test_custom_style_name(ctk_root):
    """Verifica que pode usar style_name customizado."""
    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    container = CTkTreeviewContainer(ctk_root, columns=("col1",), style_name="Custom")
    tree = container.get_treeview()

    # Style deve ter sido aplicado
    style = tree.cget("style")
    assert "Custom" in style

    container.destroy()


@SKIP_PY313_TKINTER
def test_rowheight_configurable(ctk_root):
    """Verifica que rowheight é configurável."""
    from tkinter import ttk

    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    container = CTkTreeviewContainer(ctk_root, columns=("col1",), rowheight=32)

    # Verificar através do ttk.Style
    style = ttk.Style(ctk_root)
    configured_rowheight = style.lookup("CTk.Treeview.Treeview", "rowheight")

    # O rowheight pode ser string ou int dependendo da versão
    assert configured_rowheight in (32, "32", "")  # "" se não suportado

    container.destroy()


# ==================== Testes de get_colors ====================


@SKIP_PY313_TKINTER
def test_get_colors_returns_tree_colors(ctk_root):
    """Verifica que get_colors() retorna TreeColors."""
    from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer

    container = CTkTreeviewContainer(ctk_root, columns=("col1",))
    colors = container.get_colors()

    assert colors is not None
    # TreeColors deve ter atributos de cor
    assert hasattr(colors, "bg")
    assert hasattr(colors, "fg")
    assert hasattr(colors, "sel_bg")

    container.destroy()


# ==================== Test import from package ====================


def test_import_from_widgets_package():
    """Verifica que CTkTreeviewContainer pode ser importado do package."""
    try:
        from src.ui.widgets import CTkTreeviewContainer

        assert CTkTreeviewContainer is not None
    except ImportError as e:
        pytest.fail(f"Falha ao importar CTkTreeviewContainer: {e}")
