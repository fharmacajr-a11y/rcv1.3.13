"""
Testes unitários para selection_manager.py (MS-17 Headless Selection Management).

Este módulo testa SelectionSnapshot e SelectionManager de forma headless,
sem dependências do Tkinter. Segue o padrão estabelecido nas microfases anteriores.

Objetivo: Elevar a cobertura de 46.0% para ≥85%.
Linhas não cobertas alvo: 47, 52, 113-120, 132-144, 166-167.
"""

import pytest

from src.modules.clientes.controllers.selection_manager import (
    SelectionManager,
    SelectionSnapshot,
)
from src.modules.clientes.viewmodel import ClienteRow


# ────────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_cliente_rows() -> list[ClienteRow]:
    """Lista de ClienteRow para testes."""
    return [
        ClienteRow(
            id="1",
            razao_social="Empresa Um LTDA",
            cnpj="11.111.111/0001-11",
            nome="Cliente Um",
            whatsapp="11-11111-1111",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2024-01-01",
        ),
        ClienteRow(
            id="2",
            razao_social="Empresa Dois LTDA",
            cnpj="22.222.222/0002-22",
            nome="Cliente Dois",
            whatsapp="22-22222-2222",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2024-01-02",
        ),
        ClienteRow(
            id="3",
            razao_social="Empresa Três LTDA",
            cnpj="33.333.333/0003-33",
            nome="Cliente Três",
            whatsapp="33-33333-3333",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2024-01-03",
        ),
    ]


@pytest.fixture
def empty_selection_manager(sample_cliente_rows: list[ClienteRow]) -> SelectionManager:
    """SelectionManager com clientes mas sem seleção."""
    return SelectionManager(all_clients=sample_cliente_rows)


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionSnapshot
# ────────────────────────────────────────────────────────────────────────────────


class TestSelectionSnapshot:
    """Testes do dataclass SelectionSnapshot."""

    def test_count_empty(self):
        """Testa propriedade count com seleção vazia."""
        snapshot = SelectionSnapshot(selected_ids=frozenset(), all_clients=[])
        assert snapshot.count == 0

    def test_count_with_selection(self, sample_cliente_rows: list[ClienteRow]):
        """Testa propriedade count com seleção não vazia."""
        snapshot = SelectionSnapshot(
            selected_ids=frozenset(["1", "2"]),
            all_clients=sample_cliente_rows,
        )
        assert snapshot.count == 2

    def test_has_selection_false(self):
        """Testa propriedade has_selection quando vazia (linha 47)."""
        snapshot = SelectionSnapshot(selected_ids=frozenset(), all_clients=[])
        assert snapshot.has_selection is False

    def test_has_selection_true(self, sample_cliente_rows: list[ClienteRow]):
        """Testa propriedade has_selection quando não vazia (linha 47)."""
        snapshot = SelectionSnapshot(
            selected_ids=frozenset(["1"]),
            all_clients=sample_cliente_rows,
        )
        assert snapshot.has_selection is True

    def test_immutability(self, sample_cliente_rows: list[ClienteRow]):
        """Testa imutabilidade do dataclass frozen."""
        snapshot = SelectionSnapshot(
            selected_ids=frozenset(["1"]),
            all_clients=sample_cliente_rows,
        )
        with pytest.raises(AttributeError):
            snapshot.selected_ids = frozenset(["2"])  # type: ignore

    def test_repr_contains_count(self, sample_cliente_rows: list[ClienteRow]):
        """Testa __repr__ gerado automaticamente (linha 52)."""
        snapshot = SelectionSnapshot(
            selected_ids=frozenset(["1", "2"]),
            all_clients=sample_cliente_rows,
        )
        repr_str = repr(snapshot)
        assert "SelectionSnapshot" in repr_str
        assert "selected_ids" in repr_str


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionManager Initialization
# ────────────────────────────────────────────────────────────────────────────────


