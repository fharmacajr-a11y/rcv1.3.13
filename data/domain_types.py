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

from datetime import date, datetime, time
from typing import Literal, TypedDict

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


# =============================================================================
# RC Tasks Table
# =============================================================================


class RCTaskRow(TypedDict):
    """Row from the 'rc_tasks' table.

    Represents a task in the RC system (Regularize Consultoria).
    Tasks can be assigned to users, linked to clients, and have priorities/deadlines.

    Required fields are always present. Optional fields use NotRequired.
    """

    id: str  # UUID primary key
    org_id: str  # UUID foreign key to organizations
    created_by: str  # UUID of user who created this task
    assigned_to: NotRequired[str | None]  # UUID of user assigned to this task (nullable)
    client_id: NotRequired[int | None]  # Foreign key to clients (nullable)
    title: str  # Task title
    description: NotRequired[str | None]  # Task description (nullable)
    priority: Literal["low", "normal", "high", "urgent"]  # Task priority level
    due_date: NotRequired[date | None]  # Due date (nullable)
    due_time: NotRequired[time | None]  # Due time (nullable)
    status: Literal["pending", "done", "canceled"]  # Task status
    created_at: datetime  # Timestamp of creation
    updated_at: datetime  # Timestamp of last update
    completed_at: NotRequired[datetime | None]  # Timestamp of completion (nullable)


# =============================================================================
# Regulatory Obligations Table
# =============================================================================


class RegObligationRow(TypedDict):
    """Row from the 'reg_obligations' table.

    Represents a regulatory obligation for a client (SNGPC, Farmácia Popular, etc.).
    Used to track compliance deadlines and status.

    Required fields are always present. Optional fields use NotRequired.
    """

    id: str  # UUID primary key
    org_id: str  # UUID foreign key to organizations
    client_id: int  # Foreign key to clients
    kind: Literal["SNGPC", "FARMACIA_POPULAR", "SIFAP", "LICENCA_SANITARIA", "OUTRO"]
    title: str  # Obligation title/description
    reference_start: NotRequired[date | None]  # Reference period start (nullable)
    reference_end: NotRequired[date | None]  # Reference period end (nullable)
    due_date: date  # Due date for the obligation
    status: Literal["pending", "done", "overdue", "canceled"]  # Obligation status
    created_by: str  # UUID of user who created this record
    created_at: datetime  # Timestamp of creation
    updated_at: datetime  # Timestamp of last update
    completed_at: NotRequired[datetime | None]  # Timestamp of completion (nullable)
    notes: NotRequired[str | None]  # Additional notes (nullable)
