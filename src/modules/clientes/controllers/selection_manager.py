# -*- coding: utf-8 -*-
# pyright: strict

"""Selection Manager - Gerenciamento headless de seleção de clientes.

MS-17: Responsável por representar e manipular a seleção de clientes
de forma desacoplada da UI (sem dependências de Tkinter).

Responsabilidades:
- Manter o universo de clientes disponíveis (ClienteRow)
- Representar qual subconjunto está selecionado (via IDs)
- Fornecer operações utilitárias:
  - Obter IDs selecionados (como strings ou ints)
  - Obter ClienteRow selecionados
  - Contar seleção
  - Validar se há seleção

A MainScreenFrame continua responsável por:
- Ler seleção da Treeview (self.client_list.selection())
- Alimentar o SelectionManager com esses IDs
- Consultar o manager para operações de negócio
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Sequence

from src.modules.clientes.viewmodel import ClienteRow


@dataclass(frozen=True)
class SelectionSnapshot:
    """Representa um snapshot imutável da seleção atual.

    Atributos:
        selected_ids: Conjunto de IDs selecionados (como strings vindas da Treeview).
        all_clients: Sequência de todos os clientes disponíveis (ClienteRow).
    """

    selected_ids: frozenset[str]
    all_clients: Sequence[ClienteRow]

    @property
    def count(self) -> int:
        """Retorna quantidade de itens selecionados."""
        return len(self.selected_ids)

    @property
    def has_selection(self) -> bool:
        """Retorna True se há pelo menos um item selecionado."""
        return self.count > 0


class SelectionManager:
    """Gerencia a seleção de clientes de forma headless (sem UI).

    MS-17: Extrai a lógica de seleção da MainScreenFrame, permitindo
    que a View apenas consulte a Treeview e delegue ao manager.

    Exemplo de uso:
        # Na MainScreenFrame, após carregar clientes:
        manager = SelectionManager(all_clients=self._current_rows)

        # Ao precisar consultar seleção:
        tree_ids = self.client_list.selection()  # lista de strings
        snapshot = manager.build_snapshot(tree_ids)

        # Usar snapshot para operações:
        selected_rows = manager.get_selected_client_rows(snapshot)
        selected_ids_int = manager.get_selected_client_ids_as_int(snapshot)
    """

    def __init__(self, *, all_clients: Sequence[ClienteRow]) -> None:
        """Inicializa o SelectionManager com o universo de clientes.

        Args:
            all_clients: Sequência de todos os clientes disponíveis (ClienteRow).
                        Geralmente vem de MainScreenFrame._current_rows ou
                        da ViewModel após filtros/ordenação.
        """
        self._all_clients = list(all_clients)

        # Criar mapa rápido de ID (string) -> ClienteRow
        # O ID na Treeview é str(cliente.id), então precisamos indexar por isso
        self._id_to_row: dict[str, ClienteRow] = {str(client.id): client for client in self._all_clients}

    def build_snapshot(self, selected_ids: Collection[str]) -> SelectionSnapshot:
        """Constrói um snapshot imutável da seleção atual.

        Args:
            selected_ids: Coleção de IDs selecionados (strings vindas da Treeview).
                         Geralmente obtido via self.client_list.selection().

        Returns:
            SelectionSnapshot com os IDs selecionados e todos os clientes.
        """
        return SelectionSnapshot(
            selected_ids=frozenset(selected_ids),
            all_clients=self._all_clients,
        )

    def get_selected_client_rows(self, snapshot: SelectionSnapshot) -> list[ClienteRow]:
        """Retorna lista de ClienteRow correspondentes aos IDs selecionados.

        Args:
            snapshot: Snapshot da seleção atual.

        Returns:
            Lista de ClienteRow selecionados (na ordem original dos clientes).
            Lista vazia se nenhum selecionado ou se IDs não forem encontrados.
        """
        selected_rows: list[ClienteRow] = []

        for client_id_str in snapshot.selected_ids:
            row = self._id_to_row.get(client_id_str)
            if row is not None:
                selected_rows.append(row)

        return selected_rows

    def get_selected_client_ids_as_int(self, snapshot: SelectionSnapshot) -> list[int]:
        """Retorna lista de IDs de clientes selecionados como inteiros.

        Args:
            snapshot: Snapshot da seleção atual.

        Returns:
            Lista de IDs como inteiros (conversão de ClienteRow.id).
            IDs que não puderem ser convertidos são ignorados.
        """
        ids_as_int: list[int] = []

        for client_id_str in snapshot.selected_ids:
            row = self._id_to_row.get(client_id_str)
            if row is not None:
                try:
                    # ClienteRow.id é str, precisamos converter para int
                    ids_as_int.append(int(row.id))
                except (ValueError, TypeError):
                    # Ignorar IDs que não são numéricos
                    pass

        return ids_as_int

    def get_selected_ids_as_set(self, snapshot: SelectionSnapshot) -> set[str]:
        """Retorna conjunto de IDs selecionados como strings.

        Args:
            snapshot: Snapshot da seleção atual.

        Returns:
            Set de IDs selecionados (strings).
            Compatível com a semântica antiga de _get_selected_ids().
        """
        return set(snapshot.selected_ids)

    def update_all_clients(self, all_clients: Sequence[ClienteRow]) -> None:
        """Atualiza o universo de clientes disponíveis.

        Args:
            all_clients: Nova sequência de todos os clientes.
                        Deve ser chamado quando a lista de clientes muda
                        (após carregar, filtrar, ordenar, etc.).
        """
        self._all_clients = list(all_clients)
        self._id_to_row = {str(client.id): client for client in self._all_clients}
