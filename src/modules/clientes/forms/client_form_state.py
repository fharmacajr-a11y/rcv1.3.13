# -*- coding: utf-8 -*-
"""Estado e validações do formulário de cliente.

Este módulo contém as estruturas de dados e lógica de estado do formulário,
separadas da UI e da lógica de negócio. Facilita testes e reutilização.

Refatoração: MICROFASE-11 (Divisão em 4 componentes)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols
# =============================================================================


class ClientFormStateLike(Protocol):
    """Interface de leitura para estado do formulário."""

    client_id: int | None
    is_new: bool
    is_dirty: bool
    row: tuple[Any, ...] | None


# =============================================================================
# Dataclasses de Estado
# =============================================================================


@dataclass
class ClientFormData:
    """Dados do formulário de cliente.

    Representa os valores dos campos do formulário, sem depender de widgets Tkinter.
    """

    razao_social: str = ""
    cnpj: str = ""
    nome: str = ""
    whatsapp: str = ""
    observacoes: str = ""
    status: str = ""

    # Campos internos (não persistidos no banco ainda)
    endereco: str = ""
    bairro: str = ""
    cidade: str = ""
    cep: str = ""

    def to_dict(self) -> dict[str, str]:
        """Converte para dicionário.

        Returns:
            Dicionário com todos os campos.
        """
        return {
            "Razão Social": self.razao_social,
            "CNPJ": self.cnpj,
            "Nome": self.nome,
            "WhatsApp": self.whatsapp,
            "Observações": self.observacoes,
            "Status do Cliente": self.status,
            "Endereço (interno):": self.endereco,
            "Bairro (interno):": self.bairro,
            "Cidade (interno):": self.cidade,
            "CEP (interno):": self.cep,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> ClientFormData:
        """Cria instância a partir de dicionário.

        Args:
            data: Dicionário com valores dos campos.

        Returns:
            Nova instância de ClientFormData.
        """
        return cls(
            razao_social=data.get("Razão Social", ""),
            cnpj=data.get("CNPJ", ""),
            nome=data.get("Nome", ""),
            whatsapp=data.get("WhatsApp", ""),
            observacoes=data.get("Observações", ""),
            status=data.get("Status do Cliente", ""),
            endereco=data.get("Endereço (interno):", ""),
            bairro=data.get("Bairro (interno):", ""),
            cidade=data.get("Cidade (interno):", ""),
            cep=data.get("CEP (interno):", ""),
        )

    @classmethod
    def from_row(cls, row: tuple[Any, ...] | None) -> ClientFormData:
        """Cria instância a partir de row do banco.

        Args:
            row: Tupla com dados do banco (pk, razao, cnpj, nome, numero, obs, ult).

        Returns:
            Nova instância de ClientFormData.
        """
        if not row or len(row) < 7:
            return cls()

        _, razao, cnpj, nome, numero, obs, _ = row[:7]

        # Extrair status das observações se houver prefixo
        status = ""
        observacoes_clean = obs or ""

        from src.modules.clientes.components.helpers import STATUS_PREFIX_RE

        if obs:
            m = STATUS_PREFIX_RE.match(obs)
            if m:
                status = m.group("st")
                observacoes_clean = STATUS_PREFIX_RE.sub("", obs, count=1).strip()

        return cls(
            razao_social=razao or "",
            cnpj=cnpj or "",
            nome=nome or "",
            whatsapp=numero or "",
            observacoes=observacoes_clean,
            status=status,
        )


@dataclass
class ClientFormValidation:
    """Resultado de validação do formulário.

    Contém erros e avisos de validação, sem depender de UI.
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Verifica se formulário é válido (sem erros).

        Returns:
            True se não há erros, False caso contrário.
        """
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """Verifica se há avisos.

        Returns:
            True se há avisos, False caso contrário.
        """
        return len(self.warnings) > 0

    def add_error(self, message: str) -> None:
        """Adiciona erro de validação.

        Args:
            message: Mensagem de erro.
        """
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Adiciona aviso de validação.

        Args:
            message: Mensagem de aviso.
        """
        self.warnings.append(message)

    def clear(self) -> None:
        """Limpa todos os erros e avisos."""
        self.errors.clear()
        self.warnings.clear()


