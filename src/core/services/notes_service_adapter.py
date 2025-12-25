# -*- coding: utf-8 -*-
"""Adapter para notes_service com interface compatível com NotesController.

Este adapter fornece uma interface consistente para o NotesController,
mapeando os métodos esperados (create_note, update_note, delete_note)
para as funções do notes_service.

MF-5: Adiciona suporte para toggle de is_pinned e is_done.
"""

from __future__ import annotations

import logging
from typing import Any

from infra.db_schemas import RC_NOTES_SELECT_FIELDS, RC_NOTES_SELECT_FIELDS_SAFE, is_schema_drift_error
from src.core.services import notes_service

log = logging.getLogger(__name__)

# Manter NOTES_SELECT_FIELDS como alias para compatibilidade
NOTES_SELECT_FIELDS = RC_NOTES_SELECT_FIELDS


class NotesServiceAdapter:
    """Adapter que fornece interface consistente para NotesController.

    Mapeia métodos esperados pelo controller para funções do notes_service,
    incluindo operações de update para is_pinned e is_done.
    """

    def __init__(self) -> None:
        """Inicializa o adapter."""
        pass

    def create_note(self, org_id: str, author_email: str, body: str) -> dict[str, Any]:
        """Cria nova nota.

        Args:
            org_id: UUID da organização
            author_email: Email do autor
            body: Texto da nota

        Returns:
            Dicionário com dados da nota criada

        Raises:
            ValueError: Se nota inválida
            NotesTableMissingError: Se tabela não existir
            NotesAuthError: Se sem permissão RLS
        """
        return notes_service.add_note(org_id=org_id, author_email=author_email, body=body)

    def update_note(
        self,
        note_id: str,
        *,
        body: str | None = None,
        is_pinned: bool | None = None,
        is_done: bool | None = None,
    ) -> dict[str, Any]:
        """Atualiza nota existente.

        MF-5: Permite atualizar body, is_pinned e is_done.

        Args:
            note_id: UUID da nota
            body: Novo texto (opcional)
            is_pinned: Novo estado de fixação (opcional)
            is_done: Novo estado de conclusão (opcional)

        Returns:
            Dicionário com dados da nota atualizada

        Raises:
            ValueError: Se nenhum campo fornecido
            NotesTableMissingError: Se tabela não existir
            NotesAuthError: Se sem permissão RLS
        """
        if body is None and is_pinned is None and is_done is None:
            raise ValueError("Nenhum campo fornecido para atualização")

        # Importar supabase client
        from infra.supabase_client import exec_postgrest, get_supabase

        supa = get_supabase()

        # Construir payload de atualização
        payload: dict[str, Any] = {}
        if body is not None:
            payload["body"] = body
        if is_pinned is not None:
            payload["is_pinned"] = is_pinned
        if is_done is not None:
            payload["is_done"] = is_done

        # Executar update (SEM .select() - PostgREST não suporta isso)
        try:
            resp_update = exec_postgrest(supa.table("rc_notes").update(payload).eq("id", note_id))

            # Tentar extrair dados da resposta do update
            updated_data = resp_update.data

            # Se retornou lista com item, usar ele
            if isinstance(updated_data, list) and len(updated_data) > 0:
                return updated_data[0]

            # Se retornou dict, usar ele
            if isinstance(updated_data, dict) and updated_data:
                return updated_data

            # Fallback: fazer SELECT separado para obter a nota atualizada
            log.debug(f"Update não retornou dados, fazendo SELECT separado para nota {note_id}")
            resp_get = exec_postgrest(supa.table("rc_notes").select(RC_NOTES_SELECT_FIELDS).eq("id", note_id).limit(1))

            rows = resp_get.data or []
            if not rows:
                raise ValueError(f"Nota {note_id} não encontrada ou sem permissão")

            return rows[0]

        except Exception as e:
            # P1: Retry automático se erro 42703 (schema drift)
            if is_schema_drift_error(e):
                log.warning(f"Schema drift detectado (42703) para nota {note_id}, retry com campos SAFE")
                try:
                    resp_get = exec_postgrest(
                        supa.table("rc_notes").select(RC_NOTES_SELECT_FIELDS_SAFE).eq("id", note_id).limit(1)
                    )
                    rows = resp_get.data or []
                    if rows:
                        return rows[0]
                except Exception as retry_err:
                    log.error(f"Erro no retry com campos SAFE: {retry_err}")

            log.error(f"Erro ao atualizar nota {note_id}: {e}")
            raise

    def delete_note(self, note_id: str) -> None:
        """Deleta nota (se políticas RLS permitirem).

        Nota: A migração original define rc_notes como append-only,
        sem política de DELETE. Este método existe para compatibilidade
        com o controller mas pode falhar com erro de permissão.

        Args:
            note_id: UUID da nota

        Raises:
            NotesAuthError: Se política RLS bloquear DELETE
        """
        from infra.supabase_client import exec_postgrest, get_supabase

        supa = get_supabase()

        try:
            exec_postgrest(supa.table("rc_notes").delete().eq("id", note_id))
            log.info(f"Nota {note_id} deletada com sucesso")

        except Exception as e:
            log.error(f"Erro ao deletar nota {note_id}: {e}")
            raise

    def list_notes(self, org_id: str, limit: int = 500) -> list[dict[str, Any]]:
        """Lista notas da organização.

        Args:
            org_id: UUID da organização
            limit: Número máximo de registros

        Returns:
            Lista de notas
        """
        return notes_service.list_notes(org_id=org_id, limit=limit)
