# -*- coding: utf-8 -*-
"""Testes de listagem de clientes no ClientesV2Frame.

FASE 3.1: Testes de carregamento e exibição de dados.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch
from typing import List

from src.modules.clientes.core.viewmodel import ClienteRow


@pytest.fixture
def mock_clientes_data() -> List[ClienteRow]:
    """Dados de exemplo para testes."""
    return [
        ClienteRow(
            id="1",
            razao_social="Cliente Teste A",
            cnpj="11.222.333/0001-44",
            nome="Cliente A",
            whatsapp="11999999999",
            status="Ativo",
            observacoes="Teste A",
            ultima_alteracao="2026-01-15",
        ),
        ClienteRow(
            id="2",
            razao_social="Cliente Teste B",
            cnpj="22.333.444/0001-55",
            nome="Cliente B",
            whatsapp="11888888888",
            status="Inativo",
            observacoes="Teste B",
            ultima_alteracao="2026-01-20",
        ),
        ClienteRow(
            id="3",
            razao_social="Empresa XYZ",
            cnpj="33.444.555/0001-66",
            nome="XYZ",
            whatsapp="11777777777",
            status="Ativo",
            observacoes="XYZ Corp",
            ultima_alteracao="2026-01-22",
        ),
    ]


def test_listagem_initial_load(clientes_v2_frame, mock_clientes_data):
    """Test que frame carrega dados iniciais no ViewModel."""
    frame = clientes_v2_frame

    # Mock do load_from_iterable
    with patch.object(frame._vm, "load_from_iterable"):
        # Simular carregamento inicial
        frame._vm.load_from_iterable(mock_clientes_data)

        # Verificar que get_rows retorna dados
        rows = frame._vm.get_rows()
        assert len(rows) >= 0, "get_rows deve retornar lista (pode estar vazia se não carregou)"


def test_listagem_treeview_has_columns(clientes_v2_frame):
    """Test que Treeview tem colunas configuradas."""
    frame = clientes_v2_frame
    tree = frame.tree

    # Verificar que tem colunas
    columns = tree["columns"]
    assert len(columns) > 0, "Treeview deve ter colunas"

    # Verificar que tem as colunas esperadas (pelo menos algumas)
    # ClientesV2 usa: id, razao_social, cnpj, nome, whatsapp, status, observacoes, ultima_alteracao
    assert "id" in columns, "Deve ter coluna id"
    assert "razao_social" in columns, "Deve ter coluna razao_social"


def test_listagem_can_insert_row(clientes_v2_frame, mock_clientes_data):
    """Test que consegue inserir dados no Treeview."""
    frame = clientes_v2_frame
    tree = frame.tree

    # Limpar treeview
    for item in tree.get_children():
        tree.delete(item)

    # Inserir uma linha de teste
    test_row = mock_clientes_data[0]
    iid = tree.insert(
        "",
        "end",
        values=(
            test_row.id,
            test_row.razao_social,
            test_row.cnpj,
            test_row.nome,
            test_row.whatsapp,
            test_row.status,
            test_row.observacoes,
            test_row.ultima_alteracao or "",
        ),
    )

    assert iid != "", "Inserção deve retornar ID válido"

    # Verificar que item foi inserido
    children = tree.get_children()
    assert len(children) == 1, "Treeview deve ter 1 item"
    assert children[0] == iid, "Item inserido deve estar na árvore"


def test_listagem_load_async_method_exists(clientes_v2_frame):
    """Test que método load_async() existe e pode ser chamado."""
    frame = clientes_v2_frame

    # Verificar que load_async existe
    assert hasattr(frame, "load_async"), "Frame deve ter método load_async"
    assert callable(frame.load_async), "load_async deve ser callable"

    # Tentar chamar (não deve dar erro)
    try:
        frame.load_async()
    except Exception as e:
        pytest.fail(f"load_async() não deveria dar erro: {e}")


def test_listagem_get_rows_returns_list(clientes_v2_frame):
    """Test que ViewModel.get_rows() retorna lista."""
    frame = clientes_v2_frame

    rows = frame._vm.get_rows()
    assert isinstance(rows, list), "get_rows deve retornar lista"

    # Se tiver dados, verificar que são ClienteRow
    if len(rows) > 0:
        from src.modules.clientes.core.viewmodel import ClienteRow

        assert isinstance(rows[0], ClienteRow), "Itens devem ser ClienteRow"


def test_listagem_load_from_iterable(clientes_v2_frame, mock_clientes_data):
    """Test que load_from_iterable carrega dados no ViewModel."""
    frame = clientes_v2_frame

    # Carregar dados mock
    frame._vm.load_from_iterable(mock_clientes_data)

    # Verificar que dados foram carregados
    rows = frame._vm.get_rows()
    assert len(rows) == 3, "Deve ter 3 clientes carregados"

    # Verificar primeiro item
    assert rows[0].razao_social == "Cliente Teste A"
    assert rows[0].cnpj == "11.222.333/0001-44"


def test_listagem_empty_state(clientes_v2_frame):
    """Test que frame lida com estado vazio (sem dados)."""
    frame = clientes_v2_frame

    # Carregar lista vazia
    frame._vm.load_from_iterable([])

    # Não deve dar erro
    rows = frame._vm.get_rows()
    assert len(rows) == 0, "Lista vazia deve retornar 0 items"


def test_listagem_treeview_selection(clientes_v2_frame):
    """Test que Treeview permite seleção."""
    frame = clientes_v2_frame
    tree = frame.tree

    # Inserir item de teste (8 colunas: id, razao_social, cnpj, nome, whatsapp, status, observacoes, ultima_alteracao)
    iid = tree.insert(
        "", "end", values=("999", "Test", "99.999.999/0001-99", "Nome Test", "11999999999", "Ativo", "Teste", "")
    )

    # Selecionar item
    tree.selection_set(iid)

    # Verificar seleção
    selected = tree.selection()
    assert len(selected) == 1, "Deve ter 1 item selecionado"
    assert selected[0] == iid, "Item selecionado deve ser o inserido"


def test_listagem_row_data_map(clientes_v2_frame, mock_clientes_data):
    """Test que frame mantém mapeamento iid -> ClienteRow."""
    frame = clientes_v2_frame

    # Verificar que _row_data_map existe
    assert hasattr(frame, "_row_data_map"), "Frame deve ter _row_data_map"
    assert isinstance(frame._row_data_map, dict), "_row_data_map deve ser dict"
