# -*- coding: utf-8 -*-
"""Adaptadores headless para client_form.

Este módulo contém classes adaptadoras que fazem a ponte entre a UI (Tkinter)
e a lógica de negócio do formulário de clientes. Extraídas de client_form.py
para facilitar testabilidade e reutilização.

Refatoração: UI-DECOUPLE-CLIENT-FORM-001 (Fase 1)
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Adaptadores de UI → Lógica (Headless onde possível)
# =============================================================================


class TkMessageAdapter:
    """Adaptador para messagebox do Tkinter.

    Fornece interface unificada para exibir mensagens ao usuário,
    abstraindo o uso direto de tkinter.messagebox.
    """

    def __init__(self, parent: tk.Misc | None = None) -> None:
        """Inicializa o adaptador.

        Args:
            parent: Widget pai para centralizar diálogos (opcional).
        """
        self.parent = parent

    def warn(self, title: str, message: str) -> None:
        """Exibe aviso ao usuário."""
        messagebox.showwarning(title, message, parent=self.parent)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Pergunta sim/não ao usuário."""
        return messagebox.askokcancel(title, message, parent=self.parent)

    def show_error(self, title: str, message: str) -> None:
        """Exibe erro ao usuário."""
        messagebox.showerror(title, message, parent=self.parent)

    def show_info(self, title: str, message: str) -> None:
        """Exibe informação ao usuário."""
        messagebox.showinfo(title, message, parent=self.parent)


class FormDataAdapter:
    """Adaptador para coletar dados do formulário Tkinter.

    Encapsula a coleta de valores de widgets do formulário,
    permitindo testar lógica de negócio sem depender de widgets reais.
    """

    def __init__(self, ents: dict[str, tk.Widget], status_var: tk.StringVar) -> None:
        """Inicializa o adaptador.

        Args:
            ents: Dicionário de widgets do formulário (nome_campo -> widget).
            status_var: Variável Tkinter com status selecionado.
        """
        self.ents = ents
        self.status_var = status_var

    def collect(self) -> dict[str, str]:
        """Coleta valores de todos os campos do formulário.

        Returns:
            Dicionário com valores coletados (nome_campo -> valor).
        """
        from ._collect import coletar_valores

        return coletar_valores(self.ents)

    def get_status(self) -> str:
        """Obtém status selecionado no dropdown."""
        return self.status_var.get().strip()


class EditFormState:
    """Estado do formulário de edição de cliente.

    Gerencia estado interno do formulário: se é novo, se foi modificado,
    qual o ID do cliente, etc. Separado da UI para facilitar testes.
    """

    def __init__(
        self,
        client_id: int | None,
        on_save_silent: Callable[[], bool] | None = None,
        initializing_flag: list[bool] | None = None,
    ) -> None:
        """Inicializa o estado do formulário.

        Args:
            client_id: ID do cliente (None se novo).
            on_save_silent: Callback para salvamento silencioso (opcional).
            initializing_flag: Flag compartilhada de inicialização (opcional).
        """
        self.client_id: int | None = client_id
        self.is_dirty: bool = False
        self._on_save_silent = on_save_silent
        self._initializing_flag = initializing_flag or [False]

    def mark_dirty(self, *_args: Any, **_kwargs: Any) -> None:
        """Marca formulário como modificado (dirty).

        Ignora mudanças durante inicialização para evitar falsos positivos.
        """
        if self._initializing_flag[0]:
            return
        if not self.is_dirty:
            self.is_dirty = True

    def mark_clean(self) -> None:
        """Marca formulário como não modificado (clean)."""
        if self.is_dirty:
            self.is_dirty = False

    def save_silent(self) -> bool:
        """Salva formulário silenciosamente (sem mensagens/fechar).

        Returns:
            True se salvamento foi bem-sucedido, False caso contrário.
        """
        if self._on_save_silent is None:
            logger.warning("save_silent chamado mas callback não configurado")
            return False
        return self._on_save_silent()


