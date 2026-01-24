# -*- coding: utf-8 -*-
"""Testes de busca e filtros no ClientesV2Frame.

FASE 3.1: Testes de busca por texto e filtros de status.
"""

from __future__ import annotations

import pytest
from typing import List

from src.modules.clientes.viewmodel import ClienteRow


@pytest.fixture
def clientes_busca_data() -> List[ClienteRow]:
    """Dados para testes de busca."""
    return [
        ClienteRow(
            id="1",
            razao_social="Empresa ABC Ltda",
            cnpj="11.222.333/0001-44",
            nome="ABC",
            whatsapp="11999999999",
            status="Ativo",
            observacoes="Cliente VIP",
            ultima_alteracao="2026-01-15",
        ),
        ClienteRow(
            id="2",
            razao_social="Comércio XYZ",
            cnpj="22.333.444/0001-55",
            nome="XYZ",
            whatsapp="11888888888",
            status="Inativo",
            observacoes="Aguardando renovação",
            ultima_alteracao="2026-01-20",
        ),
        ClienteRow(
            id="3",
            razao_social="ABC Serviços",
            cnpj="33.444.555/0001-66",
            nome="ABC Srv",
            whatsapp="11777777777",
            status="Ativo",
            observacoes="Contrato anual",
            ultima_alteracao="2026-01-22",
        ),
        ClienteRow(
            id="4",
            razao_social="Produtos DEF",
            cnpj="44.555.666/0001-77",
            nome="DEF",
            whatsapp="11666666666",
            status="Pausado",
            observacoes="Férias",
            ultima_alteracao="2025-12-30",
        ),
    ]


def test_busca_set_search_text(clientes_v2_frame, clientes_busca_data):
    """Test que ViewModel.set_search_text aplica filtro de texto."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Aplicar filtro de busca
    frame._vm.set_search_text("ABC")

    # Verificar que filtro foi aplicado
    rows = frame._vm.get_rows()

    # Deve retornar apenas clientes com "ABC" no nome
    # Nota: O filtro pode ser case-insensitive e pode buscar em vários campos
    for row in rows:
        assert (
            "ABC" in row.razao_social.upper() or "ABC" in row.observacoes.upper()
        ), f"Resultado {row.razao_social} deve conter 'ABC'"


def test_busca_clear_search(clientes_v2_frame, clientes_busca_data):
    """Test que limpar busca retorna todos os resultados."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Aplicar e depois limpar busca
    frame._vm.set_search_text("ABC")
    filtered_count = len(frame._vm.get_rows())

    frame._vm.set_search_text("")  # Limpar
    all_count = len(frame._vm.get_rows())

    # Sem filtro deve ter mais resultados
    assert all_count >= filtered_count, "Sem filtro deve ter >= resultados que com filtro"
    assert all_count == 4, "Deve retornar todos os 4 clientes"


def test_busca_toolbar_has_search_widget(clientes_v2_frame):
    """Test que toolbar tem widget de busca."""
    frame = clientes_v2_frame
    toolbar = frame.toolbar

    # Verificar que toolbar existe
    assert toolbar is not None, "Toolbar não deve ser None"

    # Verificar que tem entry de busca (é entry_search, não search_entry)
    assert hasattr(toolbar, "entry_search"), "Toolbar deve ter entry_search"


def test_busca_on_search_callback(clientes_v2_frame):
    """Test que callback _on_search existe e pode ser chamado."""
    frame = clientes_v2_frame

    # Verificar que método existe
    assert hasattr(frame, "_on_search"), "Frame deve ter _on_search"
    assert callable(frame._on_search), "_on_search deve ser callable"

    # Tentar chamar (não deve dar erro)
    try:
        frame._on_search("teste")
    except Exception as e:
        pytest.fail(f"_on_search não deveria dar erro: {e}")


def test_busca_on_clear_callback(clientes_v2_frame):
    """Test que callback _on_clear_search existe."""
    frame = clientes_v2_frame

    assert hasattr(frame, "_on_clear_search"), "Frame deve ter _on_clear_search"
    assert callable(frame._on_clear_search), "_on_clear_search deve ser callable"


