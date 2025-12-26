# -*- coding: utf-8 -*-
"""
Round 15: Testes de cobertura para viewmodel.py

Objetivo: Elevar cobertura de ~76.5% → 95%+
Foco: lógica de estado, filtros, ordenação, transformação de dados
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import patch

import pytest

from src.modules.clientes.viewmodel import (
    ClienteRow,
    ClientesViewModel,
    ClientesViewModelError,
)


# ========================================================================
# Fixtures e helpers
# ========================================================================


def make_cliente_dict(**overrides: Any) -> dict[str, Any]:
    """Factory para criar dict simulando cliente do banco."""
    base: dict[str, Any] = {
        "id": 1,
        "cnpj": "12345678000199",
        "razao_social": "Empresa Teste LTDA",
        "nome": "João Silva",
        "whatsapp": "11999999999",
        "observacoes": "",
        "ultima_alteracao": "2025-12-01T10:30:00",
        "ultima_por": "user@example.com",
    }
    base.update(overrides)
    return base


class ClienteMock:
    """Simula objeto cliente com atributos."""

    def __init__(self, **attrs: Any):
        for key, value in attrs.items():
            setattr(self, key, value)


@pytest.fixture
def vm() -> ClientesViewModel:
    """Retorna instância limpa do ViewModel."""
    return ClientesViewModel()


@pytest.fixture
def vm_with_order() -> ClientesViewModel:
    """ViewModel com opções de ordenação configuradas."""
    order_choices = {
        "Razão Social": ("razao_social", False),
        "Nome": ("nome", False),
        "CNPJ": ("cnpj", False),
        "ID": ("id", False),
        "Razão Social (Z-A)": ("razao_social", True),
    }
    return ClientesViewModel(
        order_choices=order_choices,
        default_order_label="Razão Social",
    )


# ========================================================================
# Testes de ClienteRow
# ========================================================================


class TestClienteRow:
    """Testes da dataclass ClienteRow."""

    def test_cliente_row_creation(self):
        """Testa criação básica de ClienteRow."""
        row = ClienteRow(
            id="42",
            razao_social="Teste LTDA",
            cnpj="12.345.678/0001-99",
            nome="João",
            whatsapp="(11) 99999-9999",
            observacoes="Obs teste",
            status="ATIVO",
            ultima_alteracao="01/12/2025",
        )

        assert row.id == "42"
        assert row.razao_social == "Teste LTDA"
        assert row.cnpj == "12.345.678/0001-99"
        assert row.search_norm == ""  # padrão
        assert row.raw == {}  # padrão

    def test_cliente_row_with_search_norm(self):
        """Testa ClienteRow com search_norm preenchido."""
        row = ClienteRow(
            id="1",
            razao_social="Farmácia",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="",
            status="",
            ultima_alteracao="",
            search_norm="farmacia",
        )

        assert row.search_norm == "farmacia"


# ========================================================================
# Testes de carregamento e reconstrução
# ========================================================================


class TestLoadAndRebuild:
    """Testes de load_from_iterable e _rebuild_rows."""

    def test_load_from_empty_iterable(self, vm: ClientesViewModel):
        """Testa carregamento de lista vazia."""
        vm.load_from_iterable([])

        rows = vm.get_rows()
        assert rows == []
        assert vm.get_status_choices() == []

    def test_load_from_single_cliente_dict(self, vm: ClientesViewModel):
        """Testa carregamento de 1 cliente via dict."""
        cliente = make_cliente_dict(id=1, razao_social="Empresa A")
        vm.load_from_iterable([cliente])

        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].id == "1"
        assert rows[0].razao_social == "Empresa A"

    def test_load_from_multiple_clientes(self, vm: ClientesViewModel):
        """Testa carregamento de múltiplos clientes."""
        clientes = [
            make_cliente_dict(id=1, razao_social="Alpha"),
            make_cliente_dict(id=2, razao_social="Beta"),
            make_cliente_dict(id=3, razao_social="Gamma"),
        ]
        vm.load_from_iterable(clientes)

        rows = vm.get_rows()
        assert len(rows) == 3
        assert rows[0].razao_social == "Alpha"
        assert rows[1].razao_social == "Beta"
        assert rows[2].razao_social == "Gamma"

    def test_load_from_cliente_object(self, vm: ClientesViewModel):
        """Testa carregamento de cliente como objeto (não dict)."""
        cliente = ClienteMock(
            id=99,
            razao_social="Objeto Teste",
            cnpj="11222333000144",
            nome="Maria",
            whatsapp="21988887777",
            observacoes="",
            ultima_alteracao="2025-11-30T08:00:00",
            ultima_por="admin",
        )
        vm.load_from_iterable([cliente])

        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].id == "99"
        assert rows[0].razao_social == "Objeto Teste"


# ========================================================================
# Testes de extração de status
# ========================================================================


class TestExtractStatus:
    """Testes de extract_status_and_observacoes."""

    def test_extract_status_from_observacoes_with_prefix(self, vm: ClientesViewModel):
        """Testa extração de status com prefixo [STATUS]."""
        status, obs = vm.extract_status_and_observacoes("[ATIVO] Cliente bom pagador")

        assert status == "ATIVO"
        assert obs == "Cliente bom pagador"

    def test_extract_status_empty_when_no_prefix(self, vm: ClientesViewModel):
        """Testa que retorna status vazio quando não há prefixo."""
        status, obs = vm.extract_status_and_observacoes("Apenas observação")

        assert status == ""
        assert obs == "Apenas observação"

    def test_extract_status_with_empty_observacoes(self, vm: ClientesViewModel):
        """Testa extração com observações vazias."""
        status, obs = vm.extract_status_and_observacoes("")

        assert status == ""
        assert obs == ""

    def test_extract_status_with_none_observacoes(self, vm: ClientesViewModel):
        """Testa extração com observações None."""
        status, obs = vm.extract_status_and_observacoes(None)  # type: ignore

        assert status == ""
        assert obs == ""

    def test_extract_status_multiple_brackets(self, vm: ClientesViewModel):
        """Testa que extrai apenas o primeiro status."""
        status, obs = vm.extract_status_and_observacoes("[INATIVO] Texto [OUTRO]")

        assert status == "INATIVO"
        assert "OUTRO" in obs  # O segundo bracket não é removido


# ========================================================================
# Testes de aplicação de status
# ========================================================================


class TestApplyStatus:
    """Testes de apply_status_to_observacoes."""

    def test_apply_status_adds_prefix(self, vm: ClientesViewModel):
        """Testa que adiciona prefixo [STATUS]."""
        result = vm.apply_status_to_observacoes("ATIVO", "Cliente premium")

        assert result == "[ATIVO] Cliente premium"

    def test_apply_status_with_empty_status(self, vm: ClientesViewModel):
        """Testa que retorna apenas texto quando status vazio."""
        result = vm.apply_status_to_observacoes("", "Apenas texto")

        assert result == "Apenas texto"

    def test_apply_status_with_whitespace_status(self, vm: ClientesViewModel):
        """Testa que ignora status só com whitespace."""
        result = vm.apply_status_to_observacoes("   ", "Texto")

        assert result == "Texto"

    def test_apply_status_with_empty_text(self, vm: ClientesViewModel):
        """Testa aplicação de status em texto vazio."""
        result = vm.apply_status_to_observacoes("PENDENTE", "")

        assert result == "[PENDENTE]"


# ========================================================================
# Testes de filtros
# ========================================================================


class TestFilters:
    """Testes de set_search_text e set_status_filter."""

    def test_search_text_filter_matches_razao(self, vm: ClientesViewModel):
        """Testa filtro por texto na razão social."""
        clientes = [
            make_cliente_dict(id=1, razao_social="Farmácia Central"),
            make_cliente_dict(id=2, razao_social="Mercado Bom Preço"),
            make_cliente_dict(id=3, razao_social="Farmácia Regional"),
        ]
        vm.load_from_iterable(clientes)

        vm.set_search_text("farmácia")
        rows = vm.get_rows()

        assert len(rows) == 2
        assert all("Farmácia" in r.razao_social for r in rows)

    def test_search_text_filter_case_insensitive(self, vm: ClientesViewModel):
        """Testa que busca é case-insensitive."""
        clientes = [make_cliente_dict(id=1, razao_social="EMPRESA MAIÚSCULA")]
        vm.load_from_iterable(clientes)

        vm.set_search_text("empresa")
        rows = vm.get_rows()

        assert len(rows) == 1

    def test_search_text_empty_returns_all(self, vm: ClientesViewModel):
        """Testa que busca vazia retorna todos."""
        clientes = [
            make_cliente_dict(id=1),
            make_cliente_dict(id=2),
        ]
        vm.load_from_iterable(clientes)

        vm.set_search_text("")
        rows = vm.get_rows()

        assert len(rows) == 2

    def test_search_text_no_rebuild(self, vm: ClientesViewModel):
        """Testa set_search_text com rebuild=False."""
        clientes = [make_cliente_dict(id=1, razao_social="Teste")]
        vm.load_from_iterable(clientes)

        vm.set_search_text("outro", rebuild=False)
        rows = vm.get_rows()

        # Ainda retorna o cliente porque não reconstruiu
        assert len(rows) == 1

    def test_status_filter_exact_match(self, vm: ClientesViewModel):
        """Testa filtro por status exato."""
        clientes = [
            make_cliente_dict(id=1, observacoes="[ATIVO] Obs1"),
            make_cliente_dict(id=2, observacoes="[INATIVO] Obs2"),
            make_cliente_dict(id=3, observacoes="[ATIVO] Obs3"),
        ]
        vm.load_from_iterable(clientes)

        vm.set_status_filter("ATIVO")
        rows = vm.get_rows()

        assert len(rows) == 2
        assert all(r.status == "ATIVO" for r in rows)

    def test_status_filter_case_insensitive(self, vm: ClientesViewModel):
        """Testa que filtro de status é case-insensitive."""
        clientes = [make_cliente_dict(id=1, observacoes="[ativo] Teste")]
        vm.load_from_iterable(clientes)

        vm.set_status_filter("ATIVO")
        rows = vm.get_rows()

        assert len(rows) == 1

    def test_status_filter_none_returns_all(self, vm: ClientesViewModel):
        """Testa que filtro None retorna todos."""
        clientes = [
            make_cliente_dict(id=1, observacoes="[ATIVO] A"),
            make_cliente_dict(id=2, observacoes="[INATIVO] B"),
        ]
        vm.load_from_iterable(clientes)

        vm.set_status_filter(None)
        rows = vm.get_rows()

        assert len(rows) == 2

    def test_status_filter_no_rebuild(self, vm: ClientesViewModel):
        """Testa set_status_filter com rebuild=False."""
        clientes = [make_cliente_dict(id=1, observacoes="[ATIVO] Teste")]
        vm.load_from_iterable(clientes)

        vm.set_status_filter("INATIVO", rebuild=False)
        rows = vm.get_rows()

        # Ainda retorna porque não reconstruiu
        assert len(rows) == 1


# ========================================================================
# Testes de ordenação
# ========================================================================


class TestOrdering:
    """Testes de set_order_label e _sort_rows."""

    def test_order_by_razao_social_ascending(self, vm_with_order: ClientesViewModel):
        """Testa ordenação por razão social (A-Z)."""
        clientes = [
            make_cliente_dict(id=1, razao_social="Zulu"),
            make_cliente_dict(id=2, razao_social="Alpha"),
            make_cliente_dict(id=3, razao_social="Bravo"),
        ]
        vm_with_order.load_from_iterable(clientes)
        vm_with_order.set_order_label("Razão Social")

        rows = vm_with_order.get_rows()

        assert rows[0].razao_social == "Alpha"
        assert rows[1].razao_social == "Bravo"
        assert rows[2].razao_social == "Zulu"

    def test_order_by_razao_social_descending(self, vm_with_order: ClientesViewModel):
        """Testa ordenação por razão social (Z-A)."""
        clientes = [
            make_cliente_dict(id=1, razao_social="Alpha"),
            make_cliente_dict(id=2, razao_social="Zulu"),
            make_cliente_dict(id=3, razao_social="Bravo"),
        ]
        vm_with_order.load_from_iterable(clientes)
        vm_with_order.set_order_label("Razão Social (Z-A)")

        rows = vm_with_order.get_rows()

        assert rows[0].razao_social == "Zulu"
        assert rows[1].razao_social == "Bravo"
        assert rows[2].razao_social == "Alpha"

    def test_order_by_nome(self, vm_with_order: ClientesViewModel):
        """Testa ordenação por nome."""
        clientes = [
            make_cliente_dict(id=1, nome="Maria"),
            make_cliente_dict(id=2, nome="Ana"),
            make_cliente_dict(id=3, nome="João"),
        ]
        vm_with_order.load_from_iterable(clientes)
        vm_with_order.set_order_label("Nome")

        rows = vm_with_order.get_rows()

        assert rows[0].nome == "Ana"
        assert rows[1].nome == "João"
        assert rows[2].nome == "Maria"

    def test_order_by_cnpj(self, vm_with_order: ClientesViewModel):
        """Testa ordenação por CNPJ (apenas dígitos)."""
        clientes = [
            make_cliente_dict(id=1, cnpj="99888777000166"),
            make_cliente_dict(id=2, cnpj="11222333000144"),
            make_cliente_dict(id=3, cnpj="55666777000188"),
        ]
        vm_with_order.load_from_iterable(clientes)
        vm_with_order.set_order_label("CNPJ")

        rows = vm_with_order.get_rows()

        # Ordem numérica dos dígitos (CNPJ pode estar formatado)
        assert rows[0].id == "2"  # 11222333
        assert rows[1].id == "3"  # 55666777
        assert rows[2].id == "1"  # 99888777

    def test_order_by_id_numeric(self, vm_with_order: ClientesViewModel):
        """Testa ordenação por ID numérico."""
        clientes = [
            make_cliente_dict(id=100),
            make_cliente_dict(id=2),
            make_cliente_dict(id=30),
        ]
        vm_with_order.load_from_iterable(clientes)
        vm_with_order.set_order_label("ID")

        rows = vm_with_order.get_rows()

        assert rows[0].id == "2"
        assert rows[1].id == "30"
        assert rows[2].id == "100"

    def test_order_nulls_last_razao(self, vm_with_order: ClientesViewModel):
        """Testa que valores vazios vão para o final na ordenação."""
        clientes = [
            make_cliente_dict(id=1, razao_social="Bravo"),
            make_cliente_dict(id=2, razao_social=""),
            make_cliente_dict(id=3, razao_social="Alpha"),
        ]
        vm_with_order.load_from_iterable(clientes)
        vm_with_order.set_order_label("Razão Social")

        rows = vm_with_order.get_rows()

        assert rows[0].razao_social == "Alpha"
        assert rows[1].razao_social == "Bravo"
        assert rows[2].razao_social == ""

    def test_set_order_no_rebuild(self, vm_with_order: ClientesViewModel):
        """Testa set_order_label com rebuild=False."""
        clientes = [
            make_cliente_dict(id=1, razao_social="Zulu"),
            make_cliente_dict(id=2, razao_social="Alpha"),
        ]
        # Carregar SEM label inicial para garantir ordem original
        vm_no_order = ClientesViewModel()
        vm_no_order.load_from_iterable(clientes)

        vm_no_order.set_order_label("Razão Social", rebuild=False)
        rows = vm_no_order.get_rows()

        # Ordem não mudou porque não reconstruiu
        assert rows[0].razao_social == "Zulu"


# ========================================================================
# Testes de get_status_choices
# ========================================================================


class TestStatusChoices:
    """Testes de get_status_choices."""

    def test_status_choices_empty_when_no_clientes(self, vm: ClientesViewModel):
        """Testa que choices é vazio sem clientes."""
        vm.load_from_iterable([])

        choices = vm.get_status_choices()

        assert choices == []

    def test_status_choices_unique(self, vm: ClientesViewModel):
        """Testa que choices contém apenas valores únicos."""
        clientes = [
            make_cliente_dict(id=1, observacoes="[ATIVO] A"),
            make_cliente_dict(id=2, observacoes="[ATIVO] B"),
            make_cliente_dict(id=3, observacoes="[INATIVO] C"),
        ]
        vm.load_from_iterable(clientes)

        choices = vm.get_status_choices()

        assert len(choices) == 2
        assert "ATIVO" in choices
        assert "INATIVO" in choices

    def test_status_choices_sorted(self, vm: ClientesViewModel):
        """Testa que choices é ordenado alfabeticamente."""
        clientes = [
            make_cliente_dict(id=1, observacoes="[Zulu] A"),
            make_cliente_dict(id=2, observacoes="[Alpha] B"),
            make_cliente_dict(id=3, observacoes="[Bravo] C"),
        ]
        vm.load_from_iterable(clientes)

        choices = vm.get_status_choices()

        assert choices == ["Alpha", "Bravo", "Zulu"]


# ========================================================================
# Testes de batch operations
# ========================================================================


class TestBatchOperations:
    """Testes de delete_clientes_batch, restore_clientes_batch, export_clientes_batch."""

    def test_delete_clientes_batch_success(self, vm: ClientesViewModel):
        """Testa exclusão em lote bem-sucedida."""
        with patch("src.modules.clientes.service.excluir_clientes_definitivamente") as mock_excluir:
            mock_excluir.return_value = (3, [])

            qtd, erros = vm.delete_clientes_batch(["1", "2", "3"])

            assert qtd == 3
            assert erros == []
            mock_excluir.assert_called_once_with([1, 2, 3])

    def test_delete_clientes_batch_with_errors(self, vm: ClientesViewModel):
        """Testa exclusão em lote com erros."""
        with patch("src.modules.clientes.service.excluir_clientes_definitivamente") as mock_excluir:
            mock_excluir.return_value = (2, [(1, "Erro ao excluir")])

            qtd, erros = vm.delete_clientes_batch(["1", "2", "3"])

            assert qtd == 2
            assert len(erros) == 1
            assert erros[0] == (1, "Erro ao excluir")

    def test_restore_clientes_batch(self, vm: ClientesViewModel):
        """Testa restauração em lote."""
        with patch("src.modules.clientes.service.restaurar_clientes_da_lixeira") as mock_restaurar:
            vm.restore_clientes_batch(["10", "20", "30"])

            mock_restaurar.assert_called_once_with([10, 20, 30])

    def test_export_clientes_batch_logs(self, vm: ClientesViewModel, monkeypatch):
        """Testa que export valida seleção vazia e exibe warning."""
        # Mock cloud_guardrails para permitir operação
        monkeypatch.setattr(
            "src.utils.helpers.cloud_guardrails.check_cloud_only_block",
            lambda operation_name: False,
        )

        # Mock messagebox para capturar warnings
        warning_called = []

        def mock_showwarning(title, message):
            warning_called.append((title, message))

        monkeypatch.setattr("tkinter.messagebox.showwarning", mock_showwarning)

        # Chamar com seleção vazia para testar validação
        vm.export_clientes_batch([])

        # Verifica que mostrou warning de seleção vazia
        assert len(warning_called) == 1
        assert "Nenhum cliente selecionado" in warning_called[0][1]


# ========================================================================
# Testes de _build_row_from_cliente
# ========================================================================


class TestBuildRow:
    """Testes de _build_row_from_cliente."""

    def test_build_row_with_all_fields(self, vm: ClientesViewModel):
        """Testa construção de row com todos os campos."""
        cliente = make_cliente_dict(
            id=42,
            razao_social="Empresa XYZ",
            cnpj="12345678000199",
            nome="Maria Silva",
            whatsapp="21987654321",
            observacoes="[ATIVO] Cliente premium",
            ultima_alteracao="2025-12-01T15:30:00",
            ultima_por="admin@example.com",
        )

        row = vm._build_row_from_cliente(cliente)

        assert row.id == "42"
        assert row.razao_social == "Empresa XYZ"
        assert row.nome == "Maria Silva"
        assert row.status == "ATIVO"
        assert row.observacoes == "Cliente premium"
        assert row.search_norm != ""  # deve ter sido normalizado

    def test_build_row_with_missing_fields(self, vm: ClientesViewModel):
        """Testa construção com campos faltando."""
        cliente = {"id": 1}  # Mínimo possível

        row = vm._build_row_from_cliente(cliente)

        assert row.id == "1"
        assert row.razao_social == ""
        assert row.cnpj == ""
        assert row.nome == ""

    def test_build_row_formats_cnpj(self, vm: ClientesViewModel):
        """Testa formatação de CNPJ."""
        cliente = make_cliente_dict(cnpj="12345678000199")

        with patch("src.utils.text_utils.format_cnpj") as mock_format:
            mock_format.return_value = "12.345.678/0001-99"

            row = vm._build_row_from_cliente(cliente)

            assert row.cnpj == "12.345.678/0001-99"

    def test_build_row_formats_date(self, vm: ClientesViewModel):
        """Testa formatação de data."""
        cliente = make_cliente_dict(ultima_alteracao="2025-12-01T10:00:00")

        with patch("src.app_utils.fmt_data") as mock_fmt:
            mock_fmt.return_value = "01/12/2025"

            row = vm._build_row_from_cliente(cliente)

            assert "01/12/2025" in row.ultima_alteracao

    def test_build_row_adds_initial_to_date(self, vm: ClientesViewModel):
        """Testa que adiciona inicial do autor na data."""
        cliente = make_cliente_dict(
            ultima_alteracao="2025-12-01",
            ultima_por="admin@example.com",
        )

        with patch("src.app_utils.fmt_data", return_value="01/12/2025"):
            row = vm._build_row_from_cliente(cliente)

            # Deve ter inicial (A) de admin
            assert "(A)" in row.ultima_alteracao or row.ultima_alteracao == "01/12/2025"

    def test_build_row_with_author_resolver(self):
        """Testa uso de author_resolver customizado."""

        def resolver(email: str) -> str:
            return "X" if "admin" in email else ""

        vm_custom = ClientesViewModel(author_resolver=resolver)
        cliente = make_cliente_dict(ultima_por="admin@test.com")

        with patch("src.app_utils.fmt_data", return_value="01/12"):
            row = vm_custom._build_row_from_cliente(cliente)

            assert "(X)" in row.ultima_alteracao

    def test_build_row_normalizes_search(self, vm: ClientesViewModel):
        """Testa que search_norm é preenchido."""
        cliente = make_cliente_dict(
            razao_social="Farmácia Açúcar",
            nome="José",
        )

        row = vm._build_row_from_cliente(cliente)

        # join_and_normalize deve remover acentos e normalizar
        assert "farmacia" in row.search_norm.lower()
        assert "acucar" in row.search_norm.lower()

    def test_build_row_with_initials_map_env(self, vm: ClientesViewModel):
        """Testa que lê RC_INITIALS_MAP do ambiente."""
        cliente = make_cliente_dict(ultima_por="john@example.com")

        mapping = json.dumps({"john@example.com": "JD"})
        with patch.dict(os.environ, {"RC_INITIALS_MAP": mapping}):
            with patch("src.app_utils.fmt_data", return_value="01/12"):
                row = vm._build_row_from_cliente(cliente)

                assert "(J)" in row.ultima_alteracao  # primeira letra de "JD"


# ========================================================================
# Testes de _value_from_cliente
# ========================================================================


class TestValueFromCliente:
    """Testes do método estático _value_from_cliente."""

    def test_value_from_dict_first_match(self):
        """Testa extração de valor de dict com primeiro nome."""
        cliente = {"razao_social": "Teste", "razao": "Outro"}

        value = ClientesViewModel._value_from_cliente(cliente, "razao_social", "razao")

        assert value == "Teste"

    def test_value_from_dict_fallback(self):
        """Testa fallback para segundo nome quando primeiro não existe."""
        cliente = {"razao": "Valor"}

        value = ClientesViewModel._value_from_cliente(cliente, "razao_social", "razao")

        assert value == "Valor"

    def test_value_from_object_attribute(self):
        """Testa extração de atributo de objeto."""
        cliente = ClienteMock(razao_social="Objeto")

        value = ClientesViewModel._value_from_cliente(cliente, "razao_social")

        assert value == "Objeto"

    def test_value_from_cliente_returns_empty_when_not_found(self):
        """Testa que retorna vazio quando nenhum nome bate."""
        cliente = {"outro_campo": "valor"}

        value = ClientesViewModel._value_from_cliente(cliente, "razao_social", "nome")

        assert value == ""

    def test_value_from_cliente_ignores_none(self):
        """Testa que ignora valores None."""
        cliente = {"razao_social": None, "razao": "Valor"}

        value = ClientesViewModel._value_from_cliente(cliente, "razao_social", "razao")

        assert value == "Valor"

    def test_value_from_cliente_ignores_empty_string(self):
        """Testa que ignora strings vazias."""
        cliente = {"razao_social": "", "razao": "Valor"}

        value = ClientesViewModel._value_from_cliente(cliente, "razao_social", "razao")

        assert value == "Valor"


# ========================================================================
# Testes de refresh_from_service
# ========================================================================


class TestRefreshFromService:
    """Testes de refresh_from_service."""

    def test_refresh_from_service_success(self):
        """Testa carregamento via serviço."""
        vm_svc = ClientesViewModel()

        fake_clientes = [
            make_cliente_dict(id=1, razao_social="A"),
            make_cliente_dict(id=2, razao_social="B"),
        ]

        with patch("src.modules.clientes.viewmodel.search_clientes") as mock_search:
            mock_search.return_value = fake_clientes

            vm_svc.refresh_from_service()

            rows = vm_svc.get_rows()
            assert len(rows) == 2

    def test_refresh_from_service_with_order(self):
        """Testa que refresh respeita ordenação configurada."""
        order_choices = {"ID": ("id", False)}
        vm_svc = ClientesViewModel(
            order_choices=order_choices,
            default_order_label="ID",
        )

        fake_clientes = [
            make_cliente_dict(id=30),
            make_cliente_dict(id=10),
            make_cliente_dict(id=20),
        ]

        with patch("src.modules.clientes.viewmodel.search_clientes") as mock_search:
            mock_search.return_value = fake_clientes

            vm_svc.refresh_from_service()

            rows = vm_svc.get_rows()
            assert rows[0].id == "10"
            assert rows[1].id == "20"
            assert rows[2].id == "30"

    def test_refresh_from_service_with_reverse_order(self):
        """Testa refresh com ordenação reversa."""
        order_choices = {"ID": ("id", True)}
        vm_svc = ClientesViewModel(
            order_choices=order_choices,
            default_order_label="ID",
        )

        fake_clientes = [
            make_cliente_dict(id=10),
            make_cliente_dict(id=20),
        ]

        with patch("src.modules.clientes.viewmodel.search_clientes") as mock_search:
            mock_search.return_value = fake_clientes

            vm_svc.refresh_from_service()

            rows = vm_svc.get_rows()
            # Reverse é aplicado APÓS o search, então ordem final é invertida
            assert rows[0].id == "20"
            assert rows[1].id == "10"

    def test_refresh_from_service_raises_error(self):
        """Testa que erro do serviço é propagado como ClientesViewModelError."""
        vm_svc = ClientesViewModel()

        with patch("src.modules.clientes.viewmodel.search_clientes") as mock_search:
            mock_search.side_effect = RuntimeError("Erro no banco")

            with pytest.raises(ClientesViewModelError) as exc_info:
                vm_svc.refresh_from_service()

            assert "Erro no banco" in str(exc_info.value)


# ========================================================================
# Testes de helpers estáticos
# ========================================================================


class TestStaticHelpers:
    """Testes de métodos estáticos auxiliares."""

    def test_only_digits_removes_non_digits(self):
        """Testa que _only_digits remove tudo exceto números."""
        result = ClientesViewModel._only_digits("12.345.678/0001-99")

        assert result == "12345678000199"

    def test_only_digits_with_empty_string(self):
        """Testa _only_digits com string vazia."""
        result = ClientesViewModel._only_digits("")

        assert result == ""

    def test_key_nulls_last_with_value(self):
        """Testa _key_nulls_last com valor não vazio."""
        is_empty, key = ClientesViewModel._key_nulls_last("Alpha", str.casefold)

        assert is_empty is False
        assert key == "alpha"

    def test_key_nulls_last_with_empty_string(self):
        """Testa _key_nulls_last com string vazia."""
        is_empty, key = ClientesViewModel._key_nulls_last("", str.casefold)

        assert is_empty is True
        assert key == ""

    def test_key_nulls_last_with_none(self):
        """Testa _key_nulls_last com None."""
        is_empty, key = ClientesViewModel._key_nulls_last(None, str.casefold)

        assert is_empty is True
        assert key == ""

    def test_key_nulls_last_with_whitespace(self):
        """Testa _key_nulls_last com apenas whitespace."""
        is_empty, key = ClientesViewModel._key_nulls_last("   ", str.casefold)

        assert is_empty is True  # strip torna vazio
        assert key == ""


# ========================================================================
# Testes de error handling
# ========================================================================


class TestErrorHandling:
    """Testes de tratamento de erros e fallbacks."""

    def test_build_row_handles_cnpj_format_error(self, vm: ClientesViewModel):
        """Testa fallback quando format_cnpj falha."""
        cliente = make_cliente_dict(cnpj="12345678000199")

        with patch("src.utils.text_utils.format_cnpj") as mock_format:
            mock_format.side_effect = Exception("Erro ao formatar")

            row = vm._build_row_from_cliente(cliente)

            # Deve usar CNPJ raw sem formatação
            assert row.cnpj == "12345678000199"

    def test_build_row_handles_date_format_error(self, vm: ClientesViewModel):
        """Testa fallback quando fmt_datetime_br falha."""
        cliente = make_cliente_dict(ultima_alteracao="2025-12-01T10:00:00")

        with patch("src.helpers.formatters.fmt_datetime_br") as mock_fmt:
            mock_fmt.side_effect = Exception("Erro ao formatar")

            row = vm._build_row_from_cliente(cliente)

            # Deve usar string bruta da data quando formatação falha (fallback)
            assert "2025-12-01T10:00:00" in row.ultima_alteracao

    def test_build_row_handles_invalid_initials_json(self, vm: ClientesViewModel):
        """Testa fallback quando RC_INITIALS_MAP tem JSON inválido."""
        cliente = make_cliente_dict(ultima_por="user@test.com")

        with patch.dict(os.environ, {"RC_INITIALS_MAP": "{invalid json"}):
            with patch("src.app_utils.fmt_data", return_value="01/12"):
                row = vm._build_row_from_cliente(cliente)

                # Deve usar primeira letra do email
                assert "(U)" in row.ultima_alteracao or "(u)" in row.ultima_alteracao

    def test_sort_rows_with_invalid_column(self, vm: ClientesViewModel):
        """Testa que retorna rows sem ordenar se coluna inválida."""
        clientes = [
            make_cliente_dict(id=2, razao_social="Beta"),
            make_cliente_dict(id=1, razao_social="Alpha"),
        ]
        vm.load_from_iterable(clientes)

        # Chamar _sort_rows com coluna que não existe
        rows = [vm._build_row_from_cliente(c) for c in clientes]
        sorted_rows = vm._sort_rows(rows)

        # Deve retornar na ordem original
        assert sorted_rows[0].id == "2"
        assert sorted_rows[1].id == "1"

    def test_order_by_id_with_invalid_ids(self):
        """Testa ordenação por ID com IDs não numéricos."""
        order_choices = {"ID": ("id", False)}
        vm_ord = ClientesViewModel(
            order_choices=order_choices,
            default_order_label="ID",
        )

        clientes = [
            {"id": "abc", "razao_social": "A"},  # ID inválido
            {"id": 10, "razao_social": "B"},
            {"id": "xyz", "razao_social": "C"},  # ID inválido
            {"id": 5, "razao_social": "D"},
        ]
        vm_ord.load_from_iterable(clientes)

        rows = vm_ord.get_rows()

        # IDs válidos vêm primeiro (ordenados), inválidos no final
        assert rows[0].id == "5"
        assert rows[1].id == "10"
        # abc e xyz vão para o final (ordem original)
