"""Serviço para gerenciar cache de sessão do usuário."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

# Import no nível do módulo para permitir DI e evitar lazy imports
try:
    from infra.supabase_client import exec_postgrest, supabase
    from infra.db_schemas import MEMBERSHIPS_SELECT_ROLE, MEMBERSHIPS_SELECT_ORG_ID
except ImportError:
    # Fallback para testes sem dependências
    exec_postgrest = None  # type: ignore
    supabase = None  # type: ignore
    MEMBERSHIPS_SELECT_ROLE = "role"  # type: ignore
    MEMBERSHIPS_SELECT_ORG_ID = "org_id"  # type: ignore

log = logging.getLogger(__name__)

# Type alias para função de exec_postgrest (para DI)
ExecPostgrestFn = Callable[[Any], Any]


class SessionCache:
    """Cache de dados de sessão do usuário (user, role, org_id)."""

    # Atributos de classe para rastrear todas as instâncias (para limpeza em testes)
    _all_instances: list[SessionCache] = []

    def __init__(self, exec_postgrest_fn: ExecPostgrestFn | None = None, supabase_client: Any = None) -> None:
        """Inicializa SessionCache com dependency injection opcional.

        Args:
            exec_postgrest_fn: Função para executar queries PostgreSQL.
                             Se None, usa exec_postgrest do infra.supabase_client.
                             Útil para testes com mocks.
            supabase_client: Cliente supabase para queries. Se None, usa o global.
        """
        self._user_cache: Optional[dict[str, Any]] = None
        self._role_cache: Optional[str] = None
        self._org_id_cache: Optional[str] = None
        # DI: usar função/cliente injetados ou padrões do módulo
        self._exec_postgrest = exec_postgrest_fn or exec_postgrest
        self._supabase = supabase_client or supabase
        # Registra instância para possível limpeza global
        SessionCache._all_instances.append(self)

    def clear(self) -> None:
        """Limpa todo o cache de sessão."""
        self._user_cache = None
        self._role_cache = None
        self._org_id_cache = None

    @classmethod
    def clear_all_instances_for_tests(cls) -> None:
        """
        Limpa cache de TODAS as instâncias de SessionCache criadas.

        Este método é para uso em testes, garantindo que nenhum estado
        de cache (role, org_id, user) seja compartilhado entre testes.
        """
        for instance in cls._all_instances:
            instance.clear()
        # Limpa também a lista de instâncias para evitar memory leak
        cls._all_instances.clear()

    def get_user(self) -> Optional[dict[str, Any]]:
        """
        Retorna dados do usuário autenticado (id, email).

        Consulta Supabase auth.get_user() e cacheia o resultado.
        """
        if self._user_cache:
            return self._user_cache

        if self._supabase is None:
            log.warning("Supabase client não disponível")
            return None

        try:
            resp = self._supabase.auth.get_user()
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

        if self._supabase is None or self._exec_postgrest is None:
            log.warning("Supabase client ou exec_postgrest não disponível")
            return "user"

        try:
            query = self._supabase.table("memberships").select(MEMBERSHIPS_SELECT_ROLE).eq("user_id", uid).limit(1)
            res = self._exec_postgrest(query)

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

        if self._supabase is None or self._exec_postgrest is None:
            log.warning("Supabase client ou exec_postgrest não disponível")
            return None

        try:
            res = self._exec_postgrest(
                self._supabase.table("memberships").select(MEMBERSHIPS_SELECT_ORG_ID).eq("user_id", uid).limit(1)
            )

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
