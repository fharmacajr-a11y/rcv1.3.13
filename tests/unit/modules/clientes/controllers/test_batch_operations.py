# -*- coding: utf-8 -*-
"""Testes unitários para BatchOperationsCoordinator.

Este módulo testa o coordenador de operações em lote (delete, restore, export)
sem depender de Tkinter real, usando mocks para o ViewModel e as dependências.

Cobertura esperada: >= 90% do arquivo batch_operations.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.clientes.controllers.batch_operations import (
    BatchOperationResult,
    BatchOperationsCoordinator,
    BatchValidationResult,
)


@pytest.fixture
def mock_vm() -> MagicMock:
    """Cria um mock do ClientesViewModel."""
    vm = MagicMock()
    vm.delete_clientes_batch = MagicMock(return_value=(2, []))
    vm.restore_clientes_batch = MagicMock()
    vm.export_clientes_batch = MagicMock()
    return vm


@pytest.fixture
def coordinator(mock_vm: MagicMock) -> BatchOperationsCoordinator:
    """Cria uma instância do BatchOperationsCoordinator com ViewModel mockado."""
    return BatchOperationsCoordinator(vm=mock_vm)


# ============================================================================
# TESTES DE DATA STRUCTURES
# ============================================================================


class TestBatchOperationResult:
    """Testes da estrutura BatchOperationResult."""

    def test_has_errors_false_quando_sem_erros(self) -> None:
        """has_errors deve retornar False quando lista de erros vazia."""
        result = BatchOperationResult(
            success_count=5,
            errors=[],
            operation_type="delete",
            total_selected=5,
        )
        assert result.has_errors is False

    def test_has_errors_true_quando_com_erros(self) -> None:
        """has_errors deve retornar True quando há erros na lista."""
        result = BatchOperationResult(
            success_count=3,
            errors=[("1", "Erro X"), ("2", "Erro Y")],
            operation_type="delete",
            total_selected=5,
        )
        assert result.has_errors is True

    def test_is_partial_success_quando_alguns_ok_alguns_falharam(self) -> None:
        """is_partial_success deve ser True quando há sucesso parcial."""
        result = BatchOperationResult(
            success_count=3,
            errors=[("4", "Erro"), ("5", "Erro")],
            operation_type="restore",
            total_selected=5,
        )
        assert result.is_partial_success is True
        assert result.is_complete_success is False
        assert result.is_complete_failure is False

    def test_is_complete_success_quando_todos_ok(self) -> None:
        """is_complete_success deve ser True quando todos itens processados sem erro."""
        result = BatchOperationResult(
            success_count=5,
            errors=[],
            operation_type="export",
            total_selected=5,
        )
        assert result.is_complete_success is True
        assert result.is_partial_success is False
        assert result.is_complete_failure is False

    def test_is_complete_failure_quando_todos_falharam(self) -> None:
        """is_complete_failure deve ser True quando nenhum item foi processado."""
        result = BatchOperationResult(
            success_count=0,
            errors=[("1", "Erro"), ("2", "Erro"), ("3", "Erro")],
            operation_type="delete",
            total_selected=3,
        )
        assert result.is_complete_failure is True
        assert result.is_partial_success is False
        assert result.is_complete_success is False

    def test_is_complete_failure_false_quando_sem_erros(self) -> None:
        """is_complete_failure deve ser False quando não há erros."""
        result = BatchOperationResult(
            success_count=2,
            errors=[],
            operation_type="delete",
            total_selected=2,
        )
        assert result.is_complete_failure is False


class TestBatchValidationResult:
    """Testes da estrutura BatchValidationResult."""

    def test_validation_result_valido(self) -> None:
        """Resultado de validação válido deve ter is_valid=True."""
        result = BatchValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.reason == ""

    def test_validation_result_invalido_com_motivo(self) -> None:
        """Resultado de validação inválido deve ter motivo."""
        result = BatchValidationResult(is_valid=False, reason="Sem conexão")
        assert result.is_valid is False
        assert result.reason == "Sem conexão"


# ============================================================================
# TESTES DE INICIALIZAÇÃO
# ============================================================================


class TestBatchOperationsCoordinatorInit:
    """Testes de inicialização do BatchOperationsCoordinator."""

    def test_coordinator_criado_com_viewmodel(self, mock_vm: MagicMock) -> None:
        """Coordinator deve ser criado com referência ao ViewModel."""
        coord = BatchOperationsCoordinator(vm=mock_vm)
        assert coord._vm is mock_vm


# ============================================================================
# TESTES DE DELETE BATCH
# ============================================================================


class TestBatchOperationsCoordinatorDeleteValidation:
    """Testes de validação de exclusão em lote."""

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_delete")
    def test_validate_delete_valido_quando_conditions_ok(
        self,
        mock_can_delete: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_delete deve retornar válido quando condições atendidas."""
        mock_can_delete.return_value = True
        selected = ["1", "2", "3"]

        result = coordinator.validate_delete(
            selected,
            is_trash_screen=False,
            is_online=True,
        )

        assert result.is_valid is True
        assert result.reason == ""
        mock_can_delete.assert_called_once_with(
            selected,
            is_trash_screen=False,
            is_online=True,
            max_items=None,
        )

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_delete")
    def test_validate_delete_invalido_quando_nenhum_selecionado(
        self,
        mock_can_delete: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_delete deve retornar inválido quando lista vazia."""
        result = coordinator.validate_delete(
            [],
            is_trash_screen=False,
            is_online=True,
        )

        assert result.is_valid is False
        assert result.reason == "Nenhum cliente selecionado"
        mock_can_delete.assert_not_called()

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_delete")
    def test_validate_delete_invalido_quando_can_batch_delete_false(
        self,
        mock_can_delete: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_delete deve retornar inválido quando helper retorna False."""
        mock_can_delete.return_value = False
        selected = ["1", "2"]

        result = coordinator.validate_delete(
            selected,
            is_trash_screen=False,
            is_online=False,
        )

        assert result.is_valid is False
        assert "exclusão em lote não está disponível" in result.reason

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_delete")
    def test_validate_delete_com_max_items(
        self,
        mock_can_delete: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_delete deve passar max_items para o helper."""
        mock_can_delete.return_value = True
        selected = ["1", "2"]

        result = coordinator.validate_delete(
            selected,
            is_trash_screen=True,
            is_online=True,
            max_items=10,
        )

        assert result.is_valid is True
        mock_can_delete.assert_called_once_with(
            selected,
            is_trash_screen=True,
            is_online=True,
            max_items=10,
        )


class TestBatchOperationsCoordinatorDeleteExecution:
    """Testes de execução de exclusão em lote."""

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_delete_sucesso_completo(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_delete deve retornar sucesso quando todos itens processados."""
        mock_count.return_value = 3
        mock_vm.delete_clientes_batch.return_value = (3, [])
        selected = ["1", "2", "3"]

        result = coordinator.execute_delete(selected)

        assert result.success_count == 3
        assert result.errors == []
        assert result.operation_type == "delete"
        assert result.total_selected == 3
        assert result.is_complete_success is True
        mock_vm.delete_clientes_batch.assert_called_once_with(selected)

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_delete_sucesso_parcial(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_delete deve retornar sucesso parcial quando alguns itens falharam."""
        mock_count.return_value = 5
        # Retorna 3 sucessos e 2 erros (id, msg)
        mock_vm.delete_clientes_batch.return_value = (
            3,
            [(4, "Erro ao deletar"), (5, "Erro ao deletar")],
        )
        selected = ["1", "2", "3", "4", "5"]

        result = coordinator.execute_delete(selected)

        assert result.success_count == 3
        assert len(result.errors) == 2
        assert result.errors == [("4", "Erro ao deletar"), ("5", "Erro ao deletar")]
        assert result.is_partial_success is True

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_delete_falha_completa_exception(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_delete deve retornar falha completa quando exceção lançada."""
        mock_count.return_value = 2
        mock_vm.delete_clientes_batch.side_effect = RuntimeError("Erro de conexão")
        selected = ["1", "2"]

        result = coordinator.execute_delete(selected)

        assert result.success_count == 0
        assert len(result.errors) == 1
        assert result.errors[0][0] == "*"
        assert "Erro geral" in result.errors[0][1]
        assert "Erro de conexão" in result.errors[0][1]
        assert result.is_complete_failure is True


# ============================================================================
# TESTES DE RESTORE BATCH
# ============================================================================


class TestBatchOperationsCoordinatorRestoreValidation:
    """Testes de validação de restauração em lote."""

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_restore")
    def test_validate_restore_valido_quando_conditions_ok(
        self,
        mock_can_restore: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_restore deve retornar válido quando condições atendidas."""
        mock_can_restore.return_value = True
        selected = ["1", "2"]

        result = coordinator.validate_restore(
            selected,
            is_trash_screen=True,
            is_online=True,
        )

        assert result.is_valid is True
        assert result.reason == ""
        mock_can_restore.assert_called_once_with(
            selected,
            is_trash_screen=True,
            is_online=True,
        )

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_restore")
    def test_validate_restore_invalido_quando_nenhum_selecionado(
        self,
        mock_can_restore: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_restore deve retornar inválido quando lista vazia."""
        result = coordinator.validate_restore(
            [],
            is_trash_screen=True,
            is_online=True,
        )

        assert result.is_valid is False
        assert result.reason == "Nenhum cliente selecionado"
        mock_can_restore.assert_not_called()

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_restore")
    def test_validate_restore_invalido_quando_can_batch_restore_false(
        self,
        mock_can_restore: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_restore deve retornar inválido quando helper retorna False."""
        mock_can_restore.return_value = False
        selected = ["1", "2"]

        result = coordinator.validate_restore(
            selected,
            is_trash_screen=False,
            is_online=True,
        )

        assert result.is_valid is False
        assert "restauração em lote não está disponível" in result.reason


class TestBatchOperationsCoordinatorRestoreExecution:
    """Testes de execução de restauração em lote."""

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_restore_sucesso_completo(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_restore deve retornar sucesso quando todos itens restaurados."""
        mock_count.return_value = 2
        selected = ["1", "2"]

        result = coordinator.execute_restore(selected)

        assert result.success_count == 2
        assert result.errors == []
        assert result.operation_type == "restore"
        assert result.total_selected == 2
        assert result.is_complete_success is True
        mock_vm.restore_clientes_batch.assert_called_once_with(selected)

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_restore_falha_completa_exception(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_restore deve retornar falha completa quando exceção lançada."""
        mock_count.return_value = 3
        mock_vm.restore_clientes_batch.side_effect = ValueError("Erro DB")
        selected = ["1", "2", "3"]

        result = coordinator.execute_restore(selected)

        assert result.success_count == 0
        assert len(result.errors) == 1
        assert result.errors[0][0] == "*"
        assert "Erro geral" in result.errors[0][1]
        assert "Erro DB" in result.errors[0][1]
        assert result.is_complete_failure is True


# ============================================================================
# TESTES DE EXPORT BATCH
# ============================================================================


class TestBatchOperationsCoordinatorExportValidation:
    """Testes de validação de exportação em lote."""

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_export")
    def test_validate_export_valido_quando_conditions_ok(
        self,
        mock_can_export: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_export deve retornar válido quando condições atendidas."""
        mock_can_export.return_value = True
        selected = ["1", "2", "3", "4"]

        result = coordinator.validate_export(selected)

        assert result.is_valid is True
        assert result.reason == ""
        mock_can_export.assert_called_once_with(selected, max_items=None)

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_export")
    def test_validate_export_invalido_quando_nenhum_selecionado(
        self,
        mock_can_export: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_export deve retornar inválido quando lista vazia."""
        result = coordinator.validate_export([])

        assert result.is_valid is False
        assert result.reason == "Nenhum cliente selecionado"
        mock_can_export.assert_not_called()

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_export")
    def test_validate_export_invalido_quando_can_batch_export_false(
        self,
        mock_can_export: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_export deve retornar inválido quando helper retorna False."""
        mock_can_export.return_value = False
        selected = ["1", "2", "3"]

        result = coordinator.validate_export(selected, max_items=2)

        assert result.is_valid is False
        assert "exportação em lote não está disponível" in result.reason

    @patch("src.modules.clientes.controllers.batch_operations.can_batch_export")
    def test_validate_export_com_max_items(
        self,
        mock_can_export: MagicMock,
        coordinator: BatchOperationsCoordinator,
    ) -> None:
        """validate_export deve passar max_items para o helper."""
        mock_can_export.return_value = True
        selected = ["1", "2", "3"]

        result = coordinator.validate_export(selected, max_items=5)

        assert result.is_valid is True
        mock_can_export.assert_called_once_with(selected, max_items=5)


class TestBatchOperationsCoordinatorExportExecution:
    """Testes de execução de exportação em lote."""

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_export_sucesso_completo(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_export deve retornar sucesso quando todos itens exportados."""
        mock_count.return_value = 4
        selected = ["1", "2", "3", "4"]

        result = coordinator.execute_export(selected)

        assert result.success_count == 4
        assert result.errors == []
        assert result.operation_type == "export"
        assert result.total_selected == 4
        assert result.is_complete_success is True
        mock_vm.export_clientes_batch.assert_called_once_with(selected)

    @patch("src.modules.clientes.controllers.batch_operations.get_selection_count")
    def test_execute_export_falha_completa_exception(
        self,
        mock_count: MagicMock,
        coordinator: BatchOperationsCoordinator,
        mock_vm: MagicMock,
    ) -> None:
        """execute_export deve retornar falha completa quando exceção lançada."""
        mock_count.return_value = 2
        mock_vm.export_clientes_batch.side_effect = IOError("Erro ao salvar arquivo")
        selected = ["1", "2"]

        result = coordinator.execute_export(selected)

        assert result.success_count == 0
        assert len(result.errors) == 1
        assert result.errors[0][0] == "*"
        assert "Erro geral" in result.errors[0][1]
        assert "Erro ao salvar arquivo" in result.errors[0][1]
        assert result.is_complete_failure is True
