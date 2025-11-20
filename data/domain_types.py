# -*- coding: utf-8 -*-
# data/domain_types.py
"""Domain TypedDicts for Supabase table rows.

This module defines typed dictionaries representing the structure of database rows
for the main tables in the application. These types improve type safety and IDE
autocomplete when working with Supabase query results.

Note: Fields marked as optional (total=False or Type | None) represent nullable
columns or fields that may not always be present in query results.
"""

from __future__ import annotations

from typing import TypedDict

from typing_extensions import NotRequired


# =============================================================================
# Client Passwords Table
# =============================================================================


class PasswordRow(TypedDict):
    """Row from the 'client_passwords' table.

    Represents a stored password/credential for a client service.
    The password_enc field contains the encrypted password value.
    """

    id: str  # UUID primary key
    org_id: str  # UUID foreign key to organizations
    client_name: str  # Name of the client this password belongs to
    service: str  # Name of the service (e.g., "Portal X", "Sistema Y")
    username: str  # Username/login for the service
    password_enc: str  # Encrypted password (use decrypt_text to view)
    notes: str  # Additional notes about this credential
    created_by: str  # User ID who created this record
    created_at: str  # ISO timestamp of creation
    updated_at: str  # ISO timestamp of last update


# =============================================================================
# Clients Table
# =============================================================================


class ClientRow(TypedDict):
    """Row from the 'clients' table.

    Represents a client/customer in the system with basic identification info.
    Used in client search, picker dialogs, and client management features.
    """

    id: str  # UUID primary key
    org_id: str  # UUID foreign key to organizations
    razao_social: str  # Legal company name (Razão Social)
    nome_fantasia: NotRequired[str]  # Trade name (Nome Fantasia) - optional
    cnpj: str  # Brazilian tax ID (CNPJ)
    nome: NotRequired[str]  # Contact name field
    numero: NotRequired[str]  # Internal/phone number field
    obs: NotRequired[str]  # Notes/observations about the client
    cnpj_norm: NotRequired[str]  # Normalized CNPJ (digits only)


# =============================================================================
# Memberships Table (minimal - used only for RLS checks)
# =============================================================================


class MembershipRow(TypedDict, total=False):
    """Row from the 'memberships' table.

    Represents the relationship between users and organizations.
    This type is minimal because memberships are primarily used for
    Row-Level Security (RLS) checks, not for business logic.

    total=False means all fields are optional (useful for partial queries).
    """

    user_id: str  # UUID foreign key to auth.users
    org_id: str  # UUID foreign key to organizations
    role: str  # Optional: user role in the organization
    created_at: str  # Optional: ISO timestamp of membership creation
