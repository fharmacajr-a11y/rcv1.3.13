# -*- coding: utf-8 -*-
"""Column Manager headless para gerenciamento de colunas da Treeview.

FASE MS-15: Extração da lógica de gerenciamento de colunas da God Class MainScreenFrame.

Este módulo concentra a lógica de "como gerenciar ordem/visibilidade/persistência de colunas"
sem dependências de Tkinter/UI.

Responsabilidades:
- Manter ordem das colunas
- Gerenciar estado de visibilidade de cada coluna
- Garantir regras de negócio (ex.: pelo menos uma coluna visível)
- Fornecer interface para carregar/salvar preferências

NÃO faz:
- Manipular widgets Tkinter (BooleanVar, Checkbutton, etc)
- Renderizar UI
- Acessar diretamente arquivos de preferências (usa injeção de dependência)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass(frozen=True)
class ColumnConfig:
    """Configuração de uma coluna individual.

    Attributes:
        name: Nome da coluna (ex.: "ID", "Razao Social")
        visible: Estado atual de visibilidade
        mandatory: Se True, não pode ser ocultada (sempre visível)
    """

    name: str
    visible: bool
    mandatory: bool = False


@dataclass(frozen=True)
class ColumnManagerState:
    """Estado completo do gerenciador de colunas.

    Esta estrutura é retornada após operações de mutação (toggle, set_visibility)
    para que a UI possa sincronizar seus widgets.

    Attributes:
        order: Lista ordenada de nomes de colunas
        visibility: Mapeamento coluna → visível
    """

    order: tuple[str, ...]
    visibility: dict[str, bool]


# ============================================================================
# VALIDATION RESULT
# ============================================================================


@dataclass(frozen=True)
class VisibilityValidationResult:
    """Resultado de validação de mudança de visibilidade.

    Attributes:
        is_valid: Se a mudança é permitida
        reason: Mensagem explicativa (se is_valid=False)
        suggested_state: Estado sugerido após aplicar regras
    """

    is_valid: bool
    reason: str = ""
    suggested_state: dict[str, bool] | None = None


# ============================================================================
# COLUMN MANAGER
# ============================================================================


class ColumnManager:
    """Gerenciador headless de colunas para Treeview.

    Responsável por:
    - Manter ordem e visibilidade de colunas
    - Aplicar regras de negócio (ex.: mínimo 1 coluna visível)
    - Validar mudanças de estado
    - Interface para persistência (via callbacks)

    Não gerencia:
    - Widgets Tkinter
    - Arquivos de preferências diretamente
    - Renderização de UI

    Examples:
        >>> columns = ["ID", "Nome", "CNPJ"]
        >>> initial_visibility = {"ID": True, "Nome": True, "CNPJ": False}
        >>> manager = ColumnManager(columns, initial_visibility)
        >>> state = manager.get_state()
        >>> state.order
        ('ID', 'Nome', 'CNPJ')
        >>> state.visibility["Nome"]
        True
    """

    def __init__(
        self,
        initial_order: Sequence[str],
        initial_visibility: Mapping[str, bool] | None = None,
        mandatory_columns: set[str] | None = None,
    ) -> None:
        """Inicializa o gerenciador de colunas.

        Args:
            initial_order: Ordem inicial das colunas
            initial_visibility: Visibilidade inicial (default: todas visíveis)
            mandatory_columns: Conjunto de colunas obrigatórias (não podem ser ocultadas)

        Examples:
            >>> manager = ColumnManager(
            ...     initial_order=["ID", "Nome"],
            ...     initial_visibility={"ID": True, "Nome": False},
            ...     mandatory_columns={"ID"}
            ... )
        """
        self._order: tuple[str, ...] = tuple(initial_order)
        self._mandatory: set[str] = mandatory_columns or set()

        # Inicializar visibilidade
        if initial_visibility is None:
            self._visibility: dict[str, bool] = {col: True for col in self._order}
        else:
            self._visibility: dict[str, bool] = dict(initial_visibility)
            # Garantir que todas as colunas têm entrada
            for col in self._order:
                if col not in self._visibility:
                    self._visibility[col] = True

        # Aplicar regra: colunas obrigatórias sempre visíveis
        for col in self._mandatory:
            if col in self._visibility:
                self._visibility[col] = True

        # Aplicar regra: pelo menos uma coluna visível
        self._ensure_at_least_one_visible()

    def _ensure_at_least_one_visible(self) -> None:
        """Garante que pelo menos uma coluna esteja visível.

        Se todas estiverem ocultas, torna a primeira visível.
        """
        if not any(self._visibility.values()):
            # Nenhuma visível, tornar primeira visível
            if self._order:
                self._visibility[self._order[0]] = True

    def get_state(self) -> ColumnManagerState:
        """Retorna estado atual do gerenciador.

        Returns:
            ColumnManagerState com ordem e visibilidade atuais

        Examples:
            >>> manager = ColumnManager(["ID", "Nome"])
            >>> state = manager.get_state()
            >>> isinstance(state, ColumnManagerState)
            True
        """
        return ColumnManagerState(
            order=self._order,
            visibility=dict(self._visibility),  # cópia defensiva
        )

    def validate_visibility_change(
        self,
        column: str,
        new_visibility: bool,
    ) -> VisibilityValidationResult:
        """Valida uma mudança de visibilidade antes de aplicá-la.

        Args:
            column: Nome da coluna a modificar
            new_visibility: Nova visibilidade desejada

        Returns:
            VisibilityValidationResult indicando se mudança é válida

        Examples:
            >>> manager = ColumnManager(["ID"], mandatory_columns={"ID"})
            >>> result = manager.validate_visibility_change("ID", False)
            >>> result.is_valid
            False
            >>> "obrigatória" in result.reason.lower()
            True
        """
        # Regra 1: Coluna deve existir
        if column not in self._visibility:
            return VisibilityValidationResult(
                is_valid=False,
                reason=f"Coluna '{column}' não existe na configuração.",
            )

        # Regra 2: Colunas obrigatórias não podem ser ocultadas
        if column in self._mandatory and not new_visibility:
            return VisibilityValidationResult(
                is_valid=False,
                reason=f"Coluna '{column}' é obrigatória e não pode ser ocultada.",
            )

        # Regra 3: Pelo menos uma coluna deve estar visível
        if not new_visibility:
            # Simular mudança
            temp_visibility = dict(self._visibility)
            temp_visibility[column] = False

            if not any(temp_visibility.values()):
                return VisibilityValidationResult(
                    is_valid=False,
                    reason="Pelo menos uma coluna deve permanecer visível.",
                    suggested_state=self._visibility.copy(),  # manter estado atual
                )

        # Mudança válida
        return VisibilityValidationResult(is_valid=True)

    def set_visibility(
        self,
        column: str,
        visible: bool,
    ) -> ColumnManagerState:
        """Define visibilidade de uma coluna.

        Aplica regras de validação antes de modificar.
        Se a mudança for inválida, retorna estado atual inalterado.

        Args:
            column: Nome da coluna
            visible: Nova visibilidade

        Returns:
            ColumnManagerState após a mudança (ou inalterado se inválida)

        Examples:
            >>> manager = ColumnManager(["ID", "Nome"])
            >>> state = manager.set_visibility("Nome", False)
            >>> state.visibility["Nome"]
            False
        """
        validation = self.validate_visibility_change(column, visible)

        if not validation.is_valid:
            # Mudança inválida, retornar estado atual
            return self.get_state()

        # Aplicar mudança
        self._visibility[column] = visible

        return self.get_state()

    def toggle(self, column: str) -> ColumnManagerState:
        """Alterna visibilidade de uma coluna (show ↔ hide).

        Args:
            column: Nome da coluna a alternar

        Returns:
            ColumnManagerState após o toggle

        Examples:
            >>> manager = ColumnManager(["ID", "Nome"])
            >>> state = manager.toggle("Nome")
            >>> # Se estava visível, agora está oculta (se regras permitirem)
        """
        if column not in self._visibility:
            return self.get_state()

        current = self._visibility[column]
        return self.set_visibility(column, not current)

    def get_configs(self) -> list[ColumnConfig]:
        """Retorna configuração detalhada de todas as colunas.

        Returns:
            Lista de ColumnConfig com nome, visibilidade e obrigatoriedade

        Examples:
            >>> manager = ColumnManager(["ID"], mandatory_columns={"ID"})
            >>> configs = manager.get_configs()
            >>> configs[0].name
            'ID'
            >>> configs[0].mandatory
            True
        """
        return [
            ColumnConfig(
                name=col,
                visible=self._visibility[col],
                mandatory=col in self._mandatory,
            )
            for col in self._order
        ]

    def load_from_prefs(
        self,
        loader: Callable[[str], dict[str, bool]],
        user_key: str,
    ) -> ColumnManagerState:
        """Carrega visibilidade de preferências usando callback fornecido.

        Args:
            loader: Função que recebe user_key e retorna dict[str, bool]
            user_key: Chave do usuário (ex.: email)

        Returns:
            ColumnManagerState após carregar preferências

        Examples:
            >>> def mock_loader(key: str) -> dict[str, bool]:
            ...     return {"ID": True, "Nome": False}
            >>> manager = ColumnManager(["ID", "Nome"])
            >>> state = manager.load_from_prefs(mock_loader, "user@example.com")
            >>> state.visibility["Nome"]
            False
        """
        try:
            prefs = loader(user_key)

            # Aplicar preferências carregadas
            for col in self._order:
                if col in prefs:
                    # Validar antes de aplicar
                    validation = self.validate_visibility_change(col, prefs[col])
                    if validation.is_valid:
                        self._visibility[col] = prefs[col]

            # Garantir regras após carregar
            self._ensure_at_least_one_visible()

            return self.get_state()

        except Exception:
            # Em caso de erro, manter estado atual
            return self.get_state()

    def save_to_prefs(
        self,
        saver: Callable[[str, dict[str, bool]], None],
        user_key: str,
    ) -> None:
        """Salva visibilidade atual em preferências usando callback fornecido.

        Args:
            saver: Função que recebe (user_key, visibility_dict)
            user_key: Chave do usuário (ex.: email)

        Examples:
            >>> saved_data = {}
            >>> def mock_saver(key: str, data: dict[str, bool]) -> None:
            ...     saved_data[key] = data
            >>> manager = ColumnManager(["ID", "Nome"])
            >>> manager.save_to_prefs(mock_saver, "user@example.com")
            >>> saved_data["user@example.com"]["ID"]
            True
        """
        try:
            saver(user_key, dict(self._visibility))
        except Exception:
            # Falha silenciosa (logging seria responsabilidade da UI)
            pass

    def get_visible_columns(self) -> list[str]:
        """Retorna lista de colunas atualmente visíveis.

        Returns:
            Lista de nomes de colunas visíveis, na ordem original

        Examples:
            >>> manager = ColumnManager(
            ...     ["ID", "Nome", "CNPJ"],
            ...     {"ID": True, "Nome": False, "CNPJ": True}
            ... )
            >>> manager.get_visible_columns()
            ['ID', 'CNPJ']
        """
        return [col for col in self._order if self._visibility[col]]

    def get_hidden_columns(self) -> list[str]:
        """Retorna lista de colunas atualmente ocultas.

        Returns:
            Lista de nomes de colunas ocultas

        Examples:
            >>> manager = ColumnManager(
            ...     ["ID", "Nome", "CNPJ"],
            ...     {"ID": True, "Nome": False, "CNPJ": True}
            ... )
            >>> manager.get_hidden_columns()
            ['Nome']
        """
        return [col for col in self._order if not self._visibility[col]]

    def build_visibility_map_for_rendering(self) -> dict[str, bool]:
        """Retorna mapa de visibilidade pronto para rendering_adapter.

        Este método facilita integração com build_rendering_context_from_ui.

        Returns:
            Cópia do dicionário de visibilidade

        Examples:
            >>> manager = ColumnManager(["ID", "Nome"])
            >>> vis_map = manager.build_visibility_map_for_rendering()
            >>> vis_map["ID"]
            True
        """
        return dict(self._visibility)

    def sync_to_ui_vars(self, ui_vars: dict[str, Any]) -> None:
        """Sincroniza estado do ColumnManager para variáveis de UI (BooleanVar).

        Helper para atualizar tk.BooleanVar após mudanças no ColumnManager.

        Args:
            ui_vars: Dict de coluna → BooleanVar (ou qualquer objeto com .set())

        Examples:
            >>> from unittest.mock import Mock
            >>> var_id = Mock()
            >>> var_nome = Mock()
            >>> ui_vars = {"ID": var_id, "Nome": var_nome}
            >>> manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
            >>> manager.sync_to_ui_vars(ui_vars)
            >>> var_id.set.assert_called_once_with(True)
            >>> var_nome.set.assert_called_once_with(False)
        """
        for col in self._order:
            if col in ui_vars:
                ui_vars[col].set(self._visibility[col])