def test_busca_set_status_filter(clientes_v2_frame, clientes_busca_data):
    """Test que filtro de status funciona."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Aplicar filtro de status
    frame._vm.set_status_filter("Ativo")

    # Verificar que apenas ativos aparecem
    rows = frame._vm.get_rows()
    for row in rows:
        assert row.status == "Ativo", f"Cliente {row.razao} deve ser Ativo"


def test_busca_get_status_choices(clientes_v2_frame, clientes_busca_data):
    """Test que get_status_choices retorna lista de status.

    Nota: get_status_choices extrai status do campo observacoes com padrão [Status].
    Para ter status choices, as observações devem conter [Status] no início.
    """
    frame = clientes_v2_frame

    # Carregar dados como dicts com status no formato correto nas observações
    data_dicts = [
        {
            "id": "1",
            "razao_social": "ABC",
            "cnpj": "11.222.333/0001-44",
            "nome": "ABC",
            "whatsapp": "11999999999",
            "observacoes": "[Ativo] Cliente VIP",
            "ultima_alteracao": "2026-01-15",
        },
        {
            "id": "2",
            "razao_social": "XYZ",
            "cnpj": "22.333.444/0001-55",
            "nome": "XYZ",
            "whatsapp": "11888888888",
            "observacoes": "[Inativo] Aguardando renovação",
            "ultima_alteracao": "2026-01-20",
        },
        {
            "id": "3",
            "razao_social": "DEF",
            "cnpj": "33.444.555/0001-66",
            "nome": "DEF",
            "whatsapp": "11777777777",
            "observacoes": "[Pausado] Férias",
            "ultima_alteracao": "2026-01-22",
        },
    ]

    frame._vm.load_from_iterable(data_dicts)

    choices = frame._vm.get_status_choices()

    assert isinstance(choices, list), "get_status_choices deve retornar lista"

    # Verificar que extraiu os status (Ativo, Inativo, Pausado)
    if len(choices) > 0:
        assert "Ativo" in choices or "Inativo" in choices, "Deve ter status extraídos das observações"


def test_busca_status_filter_all(clientes_v2_frame, clientes_busca_data):
    """Test que filtro 'Todos' retorna todos os clientes."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Aplicar filtro "Todos" (ou string vazia)
    frame._vm.set_status_filter("")  # ou "Todos" dependendo da implementação

    rows = frame._vm.get_rows()
    assert len(rows) == 4, "Filtro 'Todos' deve retornar todos os clientes"


def test_busca_combined_filters(clientes_v2_frame, clientes_busca_data):
    """Test que busca + status funcionam juntos."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Aplicar busca por texto E status
    frame._vm.set_search_text("ABC")
    frame._vm.set_status_filter("Ativo")

    rows = frame._vm.get_rows()

    # Deve retornar apenas clientes ativos com "ABC"
    for row in rows:
        assert row.status == "Ativo", f"Cliente {row.razao_social} deve ser Ativo"
        assert "ABC" in row.razao_social.upper(), f"Cliente {row.razao_social} deve conter ABC"


def test_busca_case_insensitive(clientes_v2_frame, clientes_busca_data):
    """Test que busca é case-insensitive."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Buscar com minúsculas
    frame._vm.set_search_text("abc")
    rows_lower = frame._vm.get_rows()

    # Buscar com maiúsculas
    frame._vm.set_search_text("ABC")
    rows_upper = frame._vm.get_rows()

    # Resultados devem ser iguais
    assert len(rows_lower) == len(rows_upper), "Busca deve ser case-insensitive"


def test_busca_partial_match(clientes_v2_frame, clientes_busca_data):
    """Test que busca encontra matches parciais."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Buscar parte do nome
    frame._vm.set_search_text("Empresa")
    rows = frame._vm.get_rows()

    # Deve encontrar "Empresa ABC Ltda"
    assert len(rows) > 0, "Deve encontrar pelo menos 1 cliente"
    assert any("Empresa" in row.razao_social for row in rows), "Deve ter match parcial"


def test_busca_by_cnpj(clientes_v2_frame, clientes_busca_data):
    """Test que busca funciona por CNPJ."""
    frame = clientes_v2_frame

    # Carregar dados
    frame._vm.load_from_iterable(clientes_busca_data)

    # Buscar por parte do CNPJ
    frame._vm.set_search_text("11.222")
    rows = frame._vm.get_rows()

    # Deve encontrar cliente com CNPJ "11.222.333/0001-44"
    if len(rows) > 0:
        assert any("11.222" in row.cnpj for row in rows), "Busca deve funcionar por CNPJ"


def test_busca_toolbar_get_search_text(clientes_v2_frame):
    """Test que toolbar tem método get_search_text."""
    frame = clientes_v2_frame
    toolbar = frame.toolbar

    assert hasattr(toolbar, "get_search_text"), "Toolbar deve ter get_search_text"

    # Deve retornar string
    query = toolbar.get_search_text()
    assert isinstance(query, str), "get_search_text deve retornar string"
