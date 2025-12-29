# -*- coding: utf-8 -*-
"""Repositório para operações com eventos de atividade da organização.

Este módulo fornece uma camada de abstração para gerenciar eventos de atividade
(histórico de ações) no Supabase.

Funcionalidades:
- Listar eventos recentes da organização
- Inserir novos eventos de atividade
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def list_recent(org_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Lista eventos recentes de atividade da organização.

    Args:
        org_id: ID da organização
        limit: Número máximo de eventos a retornar (padrão: 200)

    Returns:
        Lista de eventos ordenados por created_at (mais recente primeiro).
        Retorna lista vazia em caso de erro (nunca levanta exceção).
    """
    from infra.supabase_client import supabase

    try:
        response = (
            supabase.table("org_activity_events")
            .select(
                "id,org_id,module,action,message,client_id,cnpj,request_id,"
                "request_type,due_date,actor_user_id,actor_email,created_at,metadata"
            )
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception:
        # Hardening: tabela pode não existir, RLS pode bloquear, rede pode falhar
        # Retornar lista vazia para não derrubar o Hub
        log.exception(
            f"[ActivityEventsRepo] Erro ao listar eventos da org {org_id}. "
            "Possíveis causas: tabela não existe, RLS bloqueou, erro de rede."
        )
        return []


def insert_event(row: dict[str, Any]) -> bool:
    """Insere um novo evento de atividade.

    Args:
        row: Dicionário com campos do evento. Campos esperados:
            - org_id (obrigatório)
            - module (obrigatório): ex: "ANVISA", "SIFAP"
            - action (obrigatório): ex: "Concluída", "Cancelada", "Excluída"
            - message (obrigatório): mensagem formatada do evento
            - client_id (opcional): ID do cliente relacionado
            - cnpj (opcional): CNPJ do cliente
            - request_id (opcional): ID da demanda/request
            - request_type (opcional): Tipo da demanda
            - due_date (opcional): Prazo (YYYY-MM-DD)
            - actor_user_id (opcional): ID do usuário que executou
            - actor_email (opcional): Email do usuário que executou
            - metadata (opcional): JSON adicional

    Returns:
        True se inserção bem-sucedida, False se falhou.
        Nunca levanta exceção (hardening).
    """
    from infra.supabase_client import supabase

    try:
        # Validar campos obrigatórios
        required_fields = ["org_id", "module", "action", "message"]
        missing = [f for f in required_fields if not row.get(f)]
        if missing:
            log.warning(f"[ActivityEventsRepo] Campos obrigatórios ausentes: {missing}")
            return False

        response = supabase.table("org_activity_events").insert(row).execute()

        # Verificar se inserção foi bem-sucedida
        if response.data:
            log.debug(f"[ActivityEventsRepo] Evento inserido: {row['module']} - {row['action']}")
            return True
        else:
            log.warning(f"[ActivityEventsRepo] Inserção sem dados retornados: {row}")
            return False

    except Exception:
        # Hardening: tabela pode não existir, RLS pode bloquear, rede pode falhar
        # Nunca levantar exception para não quebrar UI
        log.exception(
            f"[ActivityEventsRepo] Erro ao inserir evento "
            f"(module={row.get('module')}, action={row.get('action')}). "
            "Possíveis causas: tabela não existe, RLS bloqueou, erro de rede."
        )
        return False