@dataclass
class ClientFormState:
    """Estado completo do formulário de cliente.

    Centraliza todo o estado do formulário: dados, validação, flags.
    Separado da UI para facilitar testes e reutilização.
    """

    client_id: int | None = None
    """ID do cliente (None se novo)."""

    is_new: bool = True
    """Indica se é um novo cliente."""

    is_dirty: bool = False
    """Indica se o formulário foi modificado."""

    row: tuple[Any, ...] | None = None
    """Dados originais da linha do cliente."""

    data: ClientFormData = field(default_factory=ClientFormData)
    """Dados do formulário."""

    validation: ClientFormValidation = field(default_factory=ClientFormValidation)
    """Resultado de validação."""

    initializing: bool = True
    """Flag de inicialização (ignora dirty tracking)."""

    _on_save_silent: Callable[[], bool] | None = None
    """Callback para salvamento silencioso (opcional)."""

    def mark_dirty(self, *_args: Any, **_kwargs: Any) -> None:
        """Marca formulário como modificado (dirty).

        Ignora mudanças durante inicialização para evitar falsos positivos.
        """
        if self.initializing:
            return
        if not self.is_dirty:
            self.is_dirty = True
            logger.debug(f"[ClientFormState] Marcado como dirty (client_id={self.client_id})")

    def mark_clean(self) -> None:
        """Marca formulário como não modificado (clean)."""
        if self.is_dirty:
            self.is_dirty = False
            logger.debug(f"[ClientFormState] Marcado como clean (client_id={self.client_id})")

    def update_client_id(self, client_id: int | None) -> None:
        """Atualiza o ID do cliente e recalcula is_new.

        Args:
            client_id: Novo ID do cliente.
        """
        self.client_id = client_id
        self.is_new = client_id is None
        logger.debug(f"[ClientFormState] ID atualizado: {client_id} (is_new={self.is_new})")

    def load_from_row(self, row: tuple[Any, ...] | None) -> None:
        """Carrega dados de uma row do banco.

        Args:
            row: Tupla com dados do banco.
        """
        self.row = row
        self.data = ClientFormData.from_row(row)

        if row and len(row) > 0:
            try:
                self.update_client_id(int(row[0]))
            except (ValueError, TypeError):
                self.update_client_id(None)
        else:
            self.update_client_id(None)

        logger.debug(f"[ClientFormState] Dados carregados de row (client_id={self.client_id})")

    def load_from_preset(self, preset: dict[str, str] | None) -> None:
        """Carrega dados de um preset (ex: novo cliente com CNPJ pré-preenchido).

        Args:
            preset: Dicionário com valores pré-preenchidos.
        """
        if not preset:
            return

        if preset.get("razao"):
            self.data.razao_social = preset["razao"]
        if preset.get("cnpj"):
            self.data.cnpj = preset["cnpj"]

        logger.debug(f"[ClientFormState] Dados carregados de preset: {preset}")

    def validate(self) -> ClientFormValidation:
        """Valida dados do formulário.

        Returns:
            Objeto de validação com erros/avisos.
        """
        self.validation.clear()

        # Validação básica: campos obrigatórios
        if not self.data.razao_social.strip():
            self.validation.add_error("Razão Social é obrigatória")

        if not self.data.cnpj.strip():
            self.validation.add_error("CNPJ é obrigatório")

        # Validação de formato CNPJ (simplificada)
        cnpj_clean = re.sub(r"\D", "", self.data.cnpj)
        if self.data.cnpj.strip() and len(cnpj_clean) not in (11, 14):
            self.validation.add_warning("CNPJ/CPF com formato inválido")

        logger.debug(
            f"[ClientFormState] Validação: {len(self.validation.errors)} erros, {len(self.validation.warnings)} avisos"
        )

        return self.validation

    def save_silent(self) -> bool:
        """Salva formulário silenciosamente (sem mensagens/fechar).

        Returns:
            True se salvamento foi bem-sucedido, False caso contrário.
        """
        if self._on_save_silent is None:
            logger.warning("save_silent chamado mas callback não configurado")
            return False

        logger.debug(f"[ClientFormState] Executando save_silent (client_id={self.client_id})")
        return self._on_save_silent()

    def finish_initialization(self) -> None:
        """Marca fim da inicialização (habilita dirty tracking)."""
        self.initializing = False
        logger.debug(f"[ClientFormState] Inicialização concluída (client_id={self.client_id})")


# =============================================================================
# Funções Auxiliares
# =============================================================================


def build_window_title(
    state: ClientFormStateLike,
    razao_social: str = "",
    cnpj: str = "",
) -> str:
    """Constrói título da janela com base no estado.

    Args:
        state: Estado do formulário.
        razao_social: Razão social do cliente.
        cnpj: CNPJ do cliente.

    Returns:
        Título formatado para a janela.
    """
    parts: list[str] = ["Editar Cliente"]

    if state.client_id:
        parts.append(str(state.client_id))

    if razao_social:
        parts.append(razao_social)

    if cnpj:
        parts.append(cnpj)

    return " – ".join(parts)


def extract_address_fields(cliente_like: Any) -> dict[str, str]:
    """Extrai campos de endereço de objeto cliente-like.

    Args:
        cliente_like: Objeto com atributos de endereço (dict ou objeto).

    Returns:
        Dicionário com campos de endereço (endereco, bairro, cidade, cep).
    """

    def _addr_val(src: Any | None, *keys: str) -> str:
        if src is None:
            return ""
        for key in keys:
            if isinstance(src, dict) and key in src:
                val = src.get(key)
                if val:
                    return str(val)
            try:
                converted = str(getattr(src, key))
            except Exception:
                logger.debug("Falha ao converter atributo %r em string", key, exc_info=True)
            else:
                if converted:
                    return converted
        return ""

    return {
        "endereco": _addr_val(cliente_like, "endereco", "endereço", "address", "logradouro"),
        "bairro": _addr_val(cliente_like, "bairro", "district"),
        "cidade": _addr_val(cliente_like, "cidade", "city", "municipio"),
        "cep": _addr_val(cliente_like, "cep", "zip", "postal_code"),
    }