class TestSelectionManagerInit:
    """Testes de inicialização do SelectionManager."""

    def test_init_with_clients(self, sample_cliente_rows: list[ClienteRow]):
        """Testa construtor com lista de clientes."""
        manager = SelectionManager(all_clients=sample_cliente_rows)
        assert manager is not None

    def test_init_with_empty_list(self):
        """Testa construtor com lista vazia."""
        manager = SelectionManager(all_clients=[])
        snapshot = manager.build_snapshot(selected_ids=[])
        assert snapshot.count == 0

    def test_id_to_row_mapping(self, sample_cliente_rows: list[ClienteRow]):
        """Testa que o mapeamento interno ID->ClienteRow foi criado."""
        manager = SelectionManager(all_clients=sample_cliente_rows)
        # Validação indireta: get_selected_client_rows deve funcionar
        snapshot = manager.build_snapshot(selected_ids=["1"])
        rows = manager.get_selected_client_rows(snapshot)
        assert len(rows) == 1
        assert rows[0].id == "1"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionManager.build_snapshot
# ────────────────────────────────────────────────────────────────────────────────


class TestBuildSnapshot:
    """Testes do método build_snapshot."""

    def test_build_snapshot_empty_selection(self, empty_selection_manager: SelectionManager):
        """Testa build_snapshot com seleção vazia."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=[])
        assert snapshot.count == 0
        assert not snapshot.has_selection

    def test_build_snapshot_single_selection(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa build_snapshot com um ID selecionado."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1"])
        assert snapshot.count == 1
        assert snapshot.has_selection

    def test_build_snapshot_multiple_selection(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa build_snapshot com múltiplos IDs."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1", "2", "3"])
        assert snapshot.count == 3

    def test_build_snapshot_preserves_all_clients(
        self,
        empty_selection_manager: SelectionManager,
        sample_cliente_rows: list[ClienteRow],
    ):
        """Testa que build_snapshot preserva all_clients."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1"])
        assert len(snapshot.all_clients) == len(sample_cliente_rows)


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionManager.get_selected_client_rows
# ────────────────────────────────────────────────────────────────────────────────


class TestGetSelectedClientRows:
    """Testes do método get_selected_client_rows (linhas 113-120)."""

    def test_get_selected_client_rows_empty(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno vazio quando nenhum ID selecionado."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=[])
        rows = empty_selection_manager.get_selected_client_rows(snapshot)
        assert rows == []

    def test_get_selected_client_rows_single(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno com um ID selecionado (linhas 113-120)."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1"])
        rows = empty_selection_manager.get_selected_client_rows(snapshot)
        assert len(rows) == 1
        assert rows[0].id == "1"
        assert rows[0].nome == "Cliente Um"

    def test_get_selected_client_rows_multiple(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno com múltiplos IDs selecionados (linhas 113-120)."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1", "3"])
        rows = empty_selection_manager.get_selected_client_rows(snapshot)
        assert len(rows) == 2
        ids = {row.id for row in rows}
        assert ids == {"1", "3"}

    def test_get_selected_client_rows_invalid_id(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa que IDs inválidos são ignorados silenciosamente."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["999"])
        rows = empty_selection_manager.get_selected_client_rows(snapshot)
        assert rows == []

    def test_get_selected_client_rows_mixed_valid_invalid(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa mistura de IDs válidos e inválidos."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1", "999", "2"])
        rows = empty_selection_manager.get_selected_client_rows(snapshot)
        assert len(rows) == 2
        ids = {row.id for row in rows}
        assert ids == {"1", "2"}


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionManager.get_selected_client_ids_as_int
# ────────────────────────────────────────────────────────────────────────────────


