"""Fixtures e helpers compartilhados para testes do modulo de senhas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.db.domain_types import PasswordRow


def make_password_row(**overrides: Any) -> PasswordRow:
    """Cria PasswordRow com valores padrao, permitindo overrides."""
    base: dict[str, Any] = {
        "id": "pwd-base",
        "org_id": "org-1",
        "client_id": "client-1",
        "client_name": "Cliente",
        "service": "SIFAP",
        "username": "user@example.com",
        "password_enc": "encrypted",
        "notes": "",
        "created_by": "user-1",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "client_external_id": "1",
        "razao_social": "Cliente",
        "cnpj": "",
        "nome": "",
        "whatsapp": "",
        "numero": "",
    }
    base.update(overrides)
    return PasswordRow(**base)


__all__ = ["make_password_row"]
