# -*- coding: utf-8 -*-
"""View CustomTkinter para formulário de cliente.

Este módulo fornece uma view moderna usando CustomTkinter (CTkToplevel),
mantendo 100% compatibilidade de contratos com ClientFormView original.

Refatoração: MICROFASE-5 (Forms com CustomTkinter)
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Any, Protocol

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

if TYPE_CHECKING:
    pass  # ctk já importado via src.ui.ctk_config

from src.modules.clientes.components.helpers import STATUS_CHOICES
from src.modules.clientes.appearance import ClientesThemeManager, LIGHT_PALETTE, DARK_PALETTE
from src.ui.window_utils import show_centered
from .client_form_ui_builders_ctk import (
    create_labeled_entry_ctk,
    create_labeled_textbox_ctk,
    create_status_dropdown_ctk,
    create_button_ctk,
    bind_dirty_tracking_ctk,
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
# View CustomTkinter Principal
# =============================================================================


class ClientFormViewCTK:
    """View CustomTkinter do formulário de cliente.

    Mantém mesma API pública que ClientFormView para compatibilidade,
    mas usa widgets CustomTkinter para visual moderno e integração com tema Light/Dark.

    Atributos públicos esperados pelo Controller:
        - window: CTkToplevel
        - ents: dict[str, tk.Widget] - mapa de widgets por label
        - status_var: tk.StringVar - variável do dropdown de status
        - internal_vars: dict[str, tk.StringVar] - vars de campos internos
        - internal_entries: dict[str, tk.Widget] - widgets de campos internos
        - btn_upload: CTkButton - botão Salvar e Enviar
        - btn_cartao_cnpj: CTkButton - botão Cartão CNPJ
    """

    def __init__(
        self,
        parent: tk.Misc,
        handlers: FormEventHandlers,
        *,
        transient: bool = True,
    ) -> None:
        """Inicializa a view CustomTkinter do formulário.

        Args:
            parent: Widget pai (geralmente MainWindow).
            handlers: Objeto com handlers de eventos do formulário.
            transient: Se True, cria janela transient ao parent.
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            raise RuntimeError("CustomTkinter não está disponível")

        self.parent = parent
        self.handlers = handlers

        # Theme manager para cores
        self.theme_manager = ClientesThemeManager()
        self.current_mode = self.theme_manager.load_mode()

        # NÃO usar ctk.set_appearance_mode direto (viola SSoT)
        # O GlobalThemeManager já definiu o modo global

        # Paleta atual
        self.palette = DARK_PALETTE if self.current_mode == "dark" else LIGHT_PALETTE

        # Referências a widgets principais (CONTRATO COM CONTROLLER)
        self.window: ctk.CTkToplevel | None = None
        self.ents: dict[str, tk.Widget] = {}
        self.status_var: tk.StringVar | None = None
        self.internal_vars: dict[str, tk.StringVar] = {}
        self.internal_entries: dict[str, tk.Widget] = {}

        # Referências a botões para controle de estado
        self.btn_upload: ctk.CTkButton | None = None  # type: ignore[assignment]
        self.btn_cartao_cnpj: ctk.CTkButton | None = None  # type: ignore[assignment]

        # Criar a janela
        self._create_window(transient=transient)

    def _create_window(self, transient: bool = True) -> None:
        """Cria a janela CTkToplevel principal do formulário."""
        try:
            parent_window: tk.Misc = self.parent.winfo_toplevel()  # type: ignore[assignment]
        except Exception:
            parent_window = self.parent

        self.window = ctk.CTkToplevel(parent_window)  # type: ignore[arg-type]

        # Import tardio para permitir patch em testes (Fase 2)
        from . import client_form as client_form_mod

        client_form_mod.apply_rc_icon(self.window)

        self.window.withdraw()  # type: ignore[union-attr]

        if transient:
            try:
                self.window.transient(parent_window)  # type: ignore[union-attr]
            except Exception:
                self.window.transient(self.parent)  # type: ignore[union-attr]

        self.window.resizable(False, False)  # type: ignore[union-attr]
        self.window.minsize(940, 520)  # type: ignore[union-attr]
        self.window.protocol("WM_DELETE_WINDOW", self.handlers.on_cancel)  # type: ignore[union-attr]

        # Aplicar cor de fundo da janela
        self.window.configure(fg_color=self.palette["bg"])

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

        # Frame principal CustomTkinter
        main_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 2))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        # Divisão esquerda/direita
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        sep = ctk.CTkFrame(main_frame, width=2, fg_color=self.palette.get("entry_border", "#D0D0D0"))
        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")

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

        # Configurar dirty tracking
        self._setup_dirty_tracking()

    def _build_left_panel(self, parent: tk.Widget) -> None:
        """Constrói painel esquerdo com campos principais.

        Args:
            parent: Frame pai onde criar os widgets.
        """
        row_idx = 0

        # Cores para widgets CTk (tuplas light/dark)
        entry_fg_color = (self.palette["input_bg"], DARK_PALETTE["input_bg"])
        entry_text_color = (self.palette["input_text"], DARK_PALETTE["input_text"])
        entry_border_color = (self.palette["input_border"], DARK_PALETTE["input_border"])

        # Razão Social
        lbl_razao, ent_razao, row_idx = create_labeled_entry_ctk(
            parent,
            "Razão Social:",
            row_idx,
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        self.ents["Razão Social"] = ent_razao

        # CNPJ
        lbl_cnpj, ent_cnpj, row_idx = create_labeled_entry_ctk(
            parent,
            "CNPJ:",
            row_idx,
            pady_label=(0, 0),
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        self.ents["CNPJ"] = ent_cnpj

        # Nome
        lbl_nome, ent_nome, row_idx = create_labeled_entry_ctk(
            parent,
            "Nome:",
            row_idx,
            pady_label=(0, 0),
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        self.ents["Nome"] = ent_nome

        # WhatsApp
        lbl_whats, ent_whats, row_idx = create_labeled_entry_ctk(
            parent,
            "WhatsApp:",
            row_idx,
            pady_label=(0, 0),
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        self.ents["WhatsApp"] = ent_whats

        # Observações (CTkTextbox)
        lbl_obs, ent_obs, obs_row, row_idx = create_labeled_textbox_ctk(
            parent,
            "Observações:",
            row_idx,
            width=400,
            height=120,
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        self.ents["Observações"] = ent_obs

        # Peso da linha de observações
        parent.rowconfigure(obs_row, weight=1)
        parent.columnconfigure(0, weight=1)

        # Status do Cliente (CTkOptionMenu)
        self.status_var = tk.StringVar(value=STATUS_CHOICES[0])

        dropdown_fg_color = (self.palette["dropdown_bg"], DARK_PALETTE["dropdown_bg"])
        dropdown_button_color = (self.palette["control_bg"], DARK_PALETTE["control_bg"])
        dropdown_hover = (self.palette["control_hover"], DARK_PALETTE["control_hover"])
        dropdown_text_color = (self.palette["dropdown_text"], DARK_PALETTE["dropdown_text"])

        lbl_status, cb_status, row_idx = create_status_dropdown_ctk(
            parent,
            "Status do Cliente:",
            STATUS_CHOICES,
            row_idx,
            pady_label=(6, 0),
            pady_combo=(0, 6),
            fg_color=dropdown_button_color,
            button_color=dropdown_button_color,
            button_hover_color=dropdown_hover,
            dropdown_fg_color=dropdown_fg_color,
            text_color=dropdown_text_color,
            variable=self.status_var,
            command=self.handlers.on_dirty,
        )
        self.ents["Status do Cliente"] = cb_status

        # Botão Senhas (abaixo do status)
        btn_senhas = create_button_ctk(
            parent,
            text="🔑 Senhas",
            command=self.handlers.on_senhas,
            fg_color=(self.palette["control_bg"], DARK_PALETTE["control_bg"]),
            hover_color=(self.palette["control_hover"], DARK_PALETTE["control_hover"]),
            text_color=dropdown_text_color,
        )
        btn_senhas.grid(row=row_idx, column=0, padx=6, pady=(0, 6), sticky="ew")

    def _build_right_panel(self, parent: tk.Widget) -> None:
        """Constrói painel direito com campos internos (endereço).

        Args:
            parent: Frame pai onde criar os widgets.
        """
        # Cores para widgets CTk
        entry_fg_color = (self.palette["input_bg"], DARK_PALETTE["input_bg"])
        entry_text_color = (self.palette["input_text"], DARK_PALETTE["input_text"])
        entry_border_color = (self.palette["input_border"], DARK_PALETTE["input_border"])

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
        lbl_endereco = ctk.CTkLabel(parent, text="Endereço (interno):", anchor="w")
        lbl_endereco.grid(row=right_row, column=0, sticky="w", padx=6, pady=(5, 0))
        right_row += 1
        ent_endereco = ctk.CTkEntry(
            parent,
            textvariable=addr_endereco_var,
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        ent_endereco.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["Endereço (interno):"] = ent_endereco
        self.internal_entries["Endereço (interno):"] = ent_endereco
        right_row += 1

        # Bairro
        lbl_bairro = ctk.CTkLabel(parent, text="Bairro (interno):", anchor="w")
        lbl_bairro.grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
        right_row += 1
        ent_bairro = ctk.CTkEntry(
            parent,
            textvariable=addr_bairro_var,
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        ent_bairro.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["Bairro (interno):"] = ent_bairro
        self.internal_entries["Bairro (interno):"] = ent_bairro
        right_row += 1

        # Cidade
        lbl_cidade = ctk.CTkLabel(parent, text="Cidade (interno):", anchor="w")
        lbl_cidade.grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
        right_row += 1
        ent_cidade = ctk.CTkEntry(
            parent,
            textvariable=addr_cidade_var,
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
        ent_cidade.grid(row=right_row, column=0, padx=6, pady=(0, 5), sticky="ew")
        self.ents["Cidade (interno):"] = ent_cidade
        self.internal_entries["Cidade (interno):"] = ent_cidade
        right_row += 1

        # CEP
        lbl_cep = ctk.CTkLabel(parent, text="CEP (interno):", anchor="w")
        lbl_cep.grid(row=right_row, column=0, sticky="w", padx=6, pady=(0, 0))
        right_row += 1
        ent_cep = ctk.CTkEntry(
            parent,
            textvariable=addr_cep_var,
            fg_color=entry_fg_color,
            text_color=entry_text_color,
            border_color=entry_border_color,
        )
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
        """Constrói barra de botões do formulário."""
        if not self.window:
            raise RuntimeError("Window not created")

        btns = ctk.CTkFrame(self.window, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 8))

        # Cores dos botões
        accent_color = (self.palette["accent"], DARK_PALETTE["accent"])
        accent_hover = (self.palette["accent_hover"], DARK_PALETTE["accent_hover"])
        neutral_color = (self.palette["neutral_btn"], DARK_PALETTE["neutral_btn"])
        neutral_hover = (self.palette["neutral_hover"], DARK_PALETTE["neutral_hover"])
        danger_color = (self.palette["danger"], DARK_PALETTE["danger"])
        danger_hover = (self.palette["danger_hover"], DARK_PALETTE["danger_hover"])
        text_color = ("#FFFFFF", "#FFFFFF")

        # Salvar
        btn_salvar = create_button_ctk(
            btns,
            text="💾 Salvar",
            command=self.handlers.on_save,
            fg_color=accent_color,
            hover_color=accent_hover,
            text_color=text_color,
            width=120,
        )
        btn_salvar.pack(side="left", padx=2)

        # Salvar e Enviar
        self.btn_upload = create_button_ctk(
            btns,
            text="📤 Salvar e Enviar",
            command=self.handlers.on_save_and_upload,
            fg_color=accent_color,
            hover_color=accent_hover,
            text_color=text_color,
            width=150,
        )
        self.btn_upload.pack(side="left", padx=2)

        # Cartão CNPJ
        self.btn_cartao_cnpj = create_button_ctk(
            btns,
            text="🪪 Cartão CNPJ",
            command=self.handlers.on_cartao_cnpj,
            fg_color=neutral_color,
            hover_color=neutral_hover,
            text_color=(self.palette["fg"], DARK_PALETTE["fg"]),
            width=120,
        )
        self.btn_cartao_cnpj.pack(side="left", padx=2)

        # Cancelar
        btn_cancelar = create_button_ctk(
            btns,
            text="✖ Cancelar",
            command=self.handlers.on_cancel,
            fg_color=danger_color,
            hover_color=danger_hover,
            text_color=text_color,
            width=100,
        )
        btn_cancelar.pack(side="right", padx=2)

    def _setup_dirty_tracking(self) -> None:
        """Configura dirty tracking para todos os campos."""
        for widget in self.ents.values():
            bind_dirty_tracking_ctk(widget, self.handlers.on_dirty)

    def set_title(self, title: str) -> None:
        """Define o título da janela.

        Args:
            title: Novo título da janela.
        """
        if self.window:
            self.window.title(title)

    def enable_upload_button(self) -> None:
        """Habilita o botão Salvar e Enviar."""
        if self.btn_upload:
            self.btn_upload.configure(state="normal")

    def disable_upload_button(self) -> None:
        """Desabilita o botão Salvar e Enviar."""
        if self.btn_upload:
            self.btn_upload.configure(state="disabled")

    def enable_cartao_cnpj_button(self) -> None:
        """Habilita o botão Cartão CNPJ."""
        if self.btn_cartao_cnpj:
            self.btn_cartao_cnpj.configure(state="normal")

    def disable_cartao_cnpj_button(self) -> None:
        """Desabilita o botão Cartão CNPJ."""
        if self.btn_cartao_cnpj:
            self.btn_cartao_cnpj.configure(state="disabled")

    def show(self) -> None:
        """Exibe a janela centralizada."""
        if not self.window:
            return

        self.window.update_idletasks()  # type: ignore[union-attr]
        self.window.deiconify()  # type: ignore[union-attr]
        show_centered(self.window)
        self.window.grab_set()  # type: ignore[union-attr]
        self.window.focus_set()  # type: ignore[union-attr]

        # Foco inicial no primeiro campo
        razao_widget = self.ents.get("Razão Social")
        if razao_widget and hasattr(razao_widget, "focus_set"):
            razao_widget.focus_set()

    def close(self) -> None:
        """Fecha a janela."""
        if self.window:
            try:
                self.window.grab_release()
            except Exception:
                pass
            self.window.destroy()
            self.window = None

    def update_title(self, title: str) -> None:
        """Atualiza título da janela (alias para set_title).

        Args:
            title: Novo título da janela.
        """
        self.set_title(title)

    def set_upload_button_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita botão de upload.

        Args:
            enabled: True para habilitar, False para desabilitar.
        """
        if enabled:
            self.enable_upload_button()
        else:
            self.disable_upload_button()

    def set_cartao_cnpj_button_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita botão Cartão CNPJ.

        Args:
            enabled: True para habilitar, False para desabilitar.
        """
        if enabled:
            self.enable_cartao_cnpj_button()
        else:
            self.disable_cartao_cnpj_button()

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
                # CTkTextbox
                if isinstance(widget, ctk.CTkTextbox):  # type: ignore[misc]
                    widget.delete("1.0", "end")
                    widget.insert("1.0", value or "")
                # CTkEntry ou tk.Text (fallback)
                elif isinstance(widget, tk.Text):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", value or "")
                # CTkEntry, CTkOptionMenu
                elif hasattr(widget, "delete") and hasattr(widget, "insert"):
                    widget.delete(0, "end")  # type: ignore[attr-defined]
                    widget.insert(0, value or "")  # type: ignore[attr-defined]
                # CTkOptionMenu set via StringVar
                elif isinstance(widget, ctk.CTkOptionMenu) and self.status_var:  # type: ignore[misc]
                    if field_name == "Status do Cliente":
                        self.status_var.set(value or STATUS_CHOICES[0])
                        widget.set(value or STATUS_CHOICES[0])
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
            # CTkTextbox
            if isinstance(widget, ctk.CTkTextbox):  # type: ignore[misc]
                return widget.get("1.0", "end").strip()
            # tk.Text (fallback)
            elif isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            # CTkEntry
            elif hasattr(widget, "get"):
                value = widget.get()  # type: ignore[attr-defined]
                if isinstance(value, str):
                    return value.strip()
                return str(value).strip()
            return ""
        except Exception:
            return ""
