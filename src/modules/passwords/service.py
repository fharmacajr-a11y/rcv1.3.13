"""Serviços headless do módulo de Senhas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from data.domain_types import PasswordRow
from infra.repositories import passwords_repository


@dataclass
class ClientPasswordsSummary:
    """Resumo de senhas agrupadas por cliente."""

    client_id: str
    client_external_id: int
    razao_social: str
    cnpj: str
    contato_nome: str
    whatsapp: str
    passwords_count: int
    services: list[str]

    @property
    def display_name(self) -> str:
        """Rótulo amigável para uso em títulos de janelas/dialogos."""
        parts: list[str] = []
        if self.client_external_id:
            parts.append(f"ID {self.client_external_id}")
        if self.razao_social:
            parts.append(self.razao_social)
        return " – ".join(parts) if parts else self.client_id


@dataclass
class PasswordsUserContext:
    """Representa usuário e organização correntes para o módulo."""

    org_id: str
    user_id: str


def _coerce_client_external_id(raw_id: Any, fallback: str) -> int:
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        try:
            return int(fallback)
        except (TypeError, ValueError):
            return 0


def _build_summary_from_group(client_id: str, passwords: list[PasswordRow]) -> ClientPasswordsSummary:
    first = passwords[0]
    razao_social = first.get("razao_social", first.get("client_name", ""))
    cnpj = first.get("cnpj", "")
    contato_nome = first.get("nome", "")
    whatsapp = first.get("whatsapp", first.get("numero", ""))
    services = sorted({p.get("service", "") for p in passwords if p.get("service")})
    client_external_id = _coerce_client_external_id(first.get("client_external_id"), client_id)
    return ClientPasswordsSummary(
        client_id=str(client_id),
        client_external_id=client_external_id,
        razao_social=razao_social,
        cnpj=cnpj,
        contato_nome=contato_nome,
        whatsapp=whatsapp,
        passwords_count=len(passwords),
        services=services,
    )


def group_passwords_by_client(passwords: Iterable[PasswordRow]) -> list[ClientPasswordsSummary]:
    """Agrupa senhas por client_id e retorna resumos ordenados pelo nome."""
    from collections import defaultdict

    grouped: dict[str, list[PasswordRow]] = defaultdict(list)
    for pwd in passwords:
        client_id = pwd.get("client_id")
        if not client_id:
            continue
        grouped[str(client_id)].append(pwd)

    summaries = [_build_summary_from_group(client_id, rows) for client_id, rows in grouped.items()]
    summaries.sort(key=lambda summary: summary.razao_social.lower())
    return summaries


def filter_passwords(
    passwords: Iterable[PasswordRow],
    search_text: Optional[str],
    service_filter: Optional[str],
) -> list[PasswordRow]:
    """Aplica filtros textuais/por serviço sobre a lista informada."""
    filtered = list(passwords)

    if search_text:
        lowered = search_text.strip().lower()
        if lowered:
            filtered = [
                pwd
                for pwd in filtered
                if lowered in (pwd.get("client_name") or "").lower()
                or lowered in (pwd.get("service") or "").lower()
                or lowered in (pwd.get("username") or "").lower()
            ]

    if service_filter and service_filter != "Todos":
        filtered = [pwd for pwd in filtered if pwd.get("service") == service_filter]

    return filtered


def resolve_user_context(main_window: Any) -> PasswordsUserContext:
    """
    Resolve (org_id, user_id) a partir da sessão Supabase e da janela principal.

    Levanta RuntimeError se não conseguir determinar o contexto.
    """
    try:
        from infra.supabase_client import supabase
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Cliente Supabase indisponível para senhas.") from exc

    user = supabase.auth.get_user()
    user_obj = getattr(user, "user", None) or user
    if isinstance(user_obj, dict):
        user_id = user_obj.get("id") or user_obj.get("uid")
    else:
        user_id = getattr(user_obj, "id", None)

    if not user_id:
        raise RuntimeError("Usuário não autenticado para acessar senhas.")

    org_id: Optional[str] = None
    if main_window and hasattr(main_window, "_get_org_id_cached"):
        try:
            org_id = main_window._get_org_id_cached(user_id)  # type: ignore[attr-defined]
        except Exception:
            org_id = None

    if not org_id:
        try:
            from src.modules.clientes.service import _resolve_current_org_id  # type: ignore

            org_id = _resolve_current_org_id()
        except Exception:
            org_id = None

    if not org_id:
        raise RuntimeError("Não foi possível determinar a organização atual para senhas.")

    return PasswordsUserContext(org_id=org_id, user_id=user_id)


# Reexports finos do repositório legado
get_passwords = passwords_repository.get_passwords
create_password = passwords_repository.create_password
update_password_by_id = passwords_repository.update_password_by_id
delete_password_by_id = passwords_repository.delete_password_by_id
find_duplicate_password_by_service = passwords_repository.find_duplicate_password_by_service
delete_all_passwords_for_client = passwords_repository.delete_all_passwords_for_client

__all__ = [
    "ClientPasswordsSummary",
    "PasswordsUserContext",
    "group_passwords_by_client",
    "filter_passwords",
    "resolve_user_context",
    "get_passwords",
    "create_password",
    "update_password_by_id",
    "delete_password_by_id",
    "find_duplicate_password_by_service",
    "delete_all_passwords_for_client",
]
