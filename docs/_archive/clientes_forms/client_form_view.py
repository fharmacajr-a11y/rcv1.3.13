from __future__ import annotations

from src.ui.ctk_config import ctk

# -*- coding: utf-8 -*-
"""View pura para o formulário de cliente.

Este módulo contém apenas a lógica de UI (Tkinter) do formulário de clientes,
sem lógica de negócio. Seguindo padrão MVC/MVVM para separação de responsabilidades.

Refatoração: MICROFASE-11 (Divisão em 4 componentes)
"""

import logging
import tkinter as tk
from typing import Any, Protocol

from src.modules.clientes.core.constants import STATUS_CHOICES
from src.ui.window_utils import show_centered
from .client_form_ui_builders import (
    apply_light_selection,
    bind_dirty_tracking,
    create_button_bar,
    create_labeled_entry,
    create_labeled_text,
    create_status_dropdown,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols
# =============================================================================


class FormEventHandlers(Protocol):
    """Protocol para handlers de eventos do formulário."""

    def on_save(self) -> None:
        """Handler para botão Salvar."""
        ...

    def on_save_and_upload(self) -> None:
        """Handler para botão Salvar e Enviar."""
        ...

    def on_cartao_cnpj(self) -> None:
        """Handler para botão Cartão CNPJ."""
        ...

    def on_cancel(self) -> None:
        """Handler para botão Cancelar."""
        ...

    def on_senhas(self) -> None:
        """Handler para botão Senhas."""
        ...

    def on_dirty(self, *args: Any) -> None:  # noqa: ARG002 - Protocol compatibility
        """Handler para marcação de dirty state."""
        ...


# =============================================================================
# View Principal
# =============================================================================


class ClientFormView:
    """View pura do formulário de cliente (UI Tkinter).

    Responsabilidades:
    - Criar e organizar widgets
    - Configurar layout (grid)
    - Bindear eventos → handlers externos
    - Prover métodos de atualização visual (título, estado de botões)

    Não contém:
    - Lógica de negócio
    - Validações
    - Chamadas a services/repos
    - Estado de dados (apenas referências a widgets)
    """

    def __init__(
        self,
        parent: tk.Misc,
        handlers: FormEventHandlers,
        *,
        transient: bool = True,
    ) -> None:
        """Inicializa a view do formulário.

        Args:
            parent: Widget pai (geralmente MainWindow).
            handlers: Objeto com handlers de eventos do formulário.
            transient: Se True, cria janela transient ao parent.
        """
        self.parent = parent
        self.handlers = handlers

        # Referências a widgets principais
        self.window: tk.Toplevel | None = None
        self.ents: dict[str, tk.Widget] = {}
        self.status_var: tk.StringVar | None = None
        self.internal_vars: dict[str, tk.StringVar] = {}
        self.internal_entries: dict[str, ctk.CTkEntry] = {}

        # Referências a botões para controle de estado
        self.btn_upload: ctk.CTkButton | None = None
        self.btn_cartao_cnpj: ctk.CTkButton | None = None

        # Criar a janela
        self._create_window(transient=transient)

    def _create_window(self, transient: bool = True) -> None:
        """Cria a janela principal do formulário."""
        try:
            parent_window: tk.Misc = self.parent.winfo_toplevel()  # type: ignore[assignment]
        except Exception:
            parent_window = self.parent

        self.window = tk.Toplevel(parent_window)

        # Import tardio para permitir patch em testes (Fase 2)
        from . import client_form as client_form_mod

        client_form_mod.apply_rc_icon(self.window)

        self.window.withdraw()

        if transient:
            try:
                self.window.transient(parent_window)
            except Exception:
                self.window.transient(self.parent)

        self.window.resizable(False, False)
        self.window.minsize(940, 520)
        self.window.protocol("WM_DELETE_WINDOW", self.handlers.on_cancel)

    def build_ui(self) -> None:
        """Constrói toda a interface do formulário.

        Organizado em etapas:
        1. Frame principal e divisões
        2. Painel esquerdo (campos principais)
        3. Painel direito (campos internos)
        4. Barra de botões
        5. Layout (grid)
        6. Bindings de dirty tracking
        """
        if not self.window:
            raise RuntimeError("Window not created")

        # Frame principal
        main_frame = ctk.CTkFrame(self.window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 2))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        # Divisão esquerda/direita
        left_frame = ctk.CTkFrame(main_frame)
        sep = ctk.CTkFrame(main_frame, width=2)  # Separador vertical
        right_frame = ctk.CTkFrame(main_frame)

        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=0)
        main_frame.columnconfigure(2, weight=4)
        main_frame.rowconfigure(0, weight=1)

        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        sep.grid(row=0, column=1, sticky="ns", padx=(0, 0), pady=10)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)

        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # Construir painéis
        self._build_left_panel(left_frame)
        self._build_right_panel(right_frame)
        self._build_buttons()

        # Aplicar seleção visual clara
        self._setup_visual_enhancements()

        # Configurar dirty tracking
        self._setup_dirty_tracking()

    def _build_left_panel(self, parent: tk.Widget) -> None:
        """Constrói painel esquerdo com campos principais.

        Args:
            parent: Frame pai onde criar os widgets.
        """
        row_idx = 0

        # Razão Social
        lbl_razao, ent_razao, row_idx = create_labeled_entry(parent, "Razão Social:", row_idx)
        self.ents["Razão Social"] = ent_razao

        # CNPJ
        lbl_cnpj, ent_cnpj, row_idx = create_labeled_entry(parent, "CNPJ:", row_idx, pady_label=(0, 0))
        self.ents["CNPJ"] = ent_cnpj

        # Nome
        lbl_nome, ent_nome, row_idx = create_labeled_entry(parent, "Nome:", row_idx, pady_label=(0, 0))
        self.ents["Nome"] = ent_nome

        # WhatsApp
        lbl_whats, ent_whats, row_idx = create_labeled_entry(parent, "WhatsApp:", row_idx, pady_label=(0, 0))
        self.ents["WhatsApp"] = ent_whats

        # Observações
        lbl_obs, ent_obs, obs_row_for_weight, row_idx = create_labeled_text(parent, "Observações:", row_idx)
        self.ents["Observações"] = ent_obs

        # Peso da linha de observações
        parent.rowconfigure(obs_row_for_weight, weight=1)
        parent.columnconfigure(0, weight=1)

        # Status do Cliente
        status_frame, cb_status, status_var, btn_senhas = create_status_dropdown(
            parent,
            "Status do Cliente:",
            STATUS_CHOICES,
            self.handlers.on_senhas,
        )
        status_frame.grid(row=row_idx, column=0, columnspan=1, sticky="ew", padx=6, pady=(6, 6))
        self.ents["Status do Cliente"] = cb_status
        self.status_var = status_var

    def _build_right_panel(self, parent: tk.Widget) -> None:
        """Constrói painel direito com campos internos (endereço).

        Args:
            parent: Frame pai onde criar os widgets.
        """
        # Campos internos (não persistidos no banco ainda)
        addr_endereco_var = tk.StringVar(value="")
        addr_bairro_var = tk.StringVar(value="")
        addr_cidade_var = tk.StringVar(value="")
        addr_cep_var = tk.StringVar(value="")

        self.internal_vars = {
            "endereco": addr_endereco_var,
            "bairro": addr_bairro_var,
            "cidade": addr_cidade_var,
            "cep": addr_cep_var,
        }

        right_row = 0

        # Endereço
        ctk.CTkLabel(parent, text="Endereço (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(5, 0))
        right_row += 1
        ent_endereco = ctk.CTkEntry(parent, textvariable=addr_endereco_var)
        ent_endereco.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["Endereço (interno):"] = ent_endereco
        self.internal_entries["Endereço (interno):"] = ent_endereco
        right_row += 1

        # Bairro
        ctk.CTkLabel(parent, text="Bairro (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
        right_row += 1
        ent_bairro = ctk.CTkEntry(parent, textvariable=addr_bairro_var)
        ent_bairro.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["Bairro (interno):"] = ent_bairro
        self.internal_entries["Bairro (interno):"] = ent_bairro
        right_row += 1

        # Cidade
        ctk.CTkLabel(parent, text="Cidade (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
        right_row += 1
        ent_cidade = ctk.CTkEntry(parent, textvariable=addr_cidade_var)
        ent_cidade.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["Cidade (interno):"] = ent_cidade
        self.internal_entries["Cidade (interno):"] = ent_cidade
        right_row += 1

        # CEP
        ctk.CTkLabel(parent, text="CEP (interno):").grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
        right_row += 1
        ent_cep = ctk.CTkEntry(parent, textvariable=addr_cep_var)
        ent_cep.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["CEP (interno):"] = ent_cep
        self.internal_entries["CEP (interno):"] = ent_cep
        right_row += 1

        parent.rowconfigure(right_row, weight=1)

        # Anexar vars e entries ao parent e window para compatibilidade
        if self.window:
            parent._rc_internal_notes_vars = self.internal_vars  # type: ignore[attr-defined]
            parent._rc_internal_notes_entries = self.internal_entries  # type: ignore[attr-defined]
            self.window._rc_internal_notes_vars = self.internal_vars  # type: ignore[attr-defined]
            self.window._rc_internal_notes_entries = self.internal_entries  # type: ignore[attr-defined]

    def _build_buttons(self) -> None:
        """Constrói barra de botões na parte inferior."""
        if not self.window:
            return

        btns = ctk.CTkFrame(self.window)
        btns.grid(row=1, column=0, columnspan=3, sticky="w", pady=10, padx=10)

        # Criar barra de botões usando builder
        buttons = create_button_bar(
            btns,
            on_save=self.handlers.on_save,
            on_save_and_upload=self.handlers.on_save_and_upload,
            on_cartao_cnpj=self.handlers.on_cartao_cnpj,
            on_cancel=self.handlers.on_cancel,
        )

        self.btn_cartao_cnpj = buttons["cartao_cnpj"]
        self.btn_upload = buttons["upload"]

    def _setup_visual_enhancements(self) -> None:
        """Aplica melhorias visuais (seleção clara, etc.)."""
        selection_targets = [
            self.ents.get("Razão Social"),
            self.ents.get("CNPJ"),
            self.ents.get("Nome"),
            self.ents.get("WhatsApp"),
            self.ents.get("Observações"),
            self.ents.get("Endereço (interno):"),
            self.ents.get("Bairro (interno):"),
            self.ents.get("Cidade (interno):"),
            self.ents.get("CEP (interno):"),
        ]

        for widget in selection_targets:
            if widget:
                apply_light_selection(widget)

    def _setup_dirty_tracking(self) -> None:
        """Configura bindings para dirty tracking em todos os campos."""
        for widget in self.ents.values():
            bind_dirty_tracking(widget, self.handlers.on_dirty)

        # Status combobox
        if self.status_var:
            cb_status = self.ents.get("Status do Cliente")
            if cb_status:
                cb_status.bind("<<ComboboxSelected>>", self.handlers.on_dirty, add="+")
            self.status_var.trace_add("write", lambda *_: self.handlers.on_dirty())

    # =========================================================================
    # Métodos Públicos para Controller
    # =========================================================================

    def show(self) -> None:
        """Exibe a janela centralizada e em foco."""
        if not self.window:
            return

        logger.debug("[ClientFormView] Antes de update_idletasks()")
        self.window.update_idletasks()
        logger.debug("[ClientFormView] Antes de show_centered()")
        show_centered(self.window)
        logger.debug("[ClientFormView] Após show_centered()")

        # Verifica estado da janela
        try:
            window_state = self.window.state()
            geometry = self.window.geometry()
            logger.debug(f"[ClientFormView] Janela exibida: state={window_state}, geometry={geometry}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ClientFormView] Não foi possível verificar estado: {exc}")

        self.window.grab_set()
        self.window.focus_force()

    def close(self) -> None:
        """Fecha a janela."""
        if self.window:
            self.window.destroy()

    def update_title(self, title: str) -> None:
        """Atualiza título da janela.

        Args:
            title: Novo título da janela.
        """
        if self.window:
            self.window.title(title)

    def set_upload_button_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita botão de upload.

        Args:
            enabled: True para habilitar, False para desabilitar.
        """
        if not self.btn_upload:
            return

        try:
            if enabled:
                self.btn_upload.state(["!disabled"])
            else:
                self.btn_upload.state(["disabled"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao alterar estado do botão de upload: %s", exc)
            try:
                self.btn_upload.configure(state="normal" if enabled else "disabled")
            except Exception as inner_exc:  # noqa: BLE001
                logger.debug("Falha ao configurar estado fallback do botão de upload: %s", inner_exc)

    def set_cartao_cnpj_button_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita botão Cartão CNPJ.

        Args:
            enabled: True para habilitar, False para desabilitar.
        """
        if not self.btn_cartao_cnpj:
            return

        try:
            if enabled:
                self.btn_cartao_cnpj.state(["!disabled"])
            else:
                self.btn_cartao_cnpj.state(["disabled"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao alterar estado do botão Cartão CNPJ: %s", exc)
            try:
                self.btn_cartao_cnpj.configure(state="normal" if enabled else "disabled")
            except Exception as inner_exc:  # noqa: BLE001
                logger.debug("Falha ao configurar estado fallback do botão Cartão CNPJ: %s", inner_exc)

    def fill_fields(self, data: dict[str, str]) -> None:
        """Preenche campos do formulário com dados.

        Args:
            data: Dicionário com valores (nome_campo -> valor).
        """
        for field_name, value in data.items():
            widget = self.ents.get(field_name)
            if not widget:
                continue

            try:
                # Text widget
                if isinstance(widget, tk.Text):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", value or "")
                # Entry/Combobox
                else:
                    widget.delete(0, "end")
                    widget.insert(0, value or "")
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Falha ao preencher campo {field_name}: {exc}")

    def get_field_value(self, field_name: str) -> str:
        """Obtém valor de um campo.

        Args:
            field_name: Nome do campo.

        Returns:
            Valor do campo (string vazia se não encontrado).
        """
        widget = self.ents.get(field_name)
        if not widget:
            return ""

        try:
            if isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            else:
                return widget.get().strip()  # type: ignore[attr-defined]
        except Exception:
            return ""
