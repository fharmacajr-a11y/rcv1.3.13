# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false

"""Main Screen Actions Controller.

Controller dedicado para extrair a lógica de alto nível dos botões principais
da MainScreenFrame (Novo, Editar, Excluir, Lixeira, Subpastas, Enviar, Obrigações).

Introduz ActionResult para estruturar retornos e separar decisões de UX.

Responsabilidades:
- Decidir **o que** fazer (ex.: se tem seleção, se pode editar, etc.)
- Retornar ActionResult com tipo de resultado e mensagem sugerida
- Agrupar regras de fluxo que hoje aparecem repetidas nos handlers de botões
- NÃO deve importar Tkinter diretamente (messagebox permanece na View)

A View (MainScreenFrame) continua responsável por:
- Interpretar ActionResult e mostrar messageboxes apropriadas
- Chamar carregar() quando necessário
- Chamar _update_main_buttons_state() após ações relevantes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol

if TYPE_CHECKING:
    from src.modules.clientes.viewmodel import ClientesViewModel
    from src.modules.clientes.controllers.batch_operations import BatchOperationsCoordinator
    from src.modules.clientes.controllers.selection_manager import SelectionManager

log = logging.getLogger("app_gui")


@dataclass(frozen=True)
class ActionResult:
    """Resultado estruturado de uma ação do controller.

    Permite que o controller decida o fluxo sem conhecer detalhes de UI (messageboxes).

    Attributes:
        kind: Tipo de resultado da ação
        message: Mensagem sugerida para o usuário (opcional)
        payload: Dados adicionais relevantes (opcional)
    """

    kind: Literal["ok", "no_selection", "no_callback", "error", "cancelled"]
    message: str | None = None
    payload: dict[str, Any] | None = None


class MainScreenActionsView(Protocol):
    """Protocolo que define a interface que a View deve fornecer ao controller."""

    def carregar(self) -> None:
        """Recarrega a lista de clientes."""
        ...

    def _update_main_buttons_state(self, *_: object) -> None:
        """Atualiza o estado dos botões principais."""
        ...


@dataclass
class MainScreenActions:
    """Controller de ações para os botões principais da MainScreen.

    Attributes:
        vm: ViewModel de clientes para operações de negócio
        batch: Coordenador de operações em lote
        selection: Manager de seleção para verificar estado atual
        view: Referência à View para callbacks essenciais
    """

    vm: ClientesViewModel
    batch: BatchOperationsCoordinator
    selection: SelectionManager
    view: MainScreenActionsView

    # Callbacks opcionais que a View pode fornecer
    on_new_callback: Callable[[], None] | None = None
    on_edit_callback: Callable[[], None] | None = None
    on_open_subpastas_callback: Callable[[], None] | None = None
    on_upload_callback: Callable[[], None] | None = None
    on_upload_folder_callback: Callable[[], None] | None = None
    on_open_lixeira_callback: Callable[[], None] | None = None
    on_obrigacoes_callback: Callable[[], None] | None = None

    def handle_new(self) -> ActionResult:
        """Trata clique no botão Novo Cliente.

        Regras:
        - Verifica se callback está registrado
        - Não há pré-condições especiais para criar novo cliente

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_new_callback or not callable(self.on_new_callback):
            return ActionResult(kind="no_callback", message="Callback de criação não configurado.")

        try:
            self.on_new_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_new: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao criar novo cliente: {exc}")

    def handle_edit(self) -> ActionResult:
        """Trata clique no botão Editar Cliente.

        Regras:
        - Verifica se há callback registrado
        - O callback é responsável por verificar seleção (compatibilidade com código existente)

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_edit_callback or not callable(self.on_edit_callback):
            return ActionResult(kind="no_callback", message="Callback de edição não configurado.")

        try:
            self.on_edit_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_edit: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao editar cliente: {exc}")

    def handle_delete(self) -> ActionResult:
        """Trata clique no botão Excluir (enviar para lixeira).

        Regras:
        - Esta ação é tratada diretamente pela View via on_delete callback
        - Mantido aqui para consistência de interface, mas apenas retorna ok

        Returns:
            ActionResult com kind="ok" (delegação para View)
        """
        # Nota MS-25/MS-26: A exclusão já é tratada via on_delete_selected_clients
        # que verifica seleção e chama o callback on_delete da View.
        # Mantemos este método para futura migração de lógica, se necessário.
        log.debug("handle_delete: delegando para View (on_delete callback)")
        return ActionResult(kind="ok")

    def handle_open_trash(self) -> ActionResult:
        """Trata clique no botão Lixeira.

        Regras:
        - Abre a tela de lixeira
        - Não há pré-condições especiais

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_open_lixeira_callback or not callable(self.on_open_lixeira_callback):
            return ActionResult(kind="no_callback", message="Callback de lixeira não configurado.")

        try:
            self.on_open_lixeira_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_open_lixeira: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao abrir lixeira: {exc}")

    def handle_open_subfolders(self) -> ActionResult:
        """Trata clique no botão Subpastas.

        Regras:
        - Abre o gerenciador de subpastas
        - Não há pré-condições especiais

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_open_subpastas_callback or not callable(self.on_open_subpastas_callback):
            return ActionResult(kind="no_callback", message="Callback de subpastas não configurado.")

        try:
            self.on_open_subpastas_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_open_subpastas: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao abrir subpastas: {exc}")

    def handle_send_supabase(self) -> ActionResult:
        """Trata clique em Enviar para Supabase.

        Regras:
        - Envia cliente(s) selecionado(s) para o Supabase
        - Requer callback válido (validação de seleção feita pelo callback)

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_upload_callback or not callable(self.on_upload_callback):
            return ActionResult(kind="no_callback", message="Callback de envio para Supabase não configurado.")

        try:
            self.on_upload_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_upload: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao enviar para Supabase: {exc}")

    def handle_send_folder(self) -> ActionResult:
        """Trata clique em Enviar para Pasta.

        Regras:
        - Envia arquivos do cliente para pasta
        - Requer callback válido (validação de seleção feita pelo callback)

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_upload_folder_callback or not callable(self.on_upload_folder_callback):
            return ActionResult(kind="no_callback", message="Callback de envio para pasta não configurado.")

        try:
            self.on_upload_folder_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_upload_folder: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao enviar para pasta: {exc}")

    def handle_obrigacoes(self) -> ActionResult:
        """Trata clique no botão Obrigações.

        Regras:
        - Abre tela de obrigações
        - Não há pré-condições especiais

        Returns:
            ActionResult com kind="ok" se sucesso, "no_callback" se não configurado,
            "error" se houver exceção.
        """
        if not self.on_obrigacoes_callback or not callable(self.on_obrigacoes_callback):
            return ActionResult(kind="no_callback", message="Callback de obrigações não configurado.")

        try:
            self.on_obrigacoes_callback()
            return ActionResult(kind="ok")
        except Exception as exc:
            log.exception("Erro ao executar callback on_obrigacoes: %s", exc)
            return ActionResult(kind="error", message=f"Erro ao abrir obrigações: {exc}")
