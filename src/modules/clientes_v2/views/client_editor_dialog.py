# -*- coding: utf-8 -*-
"""Diálogo de edição/criação de cliente para ClientesV2.

FASE 4 FINAL: Dialog 100% CustomTkinter (CTkToplevel).
MIGRAÇÃO COMPLETA: Equivalente ao formulário legado com todos os campos e botões.
"""

from __future__ import annotations

import logging
import re
import tkinter as tk
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, BORDER, APP_BG
from src.modules.clientes.components.helpers import STATUS_CHOICES

log = logging.getLogger(__name__)


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
        log.info(f"[ClientEditorDialog:{self.session_id}] Iniciando criação do diálogo")

        super().__init__(parent, **kwargs)

        self.client_id = client_id
        self.on_save = on_save
        self.on_close = on_close
        self._client_data: Optional[dict] = None

        # CRITICAL: Ocultar janela IMEDIATAMENTE para evitar flash
        self.withdraw()
        log.debug(f"[ClientEditorDialog:{self.session_id}] Janela ocultada (withdraw)")

        # Configurar janela (invisível)
        self._set_window_title()
        self.geometry("940x600")
        self.resizable(False, False)

        # Centralizar (ainda invisível)
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (940 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        # Tornar modal (transient antes de mostrar)
        self.transient(parent)

        # Construir UI completa (ainda invisível)
        self._build_ui()
        log.debug(f"[ClientEditorDialog:{self.session_id}] UI construída")

        # Se editando, carregar dados (ainda invisível)
        if client_id is not None:
            self.after(100, self._load_client_data)

        # CRITICAL: Forçar renderização completa ANTES de mostrar
        self.update_idletasks()
        log.debug(f"[ClientEditorDialog:{self.session_id}] update_idletasks concluído")

        # Mostrar janela (já completamente renderizada)
        self.deiconify()
        log.info(f"[ClientEditorDialog:{self.session_id}] Janela exibida (deiconify)")

        # Modal DEPOIS de mostrar (evita flicker no Windows)
        self.after(10, self.grab_set)
        log.debug(f"[ClientEditorDialog:{self.session_id}] grab_set agendado")

        # TAREFA A: Registrar callback de fechamento
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _set_window_title(self) -> None:
        """Define título da janela conforme legado."""
        if self.client_id is None:
            self.title("Novo Cliente")
        else:
            # Título será atualizado após carregar dados
            self.title(f"Editar Cliente - {self.client_id}")

    def _on_window_close(self) -> None:
        """Handler quando usuário fecha a janela (X).

        Notifica parent que diálogo foi fechado.
        """
        log.info(f"[ClientEditorDialog:{self.session_id}] Usuário fechou a janela")
        if self.on_close:
            self.on_close()
        self.destroy()

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        # TAREFA C: Background cinza claro (sem borda branca)
        self.configure(fg_color=APP_BG)

        # TAREFA C: Container principal - sem padding externo (remove borda branca)
        main_frame = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=0)
        main_frame.columnconfigure(2, weight=2)

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

        # Barra de botões (rodapé)
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
        row += 1

        # Observações (grande)
        ctk.CTkLabel(parent, text="Observações:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=row, column=0, sticky="w", padx=6, pady=(0, 0)
        )
        row += 1
        obs_row = row
        self.obs_text = ctk.CTkTextbox(
            parent, height=150, fg_color=SURFACE, border_color=BORDER, text_color=TEXT_PRIMARY
        )
        self.obs_text.grid(row=row, column=0, sticky="nsew", padx=6, pady=(0, 10))
        parent.rowconfigure(obs_row, weight=1)
        row += 1

        # Status do Cliente + botão Senhas
        status_container = ctk.CTkFrame(parent, fg_color="transparent")
        status_container.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 6))
        status_container.columnconfigure(0, weight=1)
        status_container.columnconfigure(1, weight=0)

        ctk.CTkLabel(status_container, text="Status do Cliente:", anchor="w", text_color=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 2)
        )

        self.status_var = tk.StringVar(value="Novo Cliente")
        self.status_combo = ctk.CTkOptionMenu(
            status_container,
            variable=self.status_var,
            values=STATUS_CHOICES,
            fg_color=SURFACE,
            button_color=BORDER,
            button_hover_color=BORDER,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=SURFACE_DARK,
            dropdown_text_color=TEXT_PRIMARY,
        )
        self.status_combo.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=0)

        self.senhas_btn = ctk.CTkButton(
            status_container, text="Senhas", command=self._on_senhas, width=80, fg_color="gray", hover_color="darkgray"
        )
        self.senhas_btn.grid(row=1, column=1, sticky="w", pady=0)

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

        # Espaço para expansão
        parent.rowconfigure(row, weight=1)

    def _build_buttons(self, parent: ctk.CTkFrame) -> None:
        """Constrói barra de botões no rodapé."""
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

        # Botão Salvar (verde)
        self.save_btn = ctk.CTkButton(
            buttons_frame,
            text="Salvar",
            command=self._on_save_clicked,
            width=120,
            fg_color="#28a745",
            hover_color="#218838",
        )
        self.save_btn.pack(side="left", padx=(0, 5))

        # Botão Cartão CNPJ (azul)
        self.cartao_btn = ctk.CTkButton(
            buttons_frame,
            text="Cartão CNPJ",
            command=self._on_cartao_cnpj,
            width=120,
            fg_color="#007bff",
            hover_color="#0056b3",
        )
        self.cartao_btn.pack(side="left", padx=5)

        # Botão Enviar documentos (azul)
        self.upload_btn = ctk.CTkButton(
            buttons_frame,
            text="Enviar documentos",
            command=self._on_enviar_documentos,
            width=140,
            fg_color="#007bff",
            hover_color="#0056b3",
        )
        self.upload_btn.pack(side="left", padx=5)

        # Botão Cancelar (vermelho)
        self.cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancelar",
            command=self._on_cancel,
            width=120,
            fg_color="#dc3545",
            hover_color="#c82333",
        )
        self.cancel_btn.pack(side="left", padx=5)

        # Bind Enter para salvar
        self.bind("<Return>", lambda e: self._on_save_clicked())
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _load_client_data(self) -> None:
        """Carrega dados do cliente para edição."""
        if self.client_id is None:
            return

        try:
            # Buscar cliente via service
            from src.modules.clientes import service as clientes_service

            cliente = clientes_service.fetch_cliente_by_id(self.client_id)

            if not cliente:
                log.error(f"[ClientEditor] Cliente {self.client_id} não encontrado")
                return

            self._client_data = cliente

            # Atualizar título com dados do cliente (igual ao legado)
            razao = cliente.get("razao_social", "")
            cnpj = cliente.get("cnpj", "")

            # Extrair sufixo WhatsApp das observações (se existir)
            obs = cliente.get("observacoes", "") or ""
            sufixo = ""
            if "(Não está respondendo)" in obs:
                sufixo = " (Não está respondendo)"
            elif "(Respondendo)" in obs:
                sufixo = " (Respondendo)"

            self.title(f"Editar Cliente - {self.client_id} - {razao} - {cnpj}{sufixo}")

            # Preencher campos principais
            self.razao_entry.delete(0, "end")
            self.razao_entry.insert(0, cliente.get("razao_social", ""))

            self.cnpj_entry.delete(0, "end")
            self.cnpj_entry.insert(0, cliente.get("cnpj", ""))

            self.nome_entry.delete(0, "end")
            self.nome_entry.insert(0, cliente.get("nome", ""))

            self.whatsapp_entry.delete(0, "end")
            # Campo "numero" = WhatsApp
            self.whatsapp_entry.insert(0, cliente.get("numero", "") or cliente.get("whatsapp", ""))

            # Preencher campos internos (endereço)
            # Nota: Esses campos podem não estar no banco ainda, usar valores vazios como padrão
            self.endereco_entry.delete(0, "end")
            self.endereco_entry.insert(0, cliente.get("endereco", ""))

            self.bairro_entry.delete(0, "end")
            self.bairro_entry.insert(0, cliente.get("bairro", ""))

            self.cidade_entry.delete(0, "end")
            self.cidade_entry.insert(0, cliente.get("cidade", ""))

            self.cep_entry.delete(0, "end")
            self.cep_entry.insert(0, cliente.get("cep", ""))

            # Extrair status das observações (padrão legacy: "[Status] texto")
            obs = cliente.get("observacoes", "") or cliente.get("obs", "")
            status = "Novo Cliente"  # Default

            if obs:
                # Usar método do viewmodel para extrair status
                from src.modules.clientes.viewmodel import ClientesViewModel

                vm_temp = ClientesViewModel()
                status_extracted, obs_clean = vm_temp.extract_status_and_observacoes(obs)
                if status_extracted:
                    status = status_extracted
                    obs = obs_clean

            # Aplicar status
            self.status_var.set(status)

            # Aplicar observações limpas
            if obs:
                self.obs_text.delete("1.0", "end")
                self.obs_text.insert("1.0", obs)

            log.debug(f"[ClientEditor] Dados carregados para cliente {self.client_id}")

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao carregar cliente: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Erro ao carregar dados do cliente: {e}", parent=self)

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
            from src.modules.clientes.viewmodel import ClientesViewModel

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
            }

            # FASE 3.2: Validar duplicatas antes de salvar
            from src.modules.clientes import service as clientes_service
            from tkinter import messagebox

            # Montar row (None para novo, tupla (id,) para editar)
            row = None if self.client_id is None else (self.client_id,)

            # Checar duplicatas
            duplicatas = clientes_service.checar_duplicatas_para_form(valores, row)

            # 1. CNPJ duplicado é bloqueante (hard block)
            cnpj_conflict = duplicatas.get("cnpj_conflict")
            if cnpj_conflict:
                conflicting_razao = cnpj_conflict.get("razao_social", "cliente desconhecido")
                conflicting_id = cnpj_conflict.get("id", "?")
                messagebox.showerror(
                    "CNPJ Duplicado",
                    f"O CNPJ informado já está cadastrado para:\n\n"
                    f"ID: {conflicting_id}\n"
                    f"Razão Social: {conflicting_razao}\n\n"
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
                        conf_id = conf.get("id", "?")
                        conf_razao = conf.get("razao_social", "")
                        msg_parts.append(f"  - ID {conf_id}: {conf_razao}")

                if numero_conflicts:
                    msg_parts.append("\n• Telefone similar:")
                    for conf in numero_conflicts[:3]:  # Limitar a 3
                        conf_id = conf.get("id", "?")
                        conf_razao = conf.get("razao_social", "")
                        conf_numero = conf.get("numero", "")
                        msg_parts.append(f"  - ID {conf_id}: {conf_razao} ({conf_numero})")

                msg_parts.append("\n\nDeseja prosseguir mesmo assim?")

                resposta = messagebox.askyesno("Clientes Similares", "\n".join(msg_parts), parent=self)

                if not resposta:
                    # Usuário cancelou
                    return

            # 3. Se passou as validações, salvar
            log.info(f"[ClientEditor] Salvando cliente: {valores['Razão Social']}")
            result = clientes_service.salvar_cliente_a_partir_do_form(row, valores)
            log.info(f"[ClientEditor] Cliente salvo: {result}")

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
        """Handler do botão Cancelar."""
        self.destroy()

    def _on_senhas(self) -> None:
        """Handler do botão Senhas."""
        if not self.client_id:
            from tkinter import messagebox

            messagebox.showinfo("Senhas do Cliente", "Salve o cliente antes de abrir as senhas.", parent=self)
            return

        try:
            from src.modules.passwords.helpers import open_senhas_for_cliente

            razao_text = self.razao_entry.get().strip()
            open_senhas_for_cliente(self, str(self.client_id), razao_social=razao_text)

        except Exception as e:
            log.error(f"[ClientEditor] Erro ao abrir senhas: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Falha ao abrir senhas: {e}", parent=self)

    def _on_cartao_cnpj(self) -> None:
        """Handler do botão Cartão CNPJ."""
        try:
            from tkinter.filedialog import askdirectory
            from src.modules.clientes import service as clientes_service

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

                from src.modules.clientes.viewmodel import ClientesViewModel

                vm_temp = ClientesViewModel()
                obs_completa = vm_temp.apply_status_to_observacoes(status_text, obs_body)

                valores = {
                    "Razão Social": self.razao_entry.get().strip(),
                    "CNPJ": self.cnpj_entry.get().strip(),
                    "Nome": self.nome_entry.get().strip(),
                    "WhatsApp": self.whatsapp_entry.get().strip(),
                    "Observações": obs_completa,
                }

                from src.modules.clientes import service as clientes_service

                result_save = clientes_service.salvar_cliente_a_partir_do_form(None, valores)

                # Extrair ID do resultado
                if result_save and len(result_save) > 0:
                    self.client_id = (
                        result_save[0] if isinstance(result_save[0], int) else int(result_save[0].get("id", 0))
                    )
                    self._set_window_title()

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
            from tkinter import messagebox

            messagebox.showerror("Erro", f"Erro ao enviar documentos: {e}", parent=self)
