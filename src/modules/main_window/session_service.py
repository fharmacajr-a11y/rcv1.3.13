"""Serviço para gerenciar cache de sessão do usuário."""

from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


class SessionCache:
    """Cache de dados de sessão do usuário (user, role, org_id)."""

    def __init__(self) -> None:
        self._user_cache: Optional[dict[str, Any]] = None
        self._role_cache: Optional[str] = None
        self._org_id_cache: Optional[str] = None

    def clear(self) -> None:
        """Limpa todo o cache de sessão."""
        self._user_cache = None
        self._role_cache = None
        self._org_id_cache = None

    def get_user(self) -> Optional[dict[str, Any]]:
        """
        Retorna dados do usuário autenticado (id, email).

        Consulta Supabase auth.get_user() e cacheia o resultado.
        """
        if self._user_cache:
            return self._user_cache

        try:
            from infra.supabase_client import supabase

            resp = supabase.auth.get_user()
            u = getattr(resp, "user", None) or resp
            uid = getattr(u, "id", None)
            email = getattr(u, "email", "") or ""

            if uid:
                self._user_cache = {"id": uid, "email": email}
                return self._user_cache
        except Exception as e:
            log.debug("Erro ao obter usuário da sessão: %s", e)

        return None

    def get_role(self, uid: str) -> str:
        """
        Retorna role do usuário (admin, user, etc.).

        Consulta tabela memberships e cacheia o resultado.
        Fallback: "user"
        """
        if self._role_cache:
            return self._role_cache

        try:
            from infra.supabase_client import exec_postgrest, supabase

            res = exec_postgrest(supabase.table("memberships").select("role").eq("user_id", uid).limit(1))

            if getattr(res, "data", None):
                role_value = res.data[0].get("role")
                self._role_cache = str(role_value).lower() if role_value else "user"
            else:
                self._role_cache = "user"
        except Exception as e:
            log.debug("Erro ao obter role do usuário: %s", e)
            self._role_cache = "user"

        return self._role_cache or "user"

    def get_org_id(self, uid: str) -> Optional[str]:
        """
        Retorna org_id do usuário.

        Consulta tabela memberships e cacheia o resultado.
        Retorna None se não encontrar.
        """
        if self._org_id_cache:
            return self._org_id_cache

        try:
            from infra.supabase_client import exec_postgrest, supabase

            res = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1))

            if getattr(res, "data", None) and res.data[0].get("org_id"):
                self._org_id_cache = res.data[0]["org_id"]
                return self._org_id_cache
        except Exception as e:
            log.debug("Erro ao obter org_id do usuário: %s", e)

        return None

    def get_user_with_org(self) -> Optional[dict[str, Any]]:
        """
        Retorna dados completos do usuário (id, email, org_id, role).

        Combina get_user() + get_org_id() + get_role() em uma única chamada.
        """
        user = self.get_user()
        if not user:
            return None

        uid = user["id"]
        org_id = self.get_org_id(uid)
        role = self.get_role(uid)

        return {
            "id": uid,
            "email": user["email"],
            "org_id": org_id,
            "role": role,
        }
