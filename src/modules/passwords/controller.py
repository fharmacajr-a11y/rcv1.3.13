from __future__ import annotations

import logging
from typing import Optional

from data.domain_types import ClientRow, PasswordRow
from data.supabase_repo import list_clients_for_picker
from security.crypto import decrypt_text

from src.modules.passwords import service as passwords_service

log = logging.getLogger(__name__)

__all__ = ["PasswordsController"]


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
            filtered = [p for p in filtered if lowered in p["client_name"].lower() or lowered in p["service"].lower() or lowered in p["username"].lower()]

        if service_filter and service_filter != "Todos":
            filtered = [p for p in filtered if p["service"] == service_filter]

        return filtered

    def create_password(
        self,
        org_id: str,
        client_name: str,
        service: str,
        username: str,
        password_plain: str,
        notes: str,
        user_id: str,
    ) -> None:
        passwords_service.create_password(org_id, client_name, service, username, password_plain, notes, user_id)

    def update_password(
        self,
        password_id: str,
        *,
        client_name: str,
        service: str,
        username: str,
        password_plain: str,
        notes: str,
    ) -> None:
        passwords_service.update_password_by_id(
            password_id,
            client_name=client_name,
            service=service,
            username=username,
            password_plain=password_plain,
            notes=notes,
        )

    def delete_password(self, password_id: str) -> None:
        passwords_service.delete_password_by_id(password_id)

    def decrypt_password(self, password_enc: str) -> str:
        return decrypt_text(password_enc)

    def list_clients(self, org_id: str) -> list[ClientRow]:
        return list_clients_for_picker(org_id)