class TestGetSelectedClientIdsAsInt:
    """Testes do método get_selected_client_ids_as_int (linhas 132-144)."""

    def test_get_selected_client_ids_as_int_empty(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno vazio quando nenhum ID selecionado."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=[])
        ids = empty_selection_manager.get_selected_client_ids_as_int(snapshot)
        assert ids == []

    def test_get_selected_client_ids_as_int_single(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa conversão de um ID para int (linhas 132-144)."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1"])
        ids = empty_selection_manager.get_selected_client_ids_as_int(snapshot)
        assert ids == [1]

    def test_get_selected_client_ids_as_int_multiple(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa conversão de múltiplos IDs para int (linhas 132-144)."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1", "2", "3"])
        ids = empty_selection_manager.get_selected_client_ids_as_int(snapshot)
        assert set(ids) == {1, 2, 3}

    def test_get_selected_client_ids_as_int_invalid_id(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa que IDs não numéricos são ignorados (try/except linhas 136-140)."""
        # Adicionar cliente com ID não numérico
        manager = SelectionManager(
            all_clients=[
                ClienteRow(
                    id="abc",  # ID inválido para conversão
                    razao_social="Empresa Inválida",
                    cnpj="00.000.000/0000-00",
                    nome="Cliente Inválido",
                    whatsapp="00-00000-0000",
                    observacoes="",
                    status="Ativo",
                    ultima_alteracao="2024-01-01",
                ),
            ],
        )
        snapshot = manager.build_snapshot(selected_ids=["abc"])
        ids = manager.get_selected_client_ids_as_int(snapshot)
        assert ids == []  # ID não numérico ignorado

    def test_get_selected_client_ids_as_int_mixed_valid_invalid(
        self,
        empty_selection_manager: SelectionManager,
        sample_cliente_rows: list[ClienteRow],
    ):
        """Testa mistura de IDs válidos e inválidos para conversão."""
        # Adicionar cliente com ID inválido
        all_clients = sample_cliente_rows + [
            ClienteRow(
                id="xyz",
                razao_social="Empresa Inválida",
                cnpj="00.000.000/0000-00",
                nome="Cliente Inválido",
                whatsapp="00-00000-0000",
                observacoes="",
                status="Ativo",
                ultima_alteracao="2024-01-01",
            ),
        ]
        manager = SelectionManager(all_clients=all_clients)
        snapshot = manager.build_snapshot(selected_ids=["1", "xyz", "2"])
        ids = manager.get_selected_client_ids_as_int(snapshot)
        # Apenas IDs numéricos devem ser convertidos
        assert set(ids) == {1, 2}

    def test_get_selected_client_ids_as_int_nonexistent_id(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa que IDs que não existem no mapa são ignorados."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["999"])
        ids = empty_selection_manager.get_selected_client_ids_as_int(snapshot)
        assert ids == []


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionManager.get_selected_ids_as_set
# ────────────────────────────────────────────────────────────────────────────────


class TestGetSelectedIdsAsSet:
    """Testes do método get_selected_ids_as_set."""

    def test_get_selected_ids_as_set_empty(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno vazio quando nenhum ID selecionado."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=[])
        ids = empty_selection_manager.get_selected_ids_as_set(snapshot)
        assert ids == set()

    def test_get_selected_ids_as_set_single(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno com um ID selecionado."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1"])
        ids = empty_selection_manager.get_selected_ids_as_set(snapshot)
        assert ids == {"1"}

    def test_get_selected_ids_as_set_multiple(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa retorno com múltiplos IDs selecionados."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1", "2", "3"])
        ids = empty_selection_manager.get_selected_ids_as_set(snapshot)
        assert ids == {"1", "2", "3"}


# ────────────────────────────────────────────────────────────────────────────────
# Tests: SelectionManager.update_all_clients
# ────────────────────────────────────────────────────────────────────────────────


class TestUpdateAllClients:
    """Testes do método update_all_clients (linhas 166-167)."""

    def test_update_all_clients_replaces_data(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa que update_all_clients substitui os clientes (linhas 166-167)."""
        new_clients = [
            ClienteRow(
                id="100",
                razao_social="Empresa Nova LTDA",
                cnpj="10.010.010/0100-10",
                nome="Novo Cliente",
                whatsapp="41-41414-4141",
                observacoes="",
                status="Ativo",
                ultima_alteracao="2024-01-10",
            ),
        ]
        empty_selection_manager.update_all_clients(all_clients=new_clients)

        # Validar que o novo cliente está disponível
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["100"])
        rows = empty_selection_manager.get_selected_client_rows(snapshot)
        assert len(rows) == 1
        assert rows[0].id == "100"

    def test_update_all_clients_invalidates_old_ids(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa que update_all_clients invalida IDs antigos."""
        # IDs antigos: 1, 2, 3
        snapshot_old = empty_selection_manager.build_snapshot(selected_ids=["1"])
        rows_old = empty_selection_manager.get_selected_client_rows(snapshot_old)
        assert len(rows_old) == 1

        # Atualizar para novos clientes (sem ID 1)
        new_clients = [
            ClienteRow(
                id="200",
                razao_social="Empresa Nova LTDA",
                cnpj="20.020.020/0200-20",
                nome="Cliente Novo",
                whatsapp="71-71717-7171",
                observacoes="",
                status="Ativo",
                ultima_alteracao="2024-02-01",
            ),
        ]
        empty_selection_manager.update_all_clients(all_clients=new_clients)

        # ID 1 não deve mais existir
        snapshot_new = empty_selection_manager.build_snapshot(selected_ids=["1"])
        rows_new = empty_selection_manager.get_selected_client_rows(snapshot_new)
        assert rows_new == []

    def test_update_all_clients_with_empty_list(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa update_all_clients com lista vazia."""
        empty_selection_manager.update_all_clients(all_clients=[])
        snapshot = empty_selection_manager.build_snapshot(selected_ids=[])
        assert snapshot.count == 0

    def test_update_all_clients_preserves_snapshot_semantics(
        self,
        empty_selection_manager: SelectionManager,
    ):
        """Testa que snapshots antigos permanecem imutáveis após update."""
        # Criar snapshot antes de update
        snapshot_before = empty_selection_manager.build_snapshot(selected_ids=["1"])
        assert snapshot_before.count == 1
        assert len(snapshot_before.all_clients) == 3

        # Atualizar clientes
        empty_selection_manager.update_all_clients(all_clients=[])

        # Snapshot antigo ainda deve ter os dados originais (imutável)
        assert snapshot_before.count == 1
        assert len(snapshot_before.all_clients) == 3


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ────────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_large_selection(self, empty_selection_manager: SelectionManager):
        """Testa seleção com muitos IDs."""
        # Criar 1000 clientes
        large_client_list = [
            ClienteRow(
                id=str(i),
                razao_social=f"Empresa {i} LTDA",
                cnpj=f"{i:014d}",
                nome=f"Cliente {i}",
                whatsapp="00-00000-0000",
                observacoes="",
                status="Ativo",
                ultima_alteracao="2024-01-01",
            )
            for i in range(1000)
        ]
        manager = SelectionManager(all_clients=large_client_list)

        # Selecionar todos
        all_ids = [str(i) for i in range(1000)]
        snapshot = manager.build_snapshot(selected_ids=all_ids)
        assert snapshot.count == 1000

        rows = manager.get_selected_client_rows(snapshot)
        assert len(rows) == 1000

        ids_as_int = manager.get_selected_client_ids_as_int(snapshot)
        assert len(ids_as_int) == 1000

    def test_duplicate_ids_in_selection(self, empty_selection_manager: SelectionManager):
        """Testa que IDs duplicados são deduplicados (frozenset)."""
        snapshot = empty_selection_manager.build_snapshot(selected_ids=["1", "1", "1"])
        assert snapshot.count == 1  # frozenset deduplica

    def test_special_characters_in_ids(self):
        """Testa IDs com caracteres especiais."""
        special_clients = [
            ClienteRow(
                id="abc-123",
                razao_social="Empresa Especial LTDA",
                cnpj="00.000.000/0000-00",
                nome="Cliente Especial",
                whatsapp="00-00000-0000",
                observacoes="",
                status="Ativo",
                ultima_alteracao="2024-01-01",
            ),
        ]
        manager = SelectionManager(all_clients=special_clients)
        snapshot = manager.build_snapshot(selected_ids=["abc-123"])
        rows = manager.get_selected_client_rows(snapshot)
        assert len(rows) == 1
        assert rows[0].id == "abc-123"

        # Não deve converter para int (ValueError)
        ids_as_int = manager.get_selected_client_ids_as_int(snapshot)
        assert ids_as_int == []
