"""Ações headless do módulo de Senhas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.data.domain_types import ClientRow, PasswordRow

from src.modules.passwords.controller import PasswordsController
from src.modules.passwords import service as passwords_service

ClientPasswordsSummary = passwords_service.ClientPasswordsSummary


@dataclass
class PasswordsScreenState:
    """Estado carregado ao inicializar a tela de senhas."""

    org_id: str
    user_id: str
    clients: list[ClientRow]
    all_passwords: list[PasswordRow]


@dataclass
class PasswordsScreenSummaries:
    """Resumo de listas usadas pela view."""

    all_summaries: list[ClientPasswordsSummary]
    summaries_by_id: dict[str, ClientPasswordsSummary]
    filtered_summaries: list[ClientPasswordsSummary]


@dataclass
class PasswordFormData:
    """Dados provenientes do diálogo de senha."""

    client_id: str
    client_name: str
    service: str
    username: str
    password: str
    notes: str
    is_editing: bool
    password_id: str | None = None


class PasswordsActions:
    """Coordena operações headless usadas pelas views de senhas."""

    def __init__(self, controller: PasswordsController | None = None) -> None:
        self.controller = controller or PasswordsController()

    def bootstrap_screen(self, main_window: Any) -> PasswordsScreenState:
        """Resolve contexto de usuário e carrega dados necessários."""
        context = passwords_service.resolve_user_context(main_window)
        clients = self.controller.list_clients(context.org_id)
        passwords = self.controller.load_all_passwords(context.org_id)
        return PasswordsScreenState(
            org_id=context.org_id,
            user_id=context.user_id,
            clients=clients,
            all_passwords=list(passwords),
        )

    def reload_passwords(self, org_id: str) -> list[PasswordRow]:
        """Atualiza o cache de senhas do controller."""
        return list(self.controller.load_all_passwords(org_id))

    def build_summaries(
        self,
        all_passwords: Sequence[Mapping[str, Any]],
        *,
        search_text: str | None,
        service_filter: str | None,
    ) -> PasswordsScreenSummaries:
        """Retorna listas prontas para alimentar a Treeview.

        Args:
            all_passwords: Lista completa de senhas
            search_text: Filtro de busca textual
            service_filter: Filtro por serviço

        Returns:
            PasswordsScreenSummaries com all_summaries, filtered_summaries e summaries_by_id
        """
        filtered = passwords_service.filter_passwords(all_passwords, search_text, service_filter)
        all_summaries = passwords_service.group_passwords_by_client(all_passwords)
        filtered_summaries = passwords_service.group_passwords_by_client(filtered)
        summaries_by_id = {str(summary.client_id): summary for summary in all_summaries}
        return PasswordsScreenSummaries(
            all_summaries=all_summaries,
            summaries_by_id=summaries_by_id,
            filtered_summaries=filtered_summaries,
        )

    def delete_client_passwords(self, org_id: str, client_id: str) -> int:
        """Exclui todas as senhas de um cliente."""
        return self.controller.delete_all_passwords_for_client(org_id, client_id)


class PasswordDialogActions:
    """Ações reutilizáveis para o diálogo de criação/edição de senhas."""

    def __init__(self, controller: PasswordsController | None = None) -> None:
        self.controller = controller or PasswordsController()

    @staticmethod
    def validate_form(data: PasswordFormData) -> list[str]:
        """Retorna lista de erros de validação.

        Args:
            data: Dados do formulário a validar

        Returns:
            Lista de mensagens de erro (vazia se tudo OK)

        Note:
            Quando is_editing=True, password vazia é permitida (mantém senha atual)
        """
        errors: list[str] = []
        if not data.client_id:
            errors.append("Selecione um cliente usando o botão 'Selecionar...'.")
        if not data.client_name.strip():
            errors.append("O campo Cliente está vazio.")
        if not data.service.strip():
            errors.append("Informe o serviço.")
        if not data.username.strip():
            errors.append("Informe o usuário/login.")
        if not data.password and not data.is_editing:
            errors.append("Informe a senha.")
        return errors

    def find_duplicates(self, org_id: str, client_id: str, service: str) -> list[PasswordRow]:
        """Busca possíveis duplicidades (cliente + serviço)."""
        return self.controller.find_duplicate_passwords_by_service(org_id, client_id, service)

    def create_password(self, org_id: str, user_id: str, data: PasswordFormData) -> None:
        """Persiste nova senha usando o controller."""
        self.controller.create_password(
            org_id,
            client_id=data.client_id,
            client_name=data.client_name,
            service=data.service,
            username=data.username,
            password=data.password,
            notes=data.notes,
            user_id=user_id,
        )

    def update_password(self, data: PasswordFormData) -> None:
        """Atualiza senha existente.

        Args:
            data: Dados do formulário com password_id preenchido

        Raises:
            ValueError: Se password_id não estiver preenchido
        """
        if not data.password_id:
            raise ValueError("ID da senha não informado para atualização.")
        self.controller.update_password(
            data.password_id,
            client_id=data.client_id,
            client_name=data.client_name,
            service=data.service,
            username=data.username,
            password_plain=data.password,
            notes=data.notes,
        )


__all__ = [
    "PasswordDialogActions",
    "PasswordFormData",
    "PasswordsActions",
    "PasswordsScreenState",
    "PasswordsScreenSummaries",
    "ClientPasswordsSummary",
]
