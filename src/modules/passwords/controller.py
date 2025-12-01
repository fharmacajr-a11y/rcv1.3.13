from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from data.domain_types import ClientRow, PasswordRow
from data.supabase_repo import list_clients_for_picker
from security.crypto import decrypt_text

from src.modules.passwords import service as passwords_service

log = logging.getLogger(__name__)

__all__ = ["PasswordsController", "ClientPasswordsSummary"]


@dataclass
class ClientPasswordsSummary:
    """Resumo de senhas agrupadas por cliente."""

    client_id: str
    client_external_id: int  # ID numérico que aparece na tela de clientes
    razao_social: str
    cnpj: str
    contato_nome: str
    whatsapp: str
    passwords_count: int
    services: list[str]

    @property
    def display_name(self) -> str:
        """Rótulo amigável para usar em títulos de janelas/dialogs (sem CNPJ)."""
        parts: list[str] = []

        if self.client_external_id is not None:
            parts.append(f"ID {self.client_external_id}")

        if self.razao_social:
            parts.append(self.razao_social)

        label = " – ".join(parts) if parts else self.client_id

        return label


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
        filtered = list(self._all_passwords)

        if search_text:
            lowered = search_text.strip().lower()
            filtered = [
                p
                for p in filtered
                if lowered in p["client_name"].lower()
                or lowered in p["service"].lower()
                or lowered in p["username"].lower()
            ]

        if service_filter and service_filter != "Todos":
            filtered = [p for p in filtered if p["service"] == service_filter]

        return filtered

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
        from collections import defaultdict

        # Agrupa por client_id
        grouped: dict[str, list[PasswordRow]] = defaultdict(list)
        for pwd in self._all_passwords:
            client_id = pwd.get("client_id", "")
            if client_id:
                grouped[client_id].append(pwd)

        # Monta resumos
        summaries: list[ClientPasswordsSummary] = []
        for client_id, passwords in grouped.items():
            # Pega dados do primeiro registro (todos do mesmo cliente)
            first = passwords[0]

            # Extrai todos os campos necessários do PasswordRow (que agora vem com JOIN)
            razao_social = first.get("razao_social", first.get("client_name", ""))
            cnpj = first.get("cnpj", "")
            contato_nome = first.get("nome", "")
            whatsapp = first.get("whatsapp", first.get("numero", ""))

            # ID externo (numérico) do cliente - tenta converter de client_id
            try:
                client_external_id = int(first.get("client_external_id", client_id))
            except (ValueError, TypeError):
                # Se client_id não for numérico, tenta parsear ou usa 0
                try:
                    client_external_id = int(client_id)
                except (ValueError, TypeError):
                    client_external_id = 0

            # Lista única de serviços
            services = sorted(set(p.get("service", "") for p in passwords if p.get("service")))

            summaries.append(
                ClientPasswordsSummary(
                    client_id=client_id,
                    client_external_id=client_external_id,
                    razao_social=razao_social,
                    cnpj=cnpj,
                    contato_nome=contato_nome,
                    whatsapp=whatsapp,
                    passwords_count=len(passwords),
                    services=services,
                )
            )

        # Ordena por nome do cliente
        return sorted(summaries, key=lambda s: s.razao_social.lower())

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
