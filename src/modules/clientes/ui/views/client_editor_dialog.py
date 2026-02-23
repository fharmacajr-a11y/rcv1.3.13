# -*- coding: utf-8 -*-
"""Diálogo de edição/criação de cliente para ClientesV2.

FASE 4 FINAL: Dialog 100% CustomTkinter (CTkToplevel).
MIGRAÇÃO COMPLETA: Equivalente ao formulário legado com todos os campos e botões.
"""

from __future__ import annotations

import logging
import re
import tkinter as tk
from collections.abc import Mapping
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, BORDER, APP_BG, PRIMARY_BLUE, PRIMARY_BLUE_HOVER
from src.modules.clientes.core.constants import STATUS_CHOICES
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash, apply_window_icon
from src.utils.formatters import format_cnpj
from src.utils.phone_utils import format_phone_br

log = logging.getLogger(__name__)


# ============================================================================
# Helpers locais para lidar com dict OU objeto Cliente
# ============================================================================


def _safe_get(obj: Any, key: str, default: Any = "") -> Any:
    """Extrai valor de dict OU objeto (aceita ambos).

    Usado para trabalhar com objetos Cliente que podem vir como dict
    (do Supabase) ou como dataclass/model (do ORM).

    Args:
        obj: Dict ou objeto (dataclass, Cliente, etc.)
        key: Chave/atributo a buscar
        default: Valor padrão se não encontrar

    Returns:
        Valor extraído ou default
    """
    if obj is None:
        return default

    # Tentar como dict primeiro (mais comum)
    if isinstance(obj, Mapping):
        return obj.get(key, default)

    # Tentar como objeto (getattr)
    return getattr(obj, key, default)


def _conflict_desc(conflict: Any) -> str:
    """Gera descrição amigável de um conflito de cliente.

    Args:
        conflict: Cliente conflitante (dict ou objeto)

    Returns:
        String formatada: "ID 123 - Nome da Empresa (12.345.678/0001-90)"
    """
    if conflict is None:
        return "cliente desconhecido"

    cid = _safe_get(conflict, "id", "?")
    razao = _safe_get(conflict, "razao_social", "cliente desconhecido")
    cnpj = _safe_get(conflict, "cnpj", "")

    desc = f"ID {cid} - {razao}"
    if cnpj:
        desc += f" ({cnpj})"

    return desc


