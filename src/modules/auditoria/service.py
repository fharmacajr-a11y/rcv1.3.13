"""Service layer para Auditoria - Funções de integração com Supabase."""
from __future__ import annotations

from typing import Any

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:
    def get_supabase():  # type: ignore[no-redef]
        return None


def list_clientes_minimal() -> list[dict[str, Any]]:
    """
    Retorna lista mínima de clientes (id, razao_social, cnpj) ordenada por nome.
    
    Returns:
        Lista de dicts com chaves: id, razao_social, cnpj
    """
    sb = get_supabase()
    if not sb:
        return []
    
    try:
        res = (
            sb.table("clientes")
            .select("id, razao_social, cnpj")
            .order("razao_social")
            .execute()
        )
        return getattr(res, "data", []) or []
    except Exception:
        return []


def list_auditorias() -> list[dict[str, Any]]:
    """
    Retorna lista de auditorias com dados do cliente via FK.
    
    Usa select com relação referenciada: clientes:cliente_id(razao_social)
    
    Returns:
        Lista de dicts com chaves: id, status, created_at, updated_at, cliente_id, clientes
    """
    sb = get_supabase()
    if not sb:
        return []
    
    try:
        res = (
            sb.table("auditorias")
            .select("id, status, created_at, updated_at, cliente_id, clientes:cliente_id(razao_social)")
            .order("created_at", desc=True)
            .execute()
        )
        return getattr(res, "data", []) or []
    except Exception:
        return []


def start_auditoria(cliente_id: str) -> dict[str, Any] | None:
    """
    Inicia uma nova auditoria para o cliente especificado.
    
    Args:
        cliente_id: ID do cliente (string ou int)
        
    Returns:
        Dict com dados da auditoria criada, ou None se falhar
    """
    sb = get_supabase()
    if not sb:
        return None
    
    try:
        res = (
            sb.table("auditorias")
            .insert({"cliente_id": cliente_id, "status": "em_andamento"})
            .execute()
        )
        data = getattr(res, "data", None)
        return data[0] if data else None
    except Exception:
        return None