class TkClientPersistence:
    """Adaptador para persistir cliente antes do upload.

    Usado no fluxo "Salvar e Enviar" para garantir que cliente novo
    seja salvo antes de iniciar upload de documentos.
    """

    def __init__(
        self,
        state: EditFormState,
        on_persist_client: Callable[[], bool],
        on_update_row: Callable[[int], None] | None = None,
    ) -> None:
        """Inicializa o adaptador.

        Args:
            state: Estado do formulário.
            on_persist_client: Callback para persistir cliente.
            on_update_row: Callback para atualizar row nonlocal (opcional).
        """
        self.state = state
        self._on_persist_client = on_persist_client
        self._on_update_row = on_update_row

    def persist_if_new(self, client_id: int | None) -> tuple[bool, int | None]:
        """Salva o cliente se for novo, retorna (success, client_id).

        Args:
            client_id: ID do cliente (None se novo).

        Returns:
            Tupla (sucesso, client_id_final).
        """
        if client_id is not None:
            return (True, client_id)

        # Cliente novo: salvar
        created_ok = self._on_persist_client()
        if not created_ok:
            return (False, None)

        # Atualizar row nonlocal (se callback fornecido)
        if self._on_update_row and self.state.client_id is not None:
            try:
                self._on_update_row(self.state.client_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao atualizar row apos criacao: %s", exc)

        # Marcar estado como limpo
        try:
            self.state.is_dirty = False
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao marcar estado limpo apos criacao: %s", exc)

        return (True, self.state.client_id)


class TkUploadExecutor:
    """Adaptador que delega para a lógica de upload unificada."""

    def __init__(self, state: EditFormState) -> None:
        """Inicializa o executor de upload.

        Args:
            state: Estado do formulário.
        """
        self.state = state

    def execute_upload(
        self,
        host: Any,
        row: tuple[Any, ...] | None,  # noqa: ARG002 - Interface compatibility
        ents: dict[str, Any],
        arquivos_selecionados: list | None,  # noqa: ARG002 - Interface compatibility
        win: Any,
        **kwargs: Any,  # noqa: ARG002 - Interface compatibility
    ) -> Any:
        """Executa upload delegando para módulo de upload unificado.

        Args:
            host: Widget host.
            row: Row do cliente (opcional).
            ents: Dicionário de widgets do formulário.
            arquivos_selecionados: Lista de arquivos selecionados (opcional).
            win: Janela do formulário.
            **kwargs: Argumentos adicionais.

        Returns:
            None (upload é assíncrono).
        """
        parent_widget = win or host

        # Importar helpers de formatação e lógica de upload
        from src.modules.clientes.forms.client_form_upload_helpers import (
            execute_upload_flow,
        )

        # Delegar para helper headless
        try:
            execute_upload_flow(
                parent_widget=parent_widget,
                ents=ents,
                client_id=self.state.client_id,
                host=host,
            )
        except Exception as exc:
            logger.exception("Erro durante upload de documentos")
            messagebox.showerror("Erro", f"Erro durante upload: {exc}", parent=parent_widget)

        return None


# =============================================================================
# Adaptadores para ação de Cartão CNPJ
# =============================================================================


class TkMessageSink:
    """Adaptador de mensagens para ação de Cartão CNPJ."""

    def __init__(self, parent: tk.Misc | None = None) -> None:
        """Inicializa o adaptador.

        Args:
            parent: Widget pai para centralizar diálogos.
        """
        self.parent = parent

    def warn(self, title: str, message: str) -> None:
        """Exibe aviso ao usuário."""
        messagebox.showwarning(title, message, parent=self.parent)

    def info(self, title: str, message: str) -> None:
        """Exibe informação ao usuário."""
        messagebox.showinfo(title, message, parent=self.parent)


class TkDirectorySelector:
    """Adaptador para seleção de diretório via Tkinter."""

    def __init__(self, parent: tk.Misc | None = None) -> None:
        """Inicializa o seletor.

        Args:
            parent: Widget pai para centralizar diálogo.
        """
        self.parent = parent

    def select_directory(self, title: str) -> str | None:
        """Abre diálogo para selecionar diretório.

        Args:
            title: Título do diálogo.

        Returns:
            Caminho do diretório selecionado, ou None se cancelado.
        """
        return filedialog.askdirectory(title=title, parent=self.parent)


class TkFormFieldSetter:
    """Adaptador para preencher campos do formulário."""

    def __init__(self, ents: dict[str, tk.Widget]) -> None:
        """Inicializa o setter.

        Args:
            ents: Dicionário de widgets do formulário.
        """
        self.ents = ents

    def set_value(self, field_name: str, value: str) -> None:
        """Define valor em campo do formulário.

        Args:
            field_name: Nome do campo.
            value: Valor a ser definido.
        """
        if field_name in self.ents:
            widget = self.ents[field_name]
            widget.delete(0, "end")
            widget.insert(0, value)