class ClientEditorDialog(ctk.CTkToplevel):
    """Diálogo para criar ou editar cliente.

    Usa apenas CustomTkinter (CTkToplevel, CTkLabel, CTkEntry, CTkButton).
    MIGRAÇÃO COMPLETA: Equivalente ao formulário legado com layout duas colunas,
    todos os campos (incluindo internos) e todos os botões.
    """

    def __init__(
        self,
        parent: Any,
        client_id: Optional[int] = None,
        on_save: Optional[Callable[[dict], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ):
        """Inicializa o diálogo.

        Args:
            parent: Widget pai
            client_id: ID do cliente para editar (None = novo)
            on_save: Callback chamado após salvar com sucesso
            on_close: Callback chamado quando diálogo é fechado
            session_id: ID da sessão para logs (opcional)
        """
        self.session_id = session_id or "unknown"
        log.info(f"[ClientEditorDialog:{self.session_id}] Iniciando criação")

        super().__init__(parent, **kwargs)

        self.client_id = client_id
        self.on_save = on_save
        self.on_close = on_close
        self._client_data: Optional[dict] = None

        # ANTI-FLASH: Ocultar imediatamente (withdraw + offscreen multi-monitor safe)
        prepare_hidden_window(self)
        log.debug(f"[ClientEditorDialog:{self.session_id}] Janela preparada (hidden + offscreen)")

        # Configurar cores de fundo (evita flash branco)
        self.configure(fg_color=APP_BG)

        # Configurar janela (invisível)
        self._set_window_title()

        # Usar Toplevel.resizable para evitar flicker
        try:
            from tkinter import Toplevel

            Toplevel.resizable(self, False, False)
        except Exception:
            self.resizable(False, False)

        # Modal: transient ANTES de mostrar
        self.transient(parent)

        # Construir UI completa (ainda invisível)
        self._build_ui()
        log.debug(f"[ClientEditorDialog:{self.session_id}] UI construída")
        
        # Sincronizar altura do spacer direito após renderização (pixel-perfect)
        self.after_idle(self._sync_right_spacer_height)

        # Carregar dados ANTES de exibir (se editando)
        # CRÍTICO: Previne flash de campos vazios
        if client_id is not None:
            self._load_client_data()
            log.debug(f"[ClientEditorDialog:{self.session_id}] Dados carregados")

        # Forçar renderização completa ANTES de mostrar
        self.update_idletasks()

        # Aplicar ícone do app (com reapply em 250ms para CTkToplevel)
        apply_window_icon(self)

        # Mostrar janela centralizada sem flash (offscreen → render → onscreen)
        show_centered_no_flash(self, parent, width=1100, height=700)
        log.debug(f"[ClientEditorDialog:{self.session_id}] Janela visível e centralizada")
        
        # Ativar placeholders APÓS janela visível (Novo Cliente)
        # Delay de 30ms garante que a janela já está completamente renderizada
        if client_id is None:
            self.after(30, self._activate_all_placeholders)

        # Aplicar titlebar escura (Windows) - APÓS deiconify (precisa de handle mapeado)
        try:
            set_win_dark_titlebar(self)
        except Exception as e:
            log.debug(f"[ClientEditorDialog:{self.session_id}] Erro titlebar: {e}")

        # Modal: grab_set após janela visível (com retry se não-viewable)
        self.after(10, lambda: self._setup_modal_safe())

        log.info(f"[ClientEditorDialog:{self.session_id}] PRONTO")

        # Registrar callback de fechamento
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _setup_modal_safe(self, retry_count: int = 0) -> None:
        """Configura comportamento modal APENAS quando janela está viewable.
        
        Args:
            retry_count: Contador de tentativas (máx 10 para evitar loop infinito)
        """
        max_retries = 10
        retry_delay_ms = 50
        
        try:
            # Verificar se a janela ainda existe
            if not self.winfo_exists():
                log.warning(f"[ClientEditorDialog:{self.session_id}] Janela não existe mais, abortando modal setup")
                return
                
            # Verificar se a janela está viewable (mapeada e visível)
            if not self.winfo_viewable():
                if retry_count < max_retries:
                    log.info(
                        f"[ClientEditorDialog:{self.session_id}] "
                        f"Janela não-viewable (tentativa {retry_count + 1}/{max_retries}), "
                        f"reagendando grab_set em {retry_delay_ms}ms"
                    )
                    self.after(retry_delay_ms, lambda: self._setup_modal_safe(retry_count + 1))
                    return
                else:
                    log.warning(
                        f"[ClientEditorDialog:{self.session_id}] "
                        f"Janela não ficou viewable após {max_retries} tentativas, "
                        f"abortando grab_set (modal pode não funcionar)"
                    )
                    return
            
            # Janela está viewable, aplicar grab_set
            self.grab_set()
            log.info(f"[ClientEditorDialog:{self.session_id}] grab_set aplicado com sucesso (viewable=True)")
            
        except Exception as e:
            log.error(
                f"[ClientEditorDialog:{self.session_id}] "
                f"Erro ao aplicar grab_set: {e}"
            )

    def _set_window_title(self) -> None:
        """Define título da janela conforme legado."""
        if self.client_id is None:
            self.title("Novo Cliente")
        else:
            # Título será atualizado após carregar dados
            self.title(f"Editar Cliente - ID: {self.client_id}")

    def _on_window_close(self) -> None:
        """Handler quando usuário fecha a janela (X).

        Notifica parent que diálogo foi fechado e faz cleanup completo.
        """
        log.info(f"[ClientEditorDialog:{self.session_id}] Usuário fechou a janela")
        self._cleanup_and_destroy()

    def _cleanup_and_destroy(self) -> None:
        """Cleanup centralizado: libera grab, notifica parent e destrói janela.
        
        Usado por:
        - _on_window_close (botão X)
        - _on_cancel (botão Cancelar / tecla ESC)
        """
        try:
            # Liberar grab ANTES de destruir (previne grab preso)
            self.grab_release()
            log.debug(f"[ClientEditorDialog:{self.session_id}] grab_release executado")
        except Exception as e:
            log.debug(f"[ClientEditorDialog:{self.session_id}] Erro em grab_release: {e}")
        
        try:
            # Notificar parent que diálogo foi fechado
            if self.on_close:
                self.on_close()
        except Exception as e:
            log.error(f"[ClientEditorDialog:{self.session_id}] Erro no callback on_close: {e}")
        
        try:
            # Destruir janela
            self.destroy()
        except Exception as e:
            log.error(f"[ClientEditorDialog:{self.session_id}] Erro ao destruir janela: {e}")

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        # TAREFA C: Background cinza claro (sem borda branca)
        self.configure(fg_color=APP_BG)

        # TAREFA C: Container principal - sem padding externo (remove borda branca)
        main_frame = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Grid com 3 linhas: conteúdo (0), separador (1), botões (2)
        main_frame.rowconfigure(0, weight=1)  # Conteúdo expande
        main_frame.rowconfigure(1, weight=0)  # Separador fixo
        main_frame.rowconfigure(2, weight=0)  # Botões fixo
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=0)
        main_frame.columnconfigure(2, weight=4, minsize=440)  # Aumentado weight e minsize para dar mais espaço ao painel direito

        # Divisão em duas colunas (como legado)
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        sep = ctk.CTkFrame(main_frame, width=2, fg_color=BORDER)
        sep.grid(row=0, column=1, sticky="ns", pady=10)

        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)

        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # Construir painéis
        self._build_left_panel(left_frame)
        self._build_right_panel(right_frame)

        # AJUSTE 3: Separador horizontal antes dos botões
        separator_line = ctk.CTkFrame(
            main_frame,
            height=1,
            fg_color=BORDER,
        )
        separator_line.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 0))

        # Barra de botões (rodapé) - agora em row=2
        self._build_buttons(main_frame)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        """Constrói painel esquerdo com campos principais."""
        row = 0

        # Razão Social *
        ctk.CTkLabel(parent, text="Razão Social:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(5, 0)
        )
        row += 1
        self.razao_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Nome da empresa",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.razao_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # CNPJ *
        ctk.CTkLabel(parent, text="CNPJ:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.cnpj_entry = ctk.CTkEntry(
            parent,
            placeholder_text="00.000.000/0000-00",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.cnpj_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        # Bind para formatar ao sair do campo
        self.cnpj_entry.bind("<FocusOut>", self._on_cnpj_focus_out)
        row += 1

        # Nome
        ctk.CTkLabel(parent, text="Nome:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.nome_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Nome usado no dia-a-dia",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.nome_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # WhatsApp
        ctk.CTkLabel(parent, text="WhatsApp:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.whatsapp_entry = ctk.CTkEntry(
            parent,
            placeholder_text="(00) 00000-0000",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.whatsapp_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        # Bind para formatar ao sair do campo
        self.whatsapp_entry.bind("<FocusOut>", self._on_whatsapp_focus_out)
        row += 1

        # Observações (grande)
        ctk.CTkLabel(parent, text="Observações:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        obs_row = row
        self.obs_text = ctk.CTkTextbox(
            parent,
            height=150,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",  # Wrap por palavra para melhor legibilidade
        )
        self.obs_text.grid(row=row, column=0, sticky="nsew", padx=6, pady=(0, 10))
        parent.rowconfigure(obs_row, weight=1)
        row += 1

        # OBJETIVO 2: Status do Cliente + botão Senhas (colados)
        status_container = ctk.CTkFrame(parent, fg_color="transparent")
        status_container.grid(row=row, column=0, sticky="w", padx=6, pady=(0, 6))
        status_container.columnconfigure(0, weight=0)  # Sem expansão
        status_container.columnconfigure(1, weight=0)  # Sem expansão
        
        # Salvar referência para usar no painel direito (igualar alturas)
        self._status_container = status_container
        
        # Bind para sincronizar altura do spacer direito em tempo real
        status_container.bind("<Configure>", lambda e: self._sync_right_spacer_height())

        ctk.CTkLabel(status_container, text="Status do Cliente:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 2)
        )

        self.status_var = tk.StringVar(value="Novo Cliente")
        self.status_combo = ctk.CTkOptionMenu(
            status_container,
            variable=self.status_var,
            values=STATUS_CHOICES,
            fg_color=SURFACE,
            button_color=PRIMARY_BLUE,
            button_hover_color=PRIMARY_BLUE_HOVER,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=SURFACE_DARK,
            dropdown_text_color=TEXT_PRIMARY,
            width=160,
            height=28,
        )
        self.status_combo.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=0)

        # Botão Senhas colado ao Status
        self.senhas_btn = make_btn(
            status_container,
            text="Senhas",
            command=self._on_senhas,
            fg_color="gray",
            hover_color="darkgray",
            width=70,
            height=28,
        )
        self.senhas_btn.grid(row=1, column=1, sticky="w", padx=(0, 0), pady=0)

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        """Constrói painel direito com campos internos."""
        row = 0

        # Endereço (interno)
        ctk.CTkLabel(parent, text="Endereço (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(5, 0)
        )
        row += 1
        self.endereco_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Endereço da empresa",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.endereco_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Bairro (interno)
        ctk.CTkLabel(parent, text="Bairro (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.bairro_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Bairro",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.bairro_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Cidade (interno)
        ctk.CTkLabel(parent, text="Cidade (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.cidade_entry = ctk.CTkEntry(
            parent,
            placeholder_text="Cidade",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.cidade_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # CEP (interno)
        ctk.CTkLabel(parent, text="CEP (interno):", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        self.cep_entry = ctk.CTkEntry(
            parent,
            placeholder_text="00000-000",
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
        )
        self.cep_entry.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 5))
        row += 1

        # Contatos adicionais (textbox grande, mesmo padrão visual dos outros campos)
        ctk.CTkLabel(
            parent,
            text="Contatos adicionais:",
            anchor="w",
            text_color=TEXT_PRIMARY,
        ).grid(row=row, column=0, sticky="w", padx=6, pady=(0, 0))
        row += 1

        # Textbox para contatos adicionais (mesmas cores de Observações)
        contatos_row = row
        self.contatos_text = ctk.CTkTextbox(
            parent,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            wrap="word",
        )
        self.contatos_text.grid(row=row, column=0, sticky="nsew", padx=6, pady=(0, 10))
        parent.rowconfigure(contatos_row, weight=1)  # Expande para ocupar espaço disponível
        row += 1

        # Spacer para igualar altura com Observações (compensar o bloco Status do painel esquerdo)
        # A altura será sincronizada dinamicamente pelo método _sync_right_spacer_height()
        spacer_height = 70  # Fallback inicial (será atualizado após renderização)
        self._right_spacer = ctk.CTkFrame(parent, fg_color="transparent", height=spacer_height)
        self._right_spacer.grid(row=row, column=0, sticky="ew", padx=6, pady=0)
        self._right_spacer.grid_propagate(False)  # Manter altura configurada
        row += 1

    def _sync_right_spacer_height(self) -> None:
        """Sincroniza altura do spacer direito com o bloco Status esquerdo (pixel-perfect).
        
        Este método garante que o textbox "Contatos adicionais" termine exatamente
        na mesma linha que o textbox "Observações", compensando a altura do bloco
        "Status do Cliente" no painel esquerdo.
        """
        try:
            # Forçar atualização de geometria
            self.update_idletasks()
            
            # Obter altura real do status_container
            h = self._status_container.winfo_height()
            if h <= 1:
                # Widget ainda não renderizado, usar altura requisitada
                h = self._status_container.winfo_reqheight()
            
            # Obter padding vertical do grid do status_container
            gi = self._status_container.grid_info()
            pady = gi.get("pady", 0)
            
            # Calcular padding extra
            extra = 0
            if isinstance(pady, (tuple, list)):
                extra = sum(int(p) for p in pady)
            else:
                extra = int(pady) if pady else 0
            
            # Altura alvo para o spacer (altura do container + padding)
            target = h + extra
            
            # Aplicar no spacer (mínimo 50px para evitar valores negativos/zero)
            if target > 0:
                self._right_spacer.configure(height=max(target, 50))
                
        except Exception as e:
            # Silenciar erros durante destruição de widgets
            log.debug(f"[ClientEditor] Erro ao sincronizar spacer: {e}")

    def _set_entry_value(self, entry: ctk.CTkEntry, value: str) -> None:
        """Define valor em CTkEntry preservando placeholder quando vazio.
        
        Args:
            entry: CTkEntry a ser preenchido
            value: Valor a ser inserido (ou vazio para ativar placeholder)
        """
        entry.delete(0, "end")
        value = (value or "").strip()
        if value:
            entry.insert(0, value)
            return
        
        # Campo vazio: forçar ativação do placeholder (método interno do CustomTkinter)
        # NÃO mexer em foco aqui para evitar flash durante construção da UI
        if hasattr(entry, "_activate_placeholder"):
            try:
                entry._activate_placeholder()
            except Exception:
                pass
    
    def _activate_all_placeholders(self) -> None:
        """Ativa placeholders em todos os CTkEntry vazios (usado no Novo Cliente)."""
        entries = [
            self.razao_entry,
            self.cnpj_entry,
            self.nome_entry,
            self.whatsapp_entry,
            self.endereco_entry,
            self.bairro_entry,
            self.cidade_entry,
            self.cep_entry,
        ]
        for entry in entries:
            self._set_entry_value(entry, "")

    def _build_buttons(self, parent: ctk.CTkFrame) -> None:
        """Constrói barra de botões no rodapé."""
        # OBJETIVO 3: Botões dentro do container esquerdo (não atravessa divisor)
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, sticky="w", padx=10, pady=(8, 10))

        # Botão Salvar (verde)
        self.save_btn = make_btn(
            buttons_frame,
            text="Salvar",
            command=self._on_save_clicked,
            fg_color="#28a745",
            hover_color="#218838",
        )
        self.save_btn.pack(side="left", padx=(0, 5))

        # Botão Cartão CNPJ (azul)
        self.cartao_btn = make_btn(
            buttons_frame,
            text="Cartão CNPJ",
            command=self._on_cartao_cnpj,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
        )
        self.cartao_btn.pack(side="left", padx=5)

        # Botão Enviar documentos (azul)
        self.upload_btn = make_btn(
            buttons_frame,
            text="Enviar documentos",
            command=self._on_enviar_documentos,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
        )
        self.upload_btn.pack(side="left", padx=5)

        # Botão Cancelar (vermelho)
        self.cancel_btn = make_btn(
            buttons_frame,
            text="Cancelar",
            command=self._on_cancel,
            fg_color="#dc3545",
            hover_color="#c82333",
        )
        self.cancel_btn.pack(side="left", padx=5)

        # BIND CENTRALIZADO: Enter chama handler unificado (gerencia Shift+Enter em Observações e Contatos)
        self.bind("<Return>", self._on_return_key)
        self.bind("<KP_Enter>", self._on_return_key)  # Numpad Enter
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _on_return_key(self, event: Any) -> str:
        """Handler centralizado para tecla Enter.

        Comportamento:
        - Se SHIFT pressionado E foco em Observações ou Contatos: insere nova linha
        - Caso contrário: salva o cliente

        Args:
            event: Evento de teclado

        Returns:
            "break" para impedir propagação
        """
        # Detectar se SHIFT está pressionado
        shift_pressed = bool(event.state & 0x0001)

        # Detectar se o foco está em textbox multiline (Observações ou Contatos)
        focus_widget = self.focus_get()
        is_focus_on_textbox = False

        if focus_widget is not None:
            # Verificar Observações
            obs_internal = getattr(self.obs_text, "_textbox", None)
            if focus_widget is self.obs_text or focus_widget is obs_internal:
                is_focus_on_textbox = True

            # Verificar Contatos
            contatos_internal = getattr(self.contatos_text, "_textbox", None)
            if focus_widget is self.contatos_text or focus_widget is contatos_internal:
                is_focus_on_textbox = True

        # Se Shift+Enter E foco em textbox: inserir nova linha
        if shift_pressed and is_focus_on_textbox:
            try:
                focus_widget.insert("insert", "\n")
            except Exception as e:
                log.debug(f"[ClientEditor] Erro ao inserir newline: {e}")
            return "break"

        # Caso contrário: salvar
        self._on_save_clicked()
        return "break"

    def _parse_contatos_from_textbox(self) -> list[dict]:
        """Parse contatos do textbox.

        Formato esperado por linha: "Nome - WhatsApp" ou "Nome | WhatsApp" ou "Nome ; WhatsApp"
        Se não houver separador, linha inteira é nome.

        Returns:
            Lista de dicts: [{"nome": str, "whatsapp": str}, ...]
        """
        texto = self.contatos_text.get("1.0", "end").strip()
        if not texto:
            return []

        contatos = []
        for linha in texto.split("\n"):
            linha = linha.strip()
            if not linha:
                continue

            # Tentar separadores (prioridade: " - ", "|", ";")
            nome = ""
            whatsapp = ""

            if " - " in linha:
                partes = linha.split(" - ", 1)
                nome = partes[0].strip()
                whatsapp = partes[1].strip() if len(partes) > 1 else ""
            elif "|" in linha:
                partes = linha.split("|", 1)
                nome = partes[0].strip()
                whatsapp = partes[1].strip() if len(partes) > 1 else ""
            elif ";" in linha:
                partes = linha.split(";", 1)
                nome = partes[0].strip()
                whatsapp = partes[1].strip() if len(partes) > 1 else ""
            else:
                # Sem separador: linha inteira é nome
                nome = linha

            if nome:  # Só adicionar se tiver nome
                contatos.append({"nome": nome, "whatsapp": whatsapp})

        return contatos

    def _load_contatos_from_db(self, cliente_id: int) -> None:
        """Carrega contatos do Supabase e preenche textbox.

        Args:
            cliente_id: ID do cliente (BIGINT)
        """
        try:
            from src.infra.supabase_client import get_supabase

            supabase = get_supabase()
            response = supabase.table("cliente_contatos").select("nome,whatsapp").eq("cliente_id", int(cliente_id)).execute()

            if response.data:
                linhas = []
                for contato in (response.data or []):
                    # Robustez: verificar se é dict
                    if not isinstance(contato, dict):
                        continue
                    
                    # Tratar NULL do banco (vira None em Python)
                    nome = (contato.get("nome") or "").strip()
                    whatsapp = (contato.get("whatsapp") or "").strip()
                    
                    # Ignorar registros sem nome
                    if not nome:
                        continue
                    
                    # Montar linha
                    if whatsapp:
                        linhas.append(f"{nome} - {whatsapp}")
                    else:
                        linhas.append(nome)

                # Preencher textbox
                if linhas:
                    texto_contatos = "\n".join(linhas)
                    self.contatos_text.delete("1.0", "end")
                    self.contatos_text.insert("1.0", texto_contatos)

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao carregar contatos do Supabase: {e}", exc_info=True)

    def _save_contatos_to_db(self, cliente_id: int) -> None:
        """Salva contatos no Supabase (delete + insert).

        Args:
            cliente_id: ID do cliente (BIGINT)
        """
        try:
            from src.infra.supabase_client import get_supabase

            supabase = get_supabase()
            cliente_id_int = int(cliente_id)

            # 1. Delete antigos
            supabase.table("cliente_contatos").delete().eq("cliente_id", cliente_id_int).execute()

            # 2. Parse contatos do textbox
            contatos = self._parse_contatos_from_textbox()

            # 3. Insert em lote
            if contatos:
                records = [
                    {
                        "cliente_id": cliente_id_int,
                        "nome": c["nome"],
                        "whatsapp": c["whatsapp"] or None,
                    }
                    for c in contatos
                ]
                supabase.table("cliente_contatos").insert(records).execute()

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao salvar contatos no Supabase: {e}", exc_info=True)

    def _load_client_data(self) -> None:
        """Carrega dados do cliente para edição."""
        if self.client_id is None:
            return

        try:
            # Buscar cliente via service
            from src.modules.clientes.core import service as clientes_service

            cliente = clientes_service.fetch_cliente_by_id(self.client_id)

            if not cliente:
                log.error(f"[ClientEditor] Cliente {self.client_id} não encontrado")
                return

            self._client_data = cliente

            # Atualizar título com dados do cliente (igual ao legado)
            razao = _safe_get(cliente, "razao_social", "")
            cnpj_raw = _safe_get(cliente, "cnpj", "")
            cnpj_fmt = format_cnpj(cnpj_raw) or cnpj_raw  # Formatar CNPJ com pontos/barra

            # Extrair sufixo WhatsApp das observações (se existir)
            obs = _safe_get(cliente, "observacoes", "") or ""
            sufixo = ""
            if "(Não está respondendo)" in obs:
                sufixo = " (Não está respondendo)"
            elif "(Respondendo)" in obs:
                sufixo = " (Respondendo)"

            self.title(f"Editar Cliente - ID: {self.client_id} - {razao} - {cnpj_fmt}{sufixo}")

            # Preencher campos principais (usar helper para preservar placeholders)
            self._set_entry_value(self.razao_entry, _safe_get(cliente, "razao_social", ""))

            # CNPJ FORMATADO (padrão 00.000.000/0000-00)
            cnpj_raw = _safe_get(cliente, "cnpj", "")
            cnpj_fmt = format_cnpj(cnpj_raw) if cnpj_raw else ""
            self._set_entry_value(self.cnpj_entry, cnpj_fmt or cnpj_raw)

            # Nome
            self._set_entry_value(self.nome_entry, _safe_get(cliente, "nome", ""))

            # WhatsApp FORMATADO (padrão +55 DD XXXXX-XXXX)
            whatsapp_raw = _safe_get(cliente, "numero", "") or _safe_get(cliente, "whatsapp", "")
            whatsapp_fmt = format_phone_br(whatsapp_raw) if whatsapp_raw else ""
            self._set_entry_value(self.whatsapp_entry, whatsapp_fmt or whatsapp_raw)

            # Preencher campos internos (endereço) - usar helper para preservar placeholders - usar helper para preservar placeholders
            # Nota: Esses campos podem não estar no banco ainda, usar valores vazios como padrão
            self._set_entry_value(self.endereco_entry, _safe_get(cliente, "endereco", ""))
            self._set_entry_value(self.bairro_entry, _safe_get(cliente, "bairro", ""))
            self._set_entry_value(self.cidade_entry, _safe_get(cliente, "cidade", ""))
            self._set_entry_value(self.cep_entry, _safe_get(cliente, "cep", ""))

            # Extrair status das observações (padrão legacy: "[Status] texto")
            obs = _safe_get(cliente, "observacoes", "") or _safe_get(cliente, "obs", "")
            status = "Novo Cliente"  # Default

            if obs:
                # Usar método do viewmodel para extrair status
                from src.modules.clientes.core.viewmodel import ClientesViewModel

                vm_temp = ClientesViewModel()
                status_extracted, obs_clean = vm_temp.extract_status_and_observacoes(obs)
                if status_extracted:
                    status = status_extracted
                    obs = obs_clean

            # Aplicar status
            self.status_var.set(status)

            # Aplicar observações
            if obs:
                self.obs_text.delete("1.0", "end")
                self.obs_text.insert("1.0", obs)

            # Carregar contatos adicionais do Supabase
            self._load_contatos_from_db(self.client_id)

            log.debug(f"[ClientEditor] Dados carregados para cliente {self.client_id}")

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao carregar cliente: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Erro ao carregar dados do cliente: {e}", parent=self)

    def _on_cnpj_focus_out(self, event: Any = None) -> None:
        """Formata CNPJ ao sair do campo."""
        try:
            raw = self.cnpj_entry.get().strip()
            if raw:
                formatted = format_cnpj(raw)
                if formatted and formatted != raw:
                    self._set_entry_value(self.cnpj_entry, formatted)
            else:
                # Campo vazio: garantir placeholder visível
                self._set_entry_value(self.cnpj_entry, "")
        except Exception as e:
            log.debug(f"[ClientEditor] Erro ao formatar CNPJ: {e}")

    def _on_whatsapp_focus_out(self, event: Any = None) -> None:
        """Formata WhatsApp ao sair do campo."""
        try:
            raw = self.whatsapp_entry.get().strip()
            if raw:
                formatted = format_phone_br(raw)
                if formatted and formatted != raw:
                    self._set_entry_value(self.whatsapp_entry, formatted)
            else:
                # Campo vazio: garantir placeholder visível
                self._set_entry_value(self.whatsapp_entry, "")
        except Exception as e:
            log.debug(f"[ClientEditor] Erro ao formatar WhatsApp: {e}")

    def _validate_fields(self) -> bool:
        """Valida campos obrigatórios."""
        razao = self.razao_entry.get().strip()
        cnpj = self.cnpj_entry.get().strip()

        if not razao:
            from tkinter import messagebox

            messagebox.showwarning("Atenção", "Razão Social é obrigatória.", parent=self)
            self.razao_entry.focus()
            return False

        if not cnpj:
            from tkinter import messagebox

            messagebox.showwarning("Atenção", "CNPJ é obrigatório.", parent=self)
            self.cnpj_entry.focus()
            return False

        # Validação básica de CNPJ (só formato)
        cnpj_digits = re.sub(r"\D", "", cnpj)
        if len(cnpj_digits) != 14:
            from tkinter import messagebox

            messagebox.showwarning("Atenção", "CNPJ deve ter 14 dígitos.", parent=self)
            self.cnpj_entry.focus()
            return False

        return True

    def _on_save_clicked(self) -> None:
        """Handler do botão Salvar - com validações de duplicatas."""
        if not self._validate_fields():
            return

        try:
            # Coletar dados do form
            status_text = self.status_var.get()
            obs_body = self.obs_text.get("1.0", "end").strip()

            # Aplicar status nas observações (padrão legacy: "[Status] texto")
            from src.modules.clientes.core.viewmodel import ClientesViewModel

            vm_temp = ClientesViewModel()
            obs_completa = vm_temp.apply_status_to_observacoes(status_text, obs_body)

            valores = {
                "Razão Social": self.razao_entry.get().strip(),
                "CNPJ": self.cnpj_entry.get().strip(),
                "Nome": self.nome_entry.get().strip(),
                "WhatsApp": self.whatsapp_entry.get().strip(),
                "Observações": obs_completa,
                # Campos internos (não persistidos no legado, mas incluídos para futuro)
                "Endereço": self.endereco_entry.get().strip(),
                "Bairro": self.bairro_entry.get().strip(),
                "Cidade": self.cidade_entry.get().strip(),
                "CEP": self.cep_entry.get().strip(),
                # Contatos adicionais (textbox do painel direito)
                "Contatos adicionais": self.contatos_text.get("1.0", "end").strip(),
            }

            # FASE 3.2: Validar duplicatas antes de salvar
            from src.modules.clientes.core import service as clientes_service
            from src.modules.clientes.core.service import ClienteCNPJDuplicadoError
            from tkinter import messagebox

            # Montar row (None para novo, tupla (id,) para editar)
            row = None if self.client_id is None else (self.client_id,)

            # Checar duplicatas
            duplicatas = clientes_service.checar_duplicatas_para_form(valores, row)

            # 1. CNPJ duplicado é bloqueante (hard block)
            cnpj_conflict = duplicatas.get("cnpj_conflict")
            if cnpj_conflict:
                messagebox.showerror(
                    "CNPJ Duplicado",
                    f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(cnpj_conflict)}\n\n"
                    f"Edite o cliente existente ou use um CNPJ diferente.",
                    parent=self,
                )
                return

            # 2. Razão Social e/ou Telefone similares são warnings (soft block)
            razao_conflicts = duplicatas.get("razao_conflicts", [])
            numero_conflicts = duplicatas.get("numero_conflicts", [])

            if razao_conflicts or numero_conflicts:
                # Montar mensagem com conflitos
                msg_parts = ["Encontrado(s) cliente(s) similar(es):\n"]

                if razao_conflicts:
                    msg_parts.append("\n• Razão Social similar:")
                    for conf in razao_conflicts[:3]:  # Limitar a 3
                        conf_id = _safe_get(conf, "id", "?")
                        conf_razao = _safe_get(conf, "razao_social", "")
                        msg_parts.append(f"  - ID {conf_id}: {conf_razao}")

                if numero_conflicts:
                    msg_parts.append("\n• Telefone similar:")
                    for conf in numero_conflicts[:3]:  # Limitar a 3
                        conf_id = _safe_get(conf, "id", "?")
                        conf_razao = _safe_get(conf, "razao_social", "")
                        conf_numero = _safe_get(conf, "numero", "")
                        msg_parts.append(f"  - ID {conf_id}: {conf_razao} ({conf_numero})")

                msg_parts.append("\n\nDeseja prosseguir mesmo assim?")

                resposta = messagebox.askyesno("Clientes Similares", "\n".join(msg_parts), parent=self)

                if not resposta:
                    # Usuário cancelou
                    return

            # 3. Se passou as validações, salvar
            log.debug(f"[ClientEditor] Salvando cliente: {valores['Razão Social']}")

            try:
                result = clientes_service.salvar_cliente_a_partir_do_form(row, valores)
                log.info(f"[ClientEditor] Cliente salvo: {result}")

                # Obter ID do cliente (result é tupla: (int, str) -> (id, pasta))
                cliente_id_salvo = None
                if self.client_id:
                    cliente_id_salvo = int(self.client_id)
                elif isinstance(result, tuple) and len(result) >= 1:
                    cliente_id_salvo = int(result[0])  # Primeiro elemento da tupla é o ID

                # Salvar contatos no Supabase
                if cliente_id_salvo:
                    self._save_contatos_to_db(cliente_id_salvo)

            except ClienteCNPJDuplicadoError as dup_err:
                # CNPJ duplicado detectado no service (fallback)
                messagebox.showerror(
                    "CNPJ Duplicado",
                    f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(dup_err.cliente)}\n\n"
                    f"Edite o cliente existente ou use um CNPJ diferente.",
                    parent=self,
                )
                return

            # Chamar callback
            if self.on_save:
                self.on_save(valores)

            # Fechar dialog
            self.destroy()

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao salvar: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Erro ao salvar cliente: {e}", parent=self)

    def _on_cancel(self) -> None:
        """Handler do botão Cancelar e tecla ESC.
        
        Usa o mesmo cleanup centralizado que WM_DELETE_WINDOW.
        """
        log.info(f"[ClientEditorDialog:{self.session_id}] Cancelamento solicitado")
        self._cleanup_and_destroy()

    def _on_senhas(self) -> None:
        """Handler do botão Senhas (Módulo removido)."""
        from tkinter import messagebox

        messagebox.showinfo("Módulo Removido", "O módulo de senhas foi removido do sistema.", parent=self)

    def _on_cartao_cnpj(self) -> None:
        """Handler do botão Cartão CNPJ."""
        try:
            from tkinter.filedialog import askdirectory
            from src.modules.clientes.core import service as clientes_service

            # Solicitar pasta
            base_dir = askdirectory(title="Escolha a pasta do cliente (com o Cartão CNPJ)", parent=self)

            if not base_dir:
                return

            # Extrair dados do Cartão CNPJ
            dados = clientes_service.extrair_dados_cartao_cnpj_em_pasta(base_dir)

            cnpj_extraido = dados.get("cnpj")
            razao_extraida = dados.get("razao_social")

            if not cnpj_extraido and not razao_extraida:
                from tkinter import messagebox

                messagebox.showwarning("Atenção", "Nenhum Cartão CNPJ válido encontrado.", parent=self)
                return

            # Preencher campos
            if cnpj_extraido:
                self.cnpj_entry.delete(0, "end")
                self.cnpj_entry.insert(0, cnpj_extraido)

            if razao_extraida:
                self.razao_entry.delete(0, "end")
                self.razao_entry.insert(0, razao_extraida)

            from tkinter import messagebox

            messagebox.showinfo("Sucesso", "Dados do Cartão CNPJ carregados com sucesso.", parent=self)

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao processar Cartão CNPJ: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Erro ao processar Cartão CNPJ: {e}", parent=self)

    def _on_enviar_documentos(self) -> None:
        """Handler do botão Enviar documentos.

        Implementa o fluxo COMPLETO igual ao legado:
        1. Verifica se cliente está salvo
        2. Seleciona PASTA (não arquivos)
        3. Solicita subpasta em GERAL
        4. Seleciona arquivos da pasta
        5. Executa upload com progresso
        """
        try:
            # Verificar se cliente já foi salvo
            if not self.client_id:
                from tkinter import messagebox

                result = messagebox.askyesno(
                    "Cliente não salvo",
                    "O cliente precisa ser salvo antes de enviar documentos.\n\nDeseja salvar agora?",
                    parent=self,
                )

                if not result:
                    return

                # Salvar primeiro
                if not self._validate_fields():
                    return

                # Coletar e salvar (sem fechar dialog)
                status_text = self.status_var.get()
                obs_body = self.obs_text.get("1.0", "end").strip()

                from src.modules.clientes.core.viewmodel import ClientesViewModel

                vm_temp = ClientesViewModel()
                obs_completa = vm_temp.apply_status_to_observacoes(status_text, obs_body)

                valores = {
                    "Razão Social": self.razao_entry.get().strip(),
                    "CNPJ": self.cnpj_entry.get().strip(),
                    "Nome": self.nome_entry.get().strip(),
                    "WhatsApp": self.whatsapp_entry.get().strip(),
                    "Observações": obs_completa,
                }

                from src.modules.clientes.core import service as clientes_service
                from src.modules.clientes.core.service import ClienteCNPJDuplicadoError
                from tkinter import messagebox

                try:
                    result_save = clientes_service.salvar_cliente_a_partir_do_form(None, valores)

                    # Extrair ID do resultado
                    if result_save and len(result_save) > 0:
                        self.client_id = (
                            result_save[0] if isinstance(result_save[0], int) else int(result_save[0].get("id", 0))
                        )
                        self._set_window_title()

                except ClienteCNPJDuplicadoError as dup_err:
                    # CNPJ duplicado detectado - mostrar mensagem amigável e PARAR
                    messagebox.showerror(
                        "CNPJ Duplicado",
                        f"O CNPJ informado já está cadastrado para:\n\n{_conflict_desc(dup_err.cliente)}\n\n"
                        f"Edite o cliente existente ou use um CNPJ diferente.\n\n"
                        f"Upload cancelado.",
                        parent=self,
                    )
                    return  # CRÍTICO: não prosseguir para upload

            # Executar upload usando o FLUXO COMPLETO do legado (pasta → subpasta → arquivos)
            log.info(f"[ClientEditor] Iniciando upload de documentos para cliente {self.client_id}")

            # Criar widgets mock para compatibilidade com o legado
            class EntryMock:
                def __init__(self, value: str):
                    self._value = value

                def get(self) -> str:
                    return self._value

            ents_mock = {
                "Razão Social": EntryMock(self.razao_entry.get()),
                "CNPJ": EntryMock(self.cnpj_entry.get()),
                "Nome": EntryMock(self.nome_entry.get()),
                "WhatsApp": EntryMock(self.whatsapp_entry.get()),
            }

            # Usar a função COMPLETA do legado (pasta → subpasta → arquivos → upload)
            from src.modules.clientes.forms.client_form_upload_helpers import execute_upload_flow

            # execute_upload_flow já faz:
            # 1. Solicita pasta
            # 2. Coleta PDFs da pasta
            # 3. Solicita subpasta em GERAL
            # 4. Valida arquivos
            # 5. Executa upload com progresso
            # 6. Exibe resultado
            execute_upload_flow(
                parent_widget=self,
                ents=ents_mock,
                client_id=self.client_id,
                host=self,  # Precisa ter self.supabase para resolver org_id
            )

            # Se sucesso, atualizar callback
            if self.on_save:
                valores_atualizados = {
                    "Razão Social": self.razao_entry.get().strip(),
                    "CNPJ": self.cnpj_entry.get().strip(),
                }
                self.on_save(valores_atualizados)

        except Exception as e:
            log.error(f"[ClientEditor] Erro no fluxo de upload: {e}", exc_info=True)
            # Não usar messagebox com parent=self pois o dialog pode já estar destruído
            try:
                if self.winfo_exists():
                    from src.modules.clientes.forms.client_form_upload_helpers import _show_msg

                    _show_msg(self, "Erro", f"Erro ao enviar documentos:\n{e}")
            except Exception:  # noqa: BLE001
                pass
