# -*- coding: utf-8 -*-
"""
Módulo headless para lógica de preenchimento via Cartão CNPJ do formulário de clientes.

Este módulo extrai a lógica de extração e preenchimento de dados do Cartão CNPJ,
permitindo testabilidade independente de UI e reutilização em diferentes contextos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Protocols e Tipos
# -----------------------------------------------------------------------------


class MessageSink(Protocol):
    """Protocolo para exibir mensagens ao usuário."""

    def warn(self, title: str, message: str) -> None:
        """Exibe um aviso ao usuário."""
        ...

    def info(self, title: str, message: str) -> None:
        """Exibe uma informação ao usuário."""
        ...


class FormFieldSetter(Protocol):
    """Interface para preenchimento de campos do formulário de cliente."""

    def set_value(self, field_name: str, value: str) -> None:
        """Define o valor de um campo do formulário."""
        ...


class DirectorySelector(Protocol):
    """Protocolo para seleção de diretório (abstração da UI)."""

    def select_directory(self, title: str) -> str | None:
        """
        Abre diálogo de seleção de diretório.

        Returns:
            Caminho do diretório selecionado ou None se cancelado
        """
        ...


# -----------------------------------------------------------------------------
# Contexto e Dependências
# -----------------------------------------------------------------------------


@dataclass
class CnpjExtractionResult:
    """Resultado da extração de dados do Cartão CNPJ."""

    ok: bool
    """Indica se a extração foi bem-sucedida."""

    base_dir: str | None
    """Diretório base onde foi feita a busca."""

    cnpj: str | None = None
    """CNPJ extraído (apenas dígitos)."""

    razao_social: str | None = None
    """Razão social extraída."""

    error_message: str | None = None
    """Mensagem de erro se houver falha."""


@dataclass
class CnpjActionDeps:
    """Dependências externas para ações de Cartão CNPJ."""

    messages: MessageSink
    """Adaptador para exibir mensagens ao usuário."""

    field_setter: FormFieldSetter
    """Adaptador para preencher campos do formulário."""

    directory_selector: DirectorySelector
    """Adaptador para selecionar diretório."""


# -----------------------------------------------------------------------------
# Lógica de Negócio
# -----------------------------------------------------------------------------


def extract_cnpj_from_directory(base_dir: str) -> CnpjExtractionResult:
    """
    Extrai dados do Cartão CNPJ a partir de um diretório.

    Args:
        base_dir: Caminho do diretório contendo o Cartão CNPJ

    Returns:
        CnpjExtractionResult com os dados extraídos
    """
    from src.modules.clientes.core.service import extrair_dados_cartao_cnpj_em_pasta

    try:
        result = extrair_dados_cartao_cnpj_em_pasta(base_dir)
        cnpj = result.get("cnpj")
        razao_social = result.get("razao_social")

        if not cnpj and not razao_social:
            return CnpjExtractionResult(
                ok=False,
                base_dir=base_dir,
                error_message="Nenhum Cartão CNPJ válido encontrado.",
            )

        return CnpjExtractionResult(
            ok=True,
            base_dir=base_dir,
            cnpj=cnpj,
            razao_social=razao_social,
        )

    except Exception as exc:
        logger.exception("Erro ao extrair dados do Cartão CNPJ")
        return CnpjExtractionResult(
            ok=False,
            base_dir=base_dir,
            error_message=f"Erro ao processar Cartão CNPJ: {exc}",
        )


def apply_cnpj_data_to_form(
    result: CnpjExtractionResult,
    setter: FormFieldSetter,
) -> None:
    """
    Preenche campos do formulário a partir dos dados extraídos do Cartão CNPJ.

    Args:
        result: Resultado da extração de dados
        setter: Adaptador para setar valores nos campos
    """
    if not result.ok:
        logger.debug("Não há dados para aplicar (result.ok=False)")
        return

    # Normalizar CNPJ para apenas dígitos
    if result.cnpj:
        cnpj_digits = "".join(ch for ch in result.cnpj if ch.isdigit())
        setter.set_value("CNPJ", cnpj_digits)
        logger.debug("Campo CNPJ preenchido: %s", cnpj_digits)

    # Preencher razão social
    if result.razao_social:
        setter.set_value("Razão Social", result.razao_social)
        logger.debug("Campo Razão Social preenchido: %s", result.razao_social)


def handle_cartao_cnpj_action(deps: CnpjActionDeps) -> CnpjExtractionResult:
    """
    Fluxo completo de preenchimento via Cartão CNPJ.

    Este é o fluxo principal:
    1. Solicita seleção de diretório ao usuário
    2. Extrai dados do Cartão CNPJ do diretório
    3. Preenche campos do formulário
    4. Exibe mensagens apropriadas

    Args:
        deps: Dependências (messages, field_setter, directory_selector)

    Returns:
        CnpjExtractionResult com resultado da operação
    """
    # 1. Selecionar diretório
    base_dir = deps.directory_selector.select_directory("Escolha a pasta do cliente (com o Cartão CNPJ)")

    if not base_dir:
        logger.debug("Usuário cancelou seleção de diretório")
        return CnpjExtractionResult(
            ok=False,
            base_dir=None,
            error_message="Seleção cancelada",
        )

    # 2. Extrair dados
    result = extract_cnpj_from_directory(base_dir)

    # 3. Processar resultado
    if not result.ok:
        # Exibir aviso ao usuário
        deps.messages.warn("Atenção", result.error_message or "Falha ao extrair dados")
        return result

    # 4. Preencher formulário
    apply_cnpj_data_to_form(result, deps.field_setter)

    logger.info(
        "Cartão CNPJ processado com sucesso: CNPJ=%s, Razão=%s",
        result.cnpj,
        result.razao_social,
    )

    return result


__all__ = [
    "CnpjActionDeps",
    "CnpjExtractionResult",
    "DirectorySelector",
    "FormFieldSetter",
    "MessageSink",
    "apply_cnpj_data_to_form",
    "extract_cnpj_from_directory",
    "handle_cartao_cnpj_action",
]
