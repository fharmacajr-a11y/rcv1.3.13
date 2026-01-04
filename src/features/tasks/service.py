# -*- coding: utf-8 -*-
"""Service layer for RC tasks creation and management.

Provides business logic for creating tasks with validation and normalization.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Union

from src.data.domain_types import RCTaskRow
from src.data.supabase_repo import PostgrestAPIError, get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "rc_tasks"


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _normalize_priority(priority: str) -> str:
    """Normaliza prioridade para um dos valores aceitos.

    Args:
        priority: String de prioridade (case-insensitive)

    Returns:
        Uma das strings: "low", "normal", "high", "urgent"

    Raises:
        ValueError: Se prioridade não for reconhecida
    """
    priority_lower = priority.lower().strip()
    valid_priorities = {"low", "normal", "high", "urgent"}

    # Mapeamento de aliases comuns
    aliases = {
        "baixa": "low",
        "baixo": "low",
        "média": "normal",
        "medio": "normal",
        "alta": "high",
        "alto": "high",
        "urgente": "urgent",
    }

    # Primeiro tenta usar direto
    if priority_lower in valid_priorities:
        return priority_lower

    # Senão tenta alias
    if priority_lower in aliases:
        return aliases[priority_lower]

    # Valor inválido
    raise ValueError(
        f"Prioridade '{priority}' inválida. Use: low, normal, high, urgent (ou baixa, normal, alta, urgente)"
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def create_task(
    org_id: str,
    created_by: str,
    *,
    title: str,
    description: str | None = None,
    priority: str = "normal",
    due_date: date | None = None,
    assigned_to: str | None = None,
    client_id: int | None = None,
) -> RCTaskRow:
    """Cria uma nova tarefa no sistema RC.

    Args:
        org_id: UUID da organização
        created_by: UUID do usuário criador
        title: Título da tarefa (obrigatório, não pode ser vazio)
        description: Descrição detalhada (opcional)
        priority: Prioridade: "low", "normal", "high", "urgent" (default: "normal")
        due_date: Data de vencimento (default: hoje)
        assigned_to: UUID do usuário responsável (opcional)
        client_id: ID do cliente vinculado (opcional)

    Returns:
        RCTaskRow com os dados da tarefa criada

    Raises:
        ValueError: Se título estiver vazio ou prioridade inválida
        RuntimeError: Se houver erro na comunicação com Supabase
    """
    # Validações
    if not title or not title.strip():
        raise ValueError("Título da tarefa não pode ser vazio")

    # Normaliza prioridade
    try:
        normalized_priority = _normalize_priority(priority)
    except ValueError as e:
        raise ValueError(str(e)) from e

    # Define due_date como hoje se não fornecido
    final_due_date = due_date or date.today()

    # Prepara dados para inserção (SEMPRE incluir org_id, created_by, title, priority, status, due_date)
    insert_data: Dict[str, Union[str, int, None]] = {
        "org_id": org_id,
        "created_by": created_by,
        "title": title.strip(),
        "priority": normalized_priority,
        "status": "pending",  # Status inicial sempre pending
        "due_date": final_due_date.isoformat(),
    }

    # Adicionar campos opcionais apenas se fornecidos
    if description:
        insert_data["description"] = description.strip()
    if assigned_to:
        insert_data["assigned_to"] = assigned_to
    if client_id is not None:
        insert_data["client_id"] = client_id

    # Insere no Supabase
    try:
        client = get_supabase_client()
        response = client.table(TABLE).insert(insert_data).execute()

        if not response.data or len(response.data) == 0:
            raise RuntimeError("Nenhum dado retornado após inserção da tarefa")

        # Retorna a primeira (e única) linha criada
        task_row: RCTaskRow = response.data[0]
        logger.info(
            "Tarefa criada com sucesso: id=%s, title=%s, priority=%s",
            task_row.get("id", "?"),
            task_row.get("title", "?"),
            task_row.get("priority", "?"),
        )

        return task_row

    except PostgrestAPIError as e:
        # Detectar erro de RLS (código 42501)
        error_msg = str(e)
        error_code = None

        # Tentar extrair código do erro (pode ser atributo ou no dict)
        try:
            if hasattr(e, "code"):
                error_code = e.code
            elif hasattr(e, "json") and callable(e.json):
                error_dict = e.json()
                error_code = error_dict.get("code") if isinstance(error_dict, dict) else None
        except Exception:  # noqa: BLE001
            logger.debug("Falha ao extrair error code da exceção", exc_info=True)
            pass

        if error_code == "42501" or "row-level security policy" in error_msg.lower():
            logger.warning(
                "Erro RLS ao criar tarefa: org_id=%s, created_by=%s, error=%s",
                org_id,
                created_by,
                error_msg,
            )
            raise RuntimeError(
                "Erro ao criar tarefa: permissão negada pela política de segurança (RLS). "
                "Verifique organização e usuário."
            ) from e

        logger.error("Erro ao criar tarefa no Supabase: %s", e)
        raise RuntimeError(f"Erro ao criar tarefa: {e}") from e
    except Exception as e:
        logger.error("Erro inesperado ao criar tarefa: %s", e)
        raise RuntimeError(f"Erro ao criar tarefa: {e}") from e
