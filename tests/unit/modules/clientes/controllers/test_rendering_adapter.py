"""Testes unitários para rendering_adapter.

Este módulo testa o adapter de renderização que converte ClienteRow em valores
para Treeview, sem depender de Tkinter real.

Cobertura esperada: >= 80% do arquivo rendering_adapter.py
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.modules.clientes.controllers.rendering_adapter import (
    RowRenderingContext,
    build_rendering_context_from_ui,
    build_row_tags,
    build_row_values,
)
from src.modules.clientes.viewmodel import ClienteRow


@pytest.fixture
def sample_cliente_row() -> ClienteRow:
    """Cria um ClienteRow completo com dados de exemplo."""
    return ClienteRow(
        id="123",
        razao_social="Empresa Teste LTDA",
        cnpj="12.345.678/0001-90",
        nome="João Silva",
        whatsapp="(11) 98765-4321",
        observacoes="Cliente VIP",
        status="Ativo",
        ultima_alteracao="2025-12-09 10:30:00",
        search_norm="empresa teste ltda joao silva",
    )


@pytest.fixture
def empty_cliente_row() -> ClienteRow:
    """Cria um ClienteRow com campos vazios."""
    return ClienteRow(
        id="",
        razao_social="",
        cnpj="",
        nome="",
        whatsapp="",
        observacoes="",
        status="",
        ultima_alteracao="",
    )


@pytest.fixture
def basic_rendering_context() -> RowRenderingContext:
    """Cria um contexto de renderização básico com todas colunas visíveis."""
    return RowRenderingContext(
        column_order=["ID", "Razao Social", "CNPJ", "Nome", "WhatsApp", "Status"],
        visible_columns={
            "ID": True,
            "Razao Social": True,
            "CNPJ": True,
            "Nome": True,
            "WhatsApp": True,
            "Status": True,
        },
    )


class TestRowRenderingContext:
    """Testes da estrutura de dados RowRenderingContext."""

    def test_context_criado_com_valores_corretos(self) -> None:
        """RowRenderingContext deve armazenar ordem e visibilidade das colunas."""
        ctx = RowRenderingContext(
            column_order=["ID", "Nome"],
            visible_columns={"ID": True, "Nome": False},
        )

        assert ctx.column_order == ["ID", "Nome"]
        assert ctx.visible_columns == {"ID": True, "Nome": False}


class TestBuildRowValues:
    """Testes da função build_row_values()."""

    def test_build_row_values_com_todas_colunas_visiveis(
        self, sample_cliente_row: ClienteRow, basic_rendering_context: RowRenderingContext
    ) -> None:
        """Deve retornar todos os valores quando todas colunas estão visíveis."""
        values = build_row_values(sample_cliente_row, basic_rendering_context)

        assert values == (
            "123",
            "Empresa Teste LTDA",
            "12.345.678/0001-90",
            "João Silva",
            "(11) 98765-4321",
            "Ativo",
        )

    def test_build_row_values_mascara_colunas_invisiveis(self, sample_cliente_row: ClienteRow) -> None:
        """Colunas invisíveis devem retornar string vazia."""
        ctx = RowRenderingContext(
            column_order=["ID", "Razao Social", "CNPJ", "Nome"],
            visible_columns={
                "ID": True,
                "Razao Social": False,  # Invisível
                "CNPJ": True,
                "Nome": False,  # Invisível
            },
        )

        values = build_row_values(sample_cliente_row, ctx)

        assert values == ("123", "", "12.345.678/0001-90", "")

    def test_build_row_values_com_ordem_customizada(self, sample_cliente_row: ClienteRow) -> None:
        """Valores devem seguir a ordem especificada em column_order."""
        ctx = RowRenderingContext(
            column_order=["Nome", "ID", "Status"],  # Ordem diferente
            visible_columns={
                "Nome": True,
                "ID": True,
                "Status": True,
            },
        )

        values = build_row_values(sample_cliente_row, ctx)

        assert values == ("João Silva", "123", "Ativo")

    def test_build_row_values_com_coluna_inexistente(self, sample_cliente_row: ClienteRow) -> None:
        """Coluna que não existe no mapping deve retornar string vazia."""
        ctx = RowRenderingContext(
            column_order=["ID", "Coluna Inexistente", "Nome"],
            visible_columns={
                "ID": True,
                "Coluna Inexistente": True,
                "Nome": True,
            },
        )

        values = build_row_values(sample_cliente_row, ctx)

        assert values == ("123", "", "João Silva")

    def test_build_row_values_com_todas_colunas_invisiveis(self, sample_cliente_row: ClienteRow) -> None:
        """Todas colunas invisíveis devem retornar tupla de strings vazias."""
        ctx = RowRenderingContext(
            column_order=["ID", "Nome", "Status"],
            visible_columns={
                "ID": False,
                "Nome": False,
                "Status": False,
            },
        )

        values = build_row_values(sample_cliente_row, ctx)

        assert values == ("", "", "")

    def test_build_row_values_com_cliente_vazio(
        self, empty_cliente_row: ClienteRow, basic_rendering_context: RowRenderingContext
    ) -> None:
        """Cliente com campos vazios deve retornar tupla de strings vazias."""
        values = build_row_values(empty_cliente_row, basic_rendering_context)

        assert all(v == "" for v in values)

    def test_build_row_values_visibilidade_default_true(self, sample_cliente_row: ClienteRow) -> None:
        """Colunas sem entrada em visible_columns devem ser tratadas como visíveis."""
        ctx = RowRenderingContext(
            column_order=["ID", "Nome"],
            visible_columns={},  # Vazio, todas devem ser visíveis por padrão
        )

        values = build_row_values(sample_cliente_row, ctx)

        assert values == ("123", "João Silva")

    def test_build_row_values_todas_colunas_disponiveis(self, sample_cliente_row: ClienteRow) -> None:
        """Teste com todas as colunas disponíveis no mapping."""
        ctx = RowRenderingContext(
            column_order=[
                "ID",
                "Razao Social",
                "CNPJ",
                "Nome",
                "WhatsApp",
                "Observacoes",
                "Status",
                "Ultima Alteracao",
            ],
            visible_columns={
                col: True
                for col in [
                    "ID",
                    "Razao Social",
                    "CNPJ",
                    "Nome",
                    "WhatsApp",
                    "Observacoes",
                    "Status",
                    "Ultima Alteracao",
                ]
            },
        )

        values = build_row_values(sample_cliente_row, ctx)

        assert values == (
            "123",
            "Empresa Teste LTDA",
            "12.345.678/0001-90",
            "João Silva",
            "(11) 98765-4321",
            "Cliente VIP",
            "Ativo",
            "2025-12-09 10:30:00",
        )


class TestBuildRowTags:
    """Testes da função build_row_tags()."""

    def test_build_row_tags_com_observacoes(self, sample_cliente_row: ClienteRow) -> None:
        """Cliente com observações deve ter tag 'has_obs'."""
        tags = build_row_tags(sample_cliente_row)

        assert tags == ("has_obs",)

    def test_build_row_tags_sem_observacoes(self, empty_cliente_row: ClienteRow) -> None:
        """Cliente sem observações não deve ter tags."""
        tags = build_row_tags(empty_cliente_row)

        assert tags == ()

    def test_build_row_tags_observacoes_apenas_espacos(self) -> None:
        """Observações com apenas espaços não devem gerar tag."""
        row = ClienteRow(
            id="1",
            razao_social="Empresa",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="   ",  # Apenas espaços
            status="",
            ultima_alteracao="",
        )

        tags = build_row_tags(row)

        assert tags == ()

    def test_build_row_tags_observacoes_tabs_e_newlines(self) -> None:
        """Observações com apenas tabs/newlines não devem gerar tag."""
        row = ClienteRow(
            id="1",
            razao_social="Empresa",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="\t\n  ",  # Whitespace variado
            status="",
            ultima_alteracao="",
        )

        tags = build_row_tags(row)

        assert tags == ()

    def test_build_row_tags_observacoes_com_espacos_nas_pontas(self) -> None:
        """Observações com espaços nas pontas mas conteúdo devem gerar tag."""
        row = ClienteRow(
            id="1",
            razao_social="Empresa",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="  Conteúdo importante  ",
            status="",
            ultima_alteracao="",
        )

        tags = build_row_tags(row)

        assert tags == ("has_obs",)


class TestBuildRenderingContextFromUI:
    """Testes da função build_rendering_context_from_ui()."""

    def test_build_context_from_ui_vars(self) -> None:
        """Deve construir contexto a partir de variáveis da UI."""
        # Mock de tk.BooleanVar
        var_id = Mock()
        var_id.get.return_value = True

        var_nome = Mock()
        var_nome.get.return_value = False

        var_status = Mock()
        var_status.get.return_value = True

        ctx = build_rendering_context_from_ui(
            column_order=["ID", "Nome", "Status"],
            visible_vars={"ID": var_id, "Nome": var_nome, "Status": var_status},
        )

        assert ctx.column_order == ["ID", "Nome", "Status"]
        assert ctx.visible_columns == {"ID": True, "Nome": False, "Status": True}

    def test_build_context_from_ui_todas_visiveis(self) -> None:
        """Todas variáveis retornando True."""
        vars_dict = {}
        for col in ["ID", "Razao Social", "CNPJ"]:
            var = Mock()
            var.get.return_value = True
            vars_dict[col] = var

        ctx = build_rendering_context_from_ui(
            column_order=["ID", "Razao Social", "CNPJ"],
            visible_vars=vars_dict,
        )

        assert all(ctx.visible_columns.values())

    def test_build_context_from_ui_todas_invisiveis(self) -> None:
        """Todas variáveis retornando False."""
        vars_dict = {}
        for col in ["ID", "Razao Social", "CNPJ"]:
            var = Mock()
            var.get.return_value = False
            vars_dict[col] = var

        ctx = build_rendering_context_from_ui(
            column_order=["ID", "Razao Social", "CNPJ"],
            visible_vars=vars_dict,
        )

        assert not any(ctx.visible_columns.values())

    def test_build_context_from_ui_converte_para_bool(self) -> None:
        """Deve converter valores truthy/falsy para bool."""
        var_truthy = Mock()
        var_truthy.get.return_value = 1  # Truthy

        var_falsy = Mock()
        var_falsy.get.return_value = 0  # Falsy

        ctx = build_rendering_context_from_ui(
            column_order=["Col1", "Col2"],
            visible_vars={"Col1": var_truthy, "Col2": var_falsy},
        )

        assert ctx.visible_columns["Col1"] is True
        assert ctx.visible_columns["Col2"] is False


class TestIntegration:
    """Testes de integração entre funções do módulo."""

    def test_fluxo_completo_renderizacao(self, sample_cliente_row: ClienteRow) -> None:
        """Testa fluxo completo: criar contexto da UI → renderizar valores e tags."""
        # 1. Simular variáveis da UI
        vars_dict = {}
        for col in ["ID", "Nome", "Status"]:
            var = Mock()
            var.get.return_value = True
            vars_dict[col] = var

        # 2. Construir contexto
        ctx = build_rendering_context_from_ui(
            column_order=["ID", "Nome", "Status"],
            visible_vars=vars_dict,
        )

        # 3. Renderizar valores
        values = build_row_values(sample_cliente_row, ctx)
        assert values == ("123", "João Silva", "Ativo")

        # 4. Renderizar tags
        tags = build_row_tags(sample_cliente_row)
        assert tags == ("has_obs",)

    def test_fluxo_com_colunas_ocultas_e_sem_tags(self, empty_cliente_row: ClienteRow) -> None:
        """Testa com algumas colunas ocultas e cliente sem tags."""
        vars_dict = {
            "ID": Mock(get=Mock(return_value=True)),
            "Nome": Mock(get=Mock(return_value=False)),  # Oculto
            "Status": Mock(get=Mock(return_value=True)),
        }

        ctx = build_rendering_context_from_ui(
            column_order=["ID", "Nome", "Status"],
            visible_vars=vars_dict,
        )

        values = build_row_values(empty_cliente_row, ctx)
        assert values == ("", "", "")  # Nome mascarado

        tags = build_row_tags(empty_cliente_row)
        assert tags == ()


class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_contexto_com_ordem_vazia(self, sample_cliente_row: ClienteRow) -> None:
        """Contexto com ordem vazia deve retornar tupla vazia."""
        ctx = RowRenderingContext(column_order=[], visible_columns={})

        values = build_row_values(sample_cliente_row, ctx)

        assert values == ()

    def test_cliente_com_observacoes_unicode(self) -> None:
        """Observações com caracteres unicode devem funcionar."""
        row = ClienteRow(
            id="1",
            razao_social="Empresa",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="🎉 Cliente especial 中文",
            status="",
            ultima_alteracao="",
        )

        tags = build_row_tags(row)

        assert tags == ("has_obs",)

    def test_valores_com_quebras_de_linha(self) -> None:
        """Valores com quebras de linha devem ser preservados."""
        row = ClienteRow(
            id="1",
            razao_social="Empresa\nMulti Linha",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="",
            status="",
            ultima_alteracao="",
        )

        ctx = RowRenderingContext(
            column_order=["Razao Social"],
            visible_columns={"Razao Social": True},
        )

        values = build_row_values(row, ctx)

        assert values == ("Empresa\nMulti Linha",)
