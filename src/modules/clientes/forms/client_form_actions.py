# -*- coding: utf-8 -*-
"""
Módulo headless (sem Tkinter) para lógica de negócio do formulário de clientes.

Este módulo extrai a lógica de salvar/enviar clientes do client_form.py,
permitindo testabilidade independente de UI e reutilização em diferentes contextos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.modules.clientes.components.status import apply_status_prefix
from src.modules.clientes.service import (
    checar_duplicatas_para_form,
    salvar_cliente_a_partir_do_form,
)
from ._dupes import (
    ask_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Protocols e Tipos
# -----------------------------------------------------------------------------


class MessageSink(Protocol):
    """Protocolo para exibir mensagens (warning, info, etc.), sem depender de Tk diretamente."""

    def warn(self, title: str, message: str) -> None:
        """Exibe um aviso ao usuário."""
        ...

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Pergunta sim/não ao usuário."""
        ...

    def show_error(self, title: str, message: str) -> None:
        """Exibe um erro ao usuário."""
        ...

    def show_info(self, title: str, message: str) -> None:
        """Exibe uma informação ao usuário."""
        ...


class FormDataCollector(Protocol):
    """Protocolo para coletar dados do formulário."""

    def collect(self) -> dict[str, str]:
        """Coleta valores dos campos do formulário."""
        ...

    def get_status(self) -> str:
        """Retorna o status selecionado."""
        ...


# -----------------------------------------------------------------------------
# Contexto e Dependências
# -----------------------------------------------------------------------------


@dataclass
class ClientFormContext:
    """Contexto mínimo para salvar/enviar um cliente."""

    is_new: bool
    """Indica se é um novo cliente (True) ou edição (False)."""

    client_id: int | None
    """ID do cliente sendo editado (None para novo cliente)."""

    abort: bool = False
    """Flag para indicar que o fluxo deve ser abortado."""

    saved_id: int | None = None
    """ID do cliente após salvar (preenchido pelo perform_save)."""

    error_message: str | None = None
    """Mensagem de erro se houver falha."""

    row: tuple[Any, ...] | None = None
    """Dados originais da linha (para edição)."""

    form_values: dict[str, str] = field(default_factory=dict)
    """Valores coletados do formulário."""

    duplicate_check_exclude_id: int | None = None
    """ID a excluir da checagem de duplicidade (normalmente o próprio cliente)."""


@dataclass
class ClientFormDeps:
    """Dependências externas usadas pelas ações do formulário."""

    messages: MessageSink
    """Adaptador para exibir mensagens ao usuário."""

    data_collector: FormDataCollector
    """Coletor de dados do formulário."""

    parent_window: Any | None = None
    """Referência à janela pai (para messageboxes do Tkinter)."""


# -----------------------------------------------------------------------------
# Lógica de Negócio
# -----------------------------------------------------------------------------


def _check_duplicates(
    ctx: ClientFormContext,
    deps: ClientFormDeps,
) -> bool:
    """
    Verifica duplicatas de CNPJ/Razão Social.

    Retorna True se pode prosseguir, False se deve abortar.
    """
    exclude_id = ctx.duplicate_check_exclude_id or ctx.client_id

    info = checar_duplicatas_para_form(
        ctx.form_values,
        row=ctx.row,
        exclude_id=exclude_id,
    )

    # Conflito de CNPJ é bloqueante
    if has_cnpj_conflict(info):
        show_cnpj_warning_and_abort(deps.parent_window, info)
        return False

    # Conflito de Razão Social permite confirmação
    if has_razao_conflict(info):
        if not ask_razao_confirm(deps.parent_window, info):
            return False

    return True


def perform_save(
    ctx: ClientFormContext,
    deps: ClientFormDeps,
    *,
    show_success: bool = False,
) -> ClientFormContext:
    """
    Fluxo principal de salvar: collect -> dupes -> save.

    Args:
        ctx: Contexto com dados do cliente
        deps: Dependências externas
        show_success: Se True, exibe mensagem de sucesso após salvar

    Returns:
        Contexto atualizado com resultado da operação
    """
    # 1. Coletar valores do formulário
    try:
        raw_values = deps.data_collector.collect()
        status_chosen = deps.data_collector.get_status()

        # Aplicar prefixo de status nas observações
        obs = raw_values.get("Observações", "")
        raw_values["Observações"] = apply_status_prefix(obs, status_chosen)

        ctx.form_values = raw_values
    except Exception as exc:
        logger.exception("Erro ao coletar valores do formulário")
        ctx.abort = True
        ctx.error_message = f"Erro ao coletar dados: {exc}"
        return ctx

    # 2. Verificar duplicatas
    if not _check_duplicates(ctx, deps):
        ctx.abort = True
        return ctx

    # 3. Salvar no banco
    try:
        saved_id, _ = salvar_cliente_a_partir_do_form(ctx.row, ctx.form_values)
        ctx.saved_id = saved_id
        ctx.client_id = saved_id
        ctx.abort = False

        if show_success:
            deps.messages.show_info("Sucesso", "Cliente salvo.")

    except Exception as exc:
        logger.exception("Erro ao salvar cliente")
        ctx.abort = True
        ctx.error_message = str(exc)
        deps.messages.show_error("Erro", str(exc))
        return ctx

    return ctx


def salvar(ctx: ClientFormContext, deps: ClientFormDeps) -> ClientFormContext:
    """
    Wrapper para o botão 'Salvar' (com mensagem de sucesso).
    """
    return perform_save(ctx, deps, show_success=True)


def salvar_silencioso(
    ctx: ClientFormContext,
    deps: ClientFormDeps,
) -> ClientFormContext:
    """
    Salva sem mostrar mensagem de sucesso (usado antes de enviar).
    """
    return perform_save(ctx, deps, show_success=False)


def salvar_e_enviar(
    ctx: ClientFormContext,
    deps: ClientFormDeps,
) -> ClientFormContext:
    """
    Wrapper para 'Salvar e enviar'.

    Se o cliente ainda não existe, salva primeiro (silencioso).
    A lógica de upload é tratada separadamente (fora deste módulo).
    """
    if ctx.client_id is None:
        # Cliente novo: precisa salvar antes de enviar
        return salvar_silencioso(ctx, deps)

    # Cliente já existe: apenas retorna o contexto
    # (o upload será tratado pelo caller)
    return ctx


__all__ = [
    "ClientFormContext",
    "ClientFormDeps",
    "FormDataCollector",
    "MessageSink",
    "perform_save",
    "salvar",
    "salvar_e_enviar",
    "salvar_silencioso",
]
