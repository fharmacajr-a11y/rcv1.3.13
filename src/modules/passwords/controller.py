from __future__ import annotations

import logging
from typing import Optional

from data.domain_types import ClientRow, PasswordRow
from data.supabase_repo import list_clients_for_picker
from security.crypto import decrypt_text

from src.modules.passwords import service as passwords_service
from src.modules.passwords.service import ClientPasswordsSummary

log = logging.getLogger(__name__)

__all__ = ["PasswordsController", "ClientPasswordsSummary"]


class PasswordsController:
    """Controlador fino para operações da tela de senhas."""

    def __init__(self) -> None:
        self._all_passwords: list[PasswordRow] = []

    @property
    def all_passwords(self) -> list[PasswordRow]:
        return self._all_passwords

    def load_all_passwords(self, org_id: str) -> list[PasswordRow]:
        """Busca senhas no repositório mantendo cache em memória."""
        self._all_passwords = passwords_service.get_passwords(org_id, None, "Todos")
        return self._all_passwords

    def filter_passwords(
        self,
        search_text: Optional[str],
        service_filter: Optional[str],
    ) -> list[PasswordRow]:
        """Filtra o cache atual por texto/serviço."""
        return passwords_service.filter_passwords(self._all_passwords, search_text, service_filter)

    def create_password(
        self,
        org_id: str,
        client_id: str,
        client_name: str,
        service: str,
        username: str,
        password: str,
        notes: str,
        user_id: str,
    ) -> None:
        passwords_service.create_password(org_id, client_name, service, username, password, notes, user_id, client_id)

    def update_password(
        self,
        password_id: str,
        *,
        client_id: str | None = None,
        client_name: str,
        service: str,
        username: str,
        password_plain: str,
        notes: str,
    ) -> None:
        passwords_service.update_password_by_id(
            password_id,
            client_id=client_id,
            client_name=client_name,
            service=service,
            username=username,
            password_plain=password_plain,
            notes=notes,
        )

    def delete_password(self, password_id: str) -> None:
        passwords_service.delete_password_by_id(password_id)

    def delete_all_passwords_for_client(self, org_id: str, client_id: str) -> int:
        """Exclui todas as senhas de um cliente.

        Args:
            org_id: ID da organização.
            client_id: ID do cliente.

        Returns:
            Número de senhas excluídas.
        """
        return passwords_service.delete_all_passwords_for_client(org_id, client_id)

    def decrypt_password(self, password_enc: str) -> str:
        return decrypt_text(password_enc)

    def list_clients(self, org_id: str) -> list[ClientRow]:
        return list_clients_for_picker(org_id)

    def group_passwords_by_client(self) -> list[ClientPasswordsSummary]:
        """
        Agrupa self._all_passwords por client_id e monta um resumo.

        Returns:
            list[ClientPasswordsSummary]: Lista de resumos por cliente.
        """
        return passwords_service.group_passwords_by_client(self._all_passwords)

    def get_passwords_for_client(self, client_id: str) -> list[PasswordRow]:
        """
        Filtra self._all_passwords apenas para o client_id informado.

        Args:
            client_id: ID do cliente.

        Returns:
            list[PasswordRow]: Senhas do cliente.
        """
        return [p for p in self._all_passwords if p.get("client_id") == client_id]

    def find_duplicate_passwords_by_service(
        self,
        org_id: str,
        client_id: str,
        service: str,
    ) -> list[PasswordRow]:
        """
        Retorna senhas existentes para (org_id, client_id, service).

        Args:
            org_id: ID da organização.
            client_id: ID do cliente.
            service: Nome do serviço.

        Returns:
            list[PasswordRow]: Senhas duplicadas (pode ser vazia).
        """
        return passwords_service.find_duplicate_password_by_service(
            org_id=org_id,
            client_id=client_id,
            service=service,
        )
