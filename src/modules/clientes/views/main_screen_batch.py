# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false, reportUntypedBaseClass=false, reportPrivateUsage=false

"""Main screen batch - Handlers de operações em lote.

Responsável por handlers de operações em lote (batch) da main screen.
"""

from __future__ import annotations

import logging
from tkinter import messagebox

from src.infra.supabase_client import get_supabase_state
from src.modules.clientes.views.main_screen_controller import (
    decide_batch_delete,
    decide_batch_export,
    decide_batch_restore,
)

log = logging.getLogger("app_gui")

__all__ = ["MainScreenBatchMixin"]


class MainScreenBatchMixin:
    """Mixin para operações em lote da main screen."""

    def _on_batch_delete_clicked(self) -> None:
        """Callback do botão 'Excluir em Lote' (implementação real)."""
        selected_ids = self._get_selected_ids()  # pyright: ignore[reportAttributeAccessIssue]
        supabase_state = get_supabase_state()
        is_online = supabase_state[0] == "online"

        decision = decide_batch_delete(
            selected_ids=selected_ids,
            is_trash_screen=False,
            is_online=is_online,
        )

        if decision.kind == "noop":
            return

        if decision.kind == "warning":
            messagebox.showwarning(
                "Operação não permitida",
                decision.message or "",
                parent=self,  # pyright: ignore[reportArgumentType]
            )
            return

        if decision.kind == "confirm":
            confirmed = messagebox.askyesno(
                "Excluir em Lote",
                decision.message or "",
                parent=self,  # pyright: ignore[reportArgumentType]
            )
            if not confirmed:
                return

        # Executar exclusão via coordenador
        def _delete_batch() -> None:
            result = self._batch_coordinator.execute_delete(selected_ids)  # pyright: ignore[reportAttributeAccessIssue]

            # Recarregar lista
            self.carregar()  # pyright: ignore[reportAttributeAccessIssue]

            # Feedback ao usuário baseado no resultado estruturado
            if result.is_complete_success:
                messagebox.showinfo(
                    "Sucesso",
                    f"{result.success_count} cliente(s) excluído(s) com sucesso!",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )
            elif result.is_partial_success:
                error_msg = "\n".join([f"ID {cid}: {msg}" for cid, msg in result.errors[:5]])
                if len(result.errors) > 5:
                    error_msg += f"\n... e mais {len(result.errors) - 5} erro(s)"

                messagebox.showwarning(
                    "Exclusão Parcial",
                    f"Excluídos: {result.success_count}/{result.total_selected}\n\nErros:\n{error_msg}",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )
            else:
                # Falha completa
                error_msg = result.errors[0][1] if result.errors else "Erro desconhecido"
                messagebox.showerror(
                    "Erro",
                    f"Falha ao excluir clientes em lote: {error_msg}",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )

        # Usar padrão de invocação segura
        self._invoke_safe(_delete_batch)  # pyright: ignore[reportAttributeAccessIssue]

    def _on_batch_restore_clicked(self) -> None:
        """Callback do botão 'Restaurar em Lote' (implementação real)."""
        selected_ids = self._get_selected_ids()  # pyright: ignore[reportAttributeAccessIssue]
        supabase_state = get_supabase_state()
        is_online = supabase_state[0] == "online"

        decision = decide_batch_restore(
            selected_ids=selected_ids,
            is_trash_screen=False,  # MainScreenFrame é lista principal
            is_online=is_online,
        )

        if decision.kind == "noop":
            return

        if decision.kind == "warning":
            messagebox.showwarning(
                "Operação não permitida",
                decision.message or "",
                parent=self,  # pyright: ignore[reportArgumentType]
            )
            return

        if decision.kind == "confirm":
            confirmed = messagebox.askyesno(
                "Restaurar em Lote",
                decision.message or "",
                parent=self,  # pyright: ignore[reportArgumentType]
            )
            if not confirmed:
                return

        # Executar restauração via coordenador
        def _restore_batch() -> None:
            result = self._batch_coordinator.execute_restore(selected_ids)  # pyright: ignore[reportAttributeAccessIssue]

            # Recarregar lista
            self.carregar()  # pyright: ignore[reportAttributeAccessIssue]

            # Feedback ao usuário baseado no resultado estruturado
            if result.is_complete_success:
                messagebox.showinfo(
                    "Sucesso",
                    f"{result.success_count} cliente(s) restaurado(s) com sucesso!",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )
            else:
                # Falha
                error_msg = result.errors[0][1] if result.errors else "Erro desconhecido"
                messagebox.showerror(
                    "Erro",
                    f"Falha ao restaurar clientes em lote: {error_msg}",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )

        # Usar padrão de invocação segura
        self._invoke_safe(_restore_batch)  # pyright: ignore[reportAttributeAccessIssue]

    def _on_batch_export_clicked(self) -> None:
        """Callback do botão 'Exportar em Lote' (implementação real).

        Nota: Export não precisa de confirmação (operação não destrutiva).
        """
        selected_ids = self._get_selected_ids()  # pyright: ignore[reportAttributeAccessIssue]
        decision = decide_batch_export(selected_ids=selected_ids)

        if decision.kind == "noop":
            return

        if decision.kind == "warning":
            messagebox.showwarning(
                "Operação não permitida",
                decision.message or "",
                parent=self,  # pyright: ignore[reportArgumentType]
            )
            return

        # Executar exportação via coordenador (sem confirmação - não destrutiva)
        def _export_batch() -> None:
            result = self._batch_coordinator.execute_export(selected_ids)  # pyright: ignore[reportAttributeAccessIssue]

            # Feedback ao usuário baseado no resultado estruturado
            if result.is_complete_success:
                messagebox.showinfo(
                    "Exportação",
                    f"Exportação de {result.success_count} cliente(s) iniciada.\n\n"
                    f"Nota: Funcionalidade em desenvolvimento.\n"
                    f"Os dados foram logados para processamento futuro.",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )
            else:
                # Falha
                error_msg = result.errors[0][1] if result.errors else "Erro desconhecido"
                messagebox.showerror(
                    "Erro",
                    f"Falha ao exportar clientes em lote: {error_msg}",
                    parent=self,  # pyright: ignore[reportArgumentType]
                )

        # Usar padrão de invocação segura
        self._invoke_safe(_export_batch)  # pyright: ignore[reportAttributeAccessIssue]
