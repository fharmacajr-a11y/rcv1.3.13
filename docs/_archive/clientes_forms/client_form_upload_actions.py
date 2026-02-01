# -*- coding: utf-8 -*-
"""
Módulo headless para lógica de upload de documentos do formulário de clientes.

Este módulo extrai a lógica de preparação e execução de upload do client_form.py,
permitindo testabilidade independente de UI e reutilização em diferentes contextos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Protocols e Tipos
# -----------------------------------------------------------------------------


class UploadExecutor(Protocol):
    """Protocolo para executar o upload de documentos."""

    def execute_upload(
        self,
        host: Any,
        row: tuple[Any, ...] | None,
        ents: dict[str, Any],
        arquivos_selecionados: list | None,
        win: Any,
        **kwargs: Any,
    ) -> Any:
        """Executa o upload de documentos."""
        ...


class ClientPersistence(Protocol):
    """Protocolo para persistir o cliente antes do upload."""

    def persist_if_new(self, client_id: int | None) -> tuple[bool, int | None]:
        """
        Persiste o cliente se for novo.

        Returns:
            Tuple (success, client_id)
        """
        ...


# -----------------------------------------------------------------------------
# Contexto e Dependências
# -----------------------------------------------------------------------------


@dataclass
class UploadContext:
    """Contexto para upload de documentos."""

    client_id: int | None
    """ID do cliente (None se for novo)."""

    is_new: bool
    """Indica se é um cliente novo (precisa salvar antes)."""

    row: tuple[Any, ...] | None = None
    """Dados da linha do cliente."""

    ents: dict[str, Any] = field(default_factory=dict)
    """Entries/widgets do formulário."""

    arquivos_selecionados: list | None = None
    """Arquivos selecionados para upload (se já selecionados)."""

    win: Any = None
    """Janela pai (para UI)."""

    skip_duplicate_prompt: bool = True
    """Se True, pula prompt de duplicatas."""

    abort: bool = False
    """Flag para indicar que o fluxo deve ser abortado."""

    newly_created: bool = False
    """Indica se o cliente foi criado durante este fluxo."""

    error_message: str | None = None
    """Mensagem de erro se houver falha."""


@dataclass
class UploadDeps:
    """Dependências externas para upload."""

    executor: UploadExecutor
    """Executor de upload (abstração da UI)."""

    persistence: ClientPersistence
    """Serviço de persistência do cliente."""

    host: Any
    """Referência ao host (self do formulário)."""


# -----------------------------------------------------------------------------
# Lógica de Negócio
# -----------------------------------------------------------------------------


def prepare_upload_context(
    client_id: int | None,
    row: tuple[Any, ...] | None,
    ents: dict[str, Any],
    win: Any,
    arquivos_selecionados: list | None = None,
) -> UploadContext:
    """
    Prepara o contexto de upload a partir dos dados do formulário.

    Args:
        client_id: ID do cliente (None se for novo)
        row: Dados da linha
        ents: Entries do formulário
        win: Janela pai
        arquivos_selecionados: Arquivos já selecionados (opcional)

    Returns:
        UploadContext preparado
    """
    return UploadContext(
        client_id=client_id,
        is_new=(client_id is None),
        row=row,
        ents=ents,
        arquivos_selecionados=arquivos_selecionados,
        win=win,
        skip_duplicate_prompt=True,
    )


def execute_salvar_e_enviar(
    ctx: UploadContext,
    deps: UploadDeps,
) -> UploadContext:
    """
    Executa o fluxo de salvar e enviar documentos.

    Este é o fluxo principal:
    1. Se cliente for novo, salva primeiro
    2. Configura flags no host (para compatibilidade)
    3. Executa o upload via executor

    Args:
        ctx: Contexto de upload
        deps: Dependências

    Returns:
        Contexto atualizado com resultado
    """
    # 1. Garantir que cliente existe (salvar se novo)
    if ctx.is_new:
        logger.debug("Cliente novo detectado, salvando antes do upload")
        success, saved_id = deps.persistence.persist_if_new(ctx.client_id)

        if not success:
            logger.warning("Falha ao salvar cliente antes do upload")
            ctx.abort = True
            ctx.error_message = "Não foi possível salvar o cliente antes do upload"
            return ctx

        # Atualizar contexto com ID salvo
        ctx.client_id = saved_id
        ctx.is_new = False
        ctx.newly_created = True

        # Atualizar row se necessário
        if ctx.row is None and saved_id is not None:
            ctx.row = (saved_id,)

        logger.debug("Cliente salvo com ID: %s", saved_id)

    # 2. Configurar flags no host (compatibilidade com código existente)
    try:
        if hasattr(deps.host, "_force_client_id_for_upload"):
            deps.host._force_client_id_for_upload = ctx.client_id
        if ctx.newly_created and hasattr(deps.host, "_upload_force_is_new"):
            deps.host._upload_force_is_new = True
    except Exception as exc:
        logger.debug("Falha ao configurar flags de upload no host: %s", exc)

    # 3. Executar upload
    try:
        logger.debug("Iniciando upload de documentos para cliente %s", ctx.client_id)
        deps.executor.execute_upload(
            host=deps.host,
            row=ctx.row,
            ents=ctx.ents,
            arquivos_selecionados=ctx.arquivos_selecionados,
            win=ctx.win,
            skip_duplicate_prompt=ctx.skip_duplicate_prompt,
        )
        logger.debug("Upload concluído com sucesso")

    except Exception as exc:
        logger.exception("Erro durante upload de documentos")
        ctx.abort = True
        ctx.error_message = f"Erro durante upload: {exc}"

    return ctx


__all__ = [
    "ClientPersistence",
    "UploadContext",
    "UploadDeps",
    "UploadExecutor",
    "execute_salvar_e_enviar",
    "prepare_upload_context",
]
