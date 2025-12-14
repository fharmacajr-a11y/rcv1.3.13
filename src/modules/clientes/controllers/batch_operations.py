# -*- coding: utf-8 -*-
"""Coordenador headless de batch operations para clientes.

FASE MS-13: Extração da lógica de batch operations da God Class MainScreenFrame.

Este módulo concentra a lógica de negócio para operações em lote (exclusão,
restauração, exportação) sem dependências de Tkinter/UI.

Responsabilidades:
- Validar pré-condições para batch operations (via helpers puros)
- Executar operações em lote delegando ao ViewModel
- Retornar resultados estruturados para a UI consumir

NÃO faz:
- Mostrar messageboxes (responsabilidade da UI)
- Recarregar listas (responsabilidade da UI)
- Manipular widgets Tkinter
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from src.modules.clientes.views.main_screen_helpers import (
    can_batch_delete,
    can_batch_export,
    can_batch_restore,
    get_selection_count,
)

if TYPE_CHECKING:
    from src.modules.clientes.viewmodel import ClientesViewModel

log = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class BatchOperationResult:
    """Resultado de uma operação em lote.

    Attributes:
        success_count: Quantidade de itens processados com sucesso
        errors: Lista de erros (id, mensagem) para itens que falharam
        operation_type: Tipo de operação realizada
        total_selected: Total de itens selecionados para a operação
    """

    success_count: int
    errors: list[tuple[str, str]]  # (id, error_message)
    operation_type: Literal["delete", "restore", "export"]
    total_selected: int

    @property
    def has_errors(self) -> bool:
        """Indica se houve algum erro durante a operação."""
        return len(self.errors) > 0

    @property
    def is_partial_success(self) -> bool:
        """Indica se houve sucesso parcial (alguns ok, alguns falharam)."""
        return self.success_count > 0 and self.has_errors

    @property
    def is_complete_success(self) -> bool:
        """Indica se todos os itens foram processados com sucesso."""
        return self.success_count == self.total_selected and not self.has_errors

    @property
    def is_complete_failure(self) -> bool:
        """Indica se todos os itens falharam."""
        return self.success_count == 0 and self.has_errors


@dataclass
class BatchValidationResult:
    """Resultado da validação de uma operação em lote.

    Attributes:
        is_valid: Se a operação pode prosseguir
        reason: Motivo da invalidação (se is_valid=False)
    """

    is_valid: bool
    reason: str = ""


# ============================================================================
# COORDINATOR
# ============================================================================


class BatchOperationsCoordinator:
    """Coordena operações em lote de clientes (delete, restore, export).

    Este coordenador é headless (sem UI) e delega operações ao ViewModel,
    usando helpers puros para validação de pré-condições.

    Args:
        vm: ViewModel de clientes que executa as operações reais
    """

    def __init__(self, vm: ClientesViewModel) -> None:
        """Inicializa o coordenador com o ViewModel de clientes.

        Args:
            vm: ViewModel que será usado para executar as operações
        """
        self._vm = vm

    # ========================================================================
    # DELETE BATCH
    # ========================================================================

    def validate_delete(
        self,
        selected_ids: Collection[str],
        *,
        is_trash_screen: bool,
        is_online: bool,
        max_items: int | None = None,
    ) -> BatchValidationResult:
        """Valida se a exclusão em lote pode ser executada.

        Args:
            selected_ids: IDs dos clientes selecionados
            is_trash_screen: Se está na tela de lixeira
            is_online: Se está conectado ao Supabase
            max_items: Limite máximo de itens (None = sem limite)

        Returns:
            Resultado da validação com motivo se inválido
        """
        if not selected_ids:
            return BatchValidationResult(
                is_valid=False,
                reason="Nenhum cliente selecionado",
            )

        if not can_batch_delete(
            selected_ids,
            is_trash_screen=is_trash_screen,
            is_online=is_online,
            max_items=max_items,
        ):
            return BatchValidationResult(
                is_valid=False,
                reason=(
                    "A exclusão em lote não está disponível no momento.\n"
                    "Verifique sua conexão ou se há clientes selecionados."
                ),
            )

        return BatchValidationResult(is_valid=True)

    def execute_delete(
        self,
        selected_ids: Collection[str],
    ) -> BatchOperationResult:
        """Executa exclusão em lote de clientes.

        Args:
            selected_ids: IDs dos clientes a excluir

        Returns:
            Resultado da operação com contagem de sucesso e erros
        """
        total = get_selection_count(selected_ids)

        try:
            # Delega ao ViewModel que chama o serviço
            ok_count, errors = self._vm.delete_clientes_batch(selected_ids)

            # Converte erros de (int, str) para (str, str)
            errors_str = [(str(cid), msg) for cid, msg in errors]

            log.info(
                "Batch delete executado: %d/%d sucesso, %d erros",
                ok_count,
                total,
                len(errors_str),
            )

            return BatchOperationResult(
                success_count=ok_count,
                errors=errors_str,
                operation_type="delete",
                total_selected=total,
            )

        except Exception as exc:
            log.exception("Erro ao executar batch delete")
            # Se der erro geral, considera que todos falharam
            return BatchOperationResult(
                success_count=0,
                errors=[("*", f"Erro geral: {exc}")],
                operation_type="delete",
                total_selected=total,
            )

    # ========================================================================
    # RESTORE BATCH
    # ========================================================================

    def validate_restore(
        self,
        selected_ids: Collection[str],
        *,
        is_trash_screen: bool,
        is_online: bool,
    ) -> BatchValidationResult:
        """Valida se a restauração em lote pode ser executada.

        Args:
            selected_ids: IDs dos clientes selecionados
            is_trash_screen: Se está na tela de lixeira
            is_online: Se está conectado ao Supabase

        Returns:
            Resultado da validação com motivo se inválido
        """
        if not selected_ids:
            return BatchValidationResult(
                is_valid=False,
                reason="Nenhum cliente selecionado",
            )

        if not can_batch_restore(
            selected_ids,
            is_trash_screen=is_trash_screen,
            is_online=is_online,
        ):
            return BatchValidationResult(
                is_valid=False,
                reason=(
                    "A restauração em lote não está disponível nesta tela.\n"
                    "Use a tela de Lixeira para restaurar clientes."
                ),
            )

        return BatchValidationResult(is_valid=True)

    def execute_restore(
        self,
        selected_ids: Collection[str],
    ) -> BatchOperationResult:
        """Executa restauração em lote de clientes da lixeira.

        Args:
            selected_ids: IDs dos clientes a restaurar

        Returns:
            Resultado da operação
        """
        total = get_selection_count(selected_ids)

        try:
            # Delega ao ViewModel que chama o serviço
            self._vm.restore_clientes_batch(selected_ids)

            log.info("Batch restore executado: %d clientes restaurados", total)

            return BatchOperationResult(
                success_count=total,
                errors=[],
                operation_type="restore",
                total_selected=total,
            )

        except Exception as exc:
            log.exception("Erro ao executar batch restore")
            return BatchOperationResult(
                success_count=0,
                errors=[("*", f"Erro geral: {exc}")],
                operation_type="restore",
                total_selected=total,
            )

    # ========================================================================
    # EXPORT BATCH
    # ========================================================================

    def validate_export(
        self,
        selected_ids: Collection[str],
        *,
        max_items: int | None = None,
    ) -> BatchValidationResult:
        """Valida se a exportação em lote pode ser executada.

        Args:
            selected_ids: IDs dos clientes selecionados
            max_items: Limite máximo de itens (None = sem limite)

        Returns:
            Resultado da validação com motivo se inválido
        """
        if not selected_ids:
            return BatchValidationResult(
                is_valid=False,
                reason="Nenhum cliente selecionado",
            )

        if not can_batch_export(selected_ids, max_items=max_items):
            return BatchValidationResult(
                is_valid=False,
                reason=("A exportação em lote não está disponível no momento.\nVerifique se há clientes selecionados."),
            )

        return BatchValidationResult(is_valid=True)

    def execute_export(
        self,
        selected_ids: Collection[str],
    ) -> BatchOperationResult:
        """Executa exportação em lote de clientes.

        Args:
            selected_ids: IDs dos clientes a exportar

        Returns:
            Resultado da operação
        """
        total = get_selection_count(selected_ids)

        try:
            # Delega ao ViewModel (atualmente só loga)
            self._vm.export_clientes_batch(selected_ids)

            log.info("Batch export executado: %d clientes exportados", total)

            return BatchOperationResult(
                success_count=total,
                errors=[],
                operation_type="export",
                total_selected=total,
            )

        except Exception as exc:
            log.exception("Erro ao executar batch export")
            return BatchOperationResult(
                success_count=0,
                errors=[("*", f"Erro geral: {exc}")],
                operation_type="export",
                total_selected=total,
            )
