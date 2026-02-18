# -*- coding: utf-8 -*-
"""Smoke test para ClientFilesDialog - FASE 4: Migração para CTkTreeviewContainer.

Valida que o diálogo migrado funciona corretamente:
1. Pode ser instanciado
2. Usa CTkTreeviewContainer
3. Treeview aceita inserção de item
4. update_idletasks + destroy funcionam sem erro
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.helpers.skip_conditions import SKIP_PY313_TKINTER


@pytest.fixture
def mock_storage():
    """Mock do SupabaseStorageAdapter para evitar chamadas reais."""
    with patch("src.modules.clientes.ui.views.client_files_dialog.SupabaseStorageAdapter") as mock:
        adapter_instance = MagicMock()
        adapter_instance.list_files.return_value = []
        mock.return_value = adapter_instance
        yield adapter_instance


@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase."""
    with patch("src.modules.clientes.ui.views.client_files_dialog._resolve_supabase_client") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_helpers():
    """Mock dos helpers de uploads."""
    with patch("src.modules.clientes.ui.views.client_files_dialog.get_clients_bucket") as bucket_mock:
        with patch("src.modules.clientes.ui.views.client_files_dialog.client_prefix_for_id") as prefix_mock:
            with patch("src.modules.clientes.ui.views.client_files_dialog.get_current_org_id") as org_mock:
                bucket_mock.return_value = "test-bucket"
                prefix_mock.return_value = "clients/123/"
                org_mock.return_value = "org-123"
                yield


@pytest.fixture
def ctk_root():
    """Cria root CTk para testes GUI."""
    from src.ui.ctk_config import ctk

    root = ctk.CTk()
    root.withdraw()

    yield root

    try:
        root.destroy()
    except Exception:
        pass


# ==================== Smoke Tests ====================


def test_client_files_dialog_import():
    """Verifica que ClientFilesDialog pode ser importado."""
    from src.modules.clientes.ui.views.client_files_dialog import ClientFilesDialog

    assert ClientFilesDialog is not None


def test_client_files_dialog_uses_ctk_treeview_container():
    """Verifica que o módulo importa CTkTreeviewContainer."""
    import src.modules.clientes.ui.views.client_files_dialog as mod

    # Verificar que CTkTreeviewContainer está importado
    assert hasattr(mod, "CTkTreeviewContainer"), "CTkTreeviewContainer não encontrado no módulo"


@SKIP_PY313_TKINTER
def test_client_files_dialog_instantiate_insert_destroy(ctk_root, mock_storage, mock_supabase_client, mock_helpers):
    """Smoke test: instancia diálogo, insere item no tree, destroy."""
    from src.modules.clientes.ui.views.client_files_dialog import ClientFilesDialog

    # Criar diálogo
    dialog = ClientFilesDialog(
        parent=ctk_root,
        client_id=123,
        client_name="Teste Cliente",
    )

    # Verificar que _tree_container existe (CTkTreeviewContainer)
    assert hasattr(dialog, "_tree_container"), "_tree_container não encontrado"
    assert dialog._tree_container is not None, "_tree_container é None"

    # Verificar que tree é o Treeview interno
    assert dialog.tree is not None, "tree é None"
    assert dialog.tree == dialog._tree_container.get_treeview(), "tree não é o Treeview do container"

    # Inserir item de teste no Treeview
    item_id = dialog.tree.insert("", "end", text="test_file.pdf", values=("PDF",))
    assert item_id is not None, "Falha ao inserir item"

    # Verificar que o item foi inserido
    children = dialog.tree.get_children()
    assert len(children) >= 1, "Item não foi inserido no tree"

    # update_idletasks
    dialog.update_idletasks()

    # destroy
    dialog.destroy()


@SKIP_PY313_TKINTER
def test_client_files_dialog_tree_colors(ctk_root, mock_storage, mock_supabase_client, mock_helpers):
    """Verifica que _tree_colors é obtido corretamente do container."""
    from src.modules.clientes.ui.views.client_files_dialog import ClientFilesDialog

    dialog = ClientFilesDialog(
        parent=ctk_root,
        client_id=123,
        client_name="Teste Cliente",
    )

    # Verificar que _tree_colors existe
    assert hasattr(dialog, "_tree_colors"), "_tree_colors não encontrado"

    # Cores devem vir do CTkTreeviewContainer
    container_colors = dialog._tree_container.get_colors()
    assert dialog._tree_colors == container_colors, "Cores não coincidem com o container"

    dialog.destroy()


@SKIP_PY313_TKINTER
def test_client_files_dialog_no_ttkbootstrap(ctk_root, mock_storage, mock_supabase_client, mock_helpers):
    """Verifica que o diálogo funciona sem ttkbootstrap."""
    import sys

    # Garantir que ttkbootstrap não está carregado pelo módulo
    modules_before = set(sys.modules.keys())

    from src.modules.clientes.ui.views.client_files_dialog import ClientFilesDialog

    dialog = ClientFilesDialog(
        parent=ctk_root,
        client_id=123,
        client_name="Teste Cliente",
    )

    # Verificar que ttkbootstrap não foi importado
    modules_after = set(sys.modules.keys())
    new_modules = modules_after - modules_before
    ttkbootstrap_modules = [m for m in new_modules if "ttkbootstrap" in m.lower()]
    assert len(ttkbootstrap_modules) == 0, f"ttkbootstrap foi importado: {ttkbootstrap_modules}"

    dialog.destroy()
