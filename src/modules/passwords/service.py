"""Serviços headless do módulo de Senhas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from src.db.domain_types import PasswordRow
from src.infra.repositories import passwords_repository


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


def _build_summary_from_group(client_id: str, passwords: Sequence[Mapping[str, Any]]) -> ClientPasswordsSummary:
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


def group_passwords_by_client(passwords: Sequence[Mapping[str, Any]]) -> list[ClientPasswordsSummary]:
    """Agrupa senhas por client_id e retorna resumos ordenados pelo nome.

    PERF-004: Usa índice por client_id para evitar reprocessamento.

    Args:
        passwords: Lista de senhas a agrupar

    Returns:
        Lista de ClientPasswordsSummary ordenada por razao_social (case-insensitive)
    """
    from collections import defaultdict

    # PERF-004: Construção de índice mais eficiente
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for pwd in passwords:
        client_id = pwd.get("client_id")
        if not client_id:
            continue
        grouped[str(client_id)].append(pwd)

    # PERF-004: Constrói summaries uma única vez
    summaries = [_build_summary_from_group(client_id, rows) for client_id, rows in grouped.items()]
    summaries.sort(key=lambda summary: summary.razao_social.lower())
    return summaries


def filter_passwords(
    passwords: Sequence[Mapping[str, Any]],
    search_text: str | None,
    service_filter: str | None,
) -> list[PasswordRow]:
    """Aplica filtros textuais/por serviço sobre a lista informada.

    Args:
        passwords: Lista de senhas a filtrar
        search_text: Texto para buscar em client_name, service, username (case-insensitive)
        service_filter: Filtro por serviço específico ("Todos" = sem filtro)

    Returns:
        Lista filtrada de PasswordRow
    """
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

    return cast(list[PasswordRow], filtered)


def _extract_user_id(user_response: Any) -> str | None:
    """Extrai user_id de diferentes formatos de resposta do Supabase.

    BUG-003: Helper function para extração segura de user_id.
    Suporta: dict, objeto com atributo 'id', objeto aninhado 'user'.

    Args:
        user_response: Resposta do supabase.auth.get_user()

    Returns:
        user_id como string, ou None se não encontrado
    """
    if not user_response:
        return None

    # Tenta acessar user_response.user primeiro
    user_obj = getattr(user_response, "user", None) or user_response

    # Se for dict
    if isinstance(user_obj, dict):
        return user_obj.get("id") or user_obj.get("uid")

    # Se for objeto com atributo id
    return getattr(user_obj, "id", None)


def resolve_user_context(main_window: Any) -> PasswordsUserContext:
    """Resolve (org_id, user_id) a partir da sessão Supabase e da janela principal.

    Args:
        main_window: Janela principal da aplicação (para cache de org_id)

    Returns:
        PasswordsUserContext com org_id e user_id válidos

    Raises:
        RuntimeError: Se não conseguir determinar usuário ou organização
    """
    try:
        from src.infra.supabase_client import supabase
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Cliente Supabase indisponível para senhas.") from exc

    user = supabase.auth.get_user()
    user_id = _extract_user_id(user)

    if not user_id:
        raise RuntimeError("Usuário não autenticado para acessar senhas.")

    org_id: str | None = None
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
