# -*- coding: utf-8 -*-
"""Repositório para operações com senhas."""

from __future__ import annotations

from typing import Optional

from data.domain_types import PasswordRow


def get_passwords(org_id: str, search_text: Optional[str] = None, client_filter: Optional[str] = None) -> list[PasswordRow]:
    """Lista senhas com filtros opcionais."""
    from data.supabase_repo import list_passwords

    passwords = list_passwords(org_id)

    if search_text:
        search_lower = search_text.lower()
        passwords = [
            p for p in passwords if search_lower in p["client_name"].lower() or search_lower in p["service"].lower() or search_lower in p["username"].lower()
        ]

    if client_filter and client_filter != "Todos":
        passwords = [p for p in passwords if p["client_name"] == client_filter]

    return passwords


def create_password(org_id: str, client_name: str, service: str, username: str, password_plain: str, notes: str, created_by: str) -> PasswordRow:
    """Cria uma nova senha."""
    from data.supabase_repo import add_password

    return add_password(org_id, client_name, service, username, password_plain, notes, created_by)


def update_password_by_id(
    password_id: str,
    client_name: Optional[str] = None,
    service: Optional[str] = None,
    username: Optional[str] = None,
    password_plain: Optional[str] = None,
    notes: Optional[str] = None,
) -> PasswordRow:
    """Atualiza uma senha existente."""
    from data.supabase_repo import update_password

    return update_password(password_id, client_name, service, username, password_plain, notes)


def delete_password_by_id(password_id: str) -> None:
    """Exclui uma senha."""
    from data.supabase_repo import delete_password

    delete_password(password_id)
