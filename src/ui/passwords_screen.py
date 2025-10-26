# -*- coding: utf-8 -*-
# gui/passwords_screen.py
"""Tela de gerenciamento de senhas (CRUD + criptografia)."""

from __future__ import annotations

import tkinter as tk
import logging
from tkinter import messagebox, ttk
from typing import Optional

import ttkbootstrap as tb

from data.supabase_repo import (
    list_passwords,
    add_password,
    update_password,
    delete_password,
    decrypt_for_view,
)

log = logging.getLogger(__name__)


class PasswordsScreen(tb.Frame):
    """
    Tela de gerenciamento de senhas com:
    - Esquerda: Treeview com lista de senhas (senha sempre mascarada)
    - Direita: Formulário de edição/criação
    """

    def __init__(self, master, main_window=None, **kwargs) -> None:
        super().__init__(master, padding=10, **kwargs)
        
        self._org_id: Optional[str] = None
        self._user_id: Optional[str] = None
        self._current_id: Optional[int] = None
        self._password_visible = False
        self.main_window = main_window  # Referência para MainWindow
        
        # Cliente Supabase (lazy)
        self._supabase = None
        
        # Grid principal: 2 colunas (lista | formulário)
        self.columnconfigure(0, weight=2, minsize=500)
        self.columnconfigure(1, weight=1, minsize=400)
        self.rowconfigure(0, weight=1)
        
        self._build_list_panel()
        self._build_form_panel()
        
    def _build_list_panel(self) -> None:
        """Constrói painel esquerdo com Treeview."""
        frame = tb.Labelframe(self, text="Senhas Cadastradas", padding=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        
        # Treeview
        columns = ("cliente", "servico", "usuario", "senha", "atualizado")
        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15,
        )
        
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("servico", text="Serviço")
        self.tree.heading("usuario", text="Usuário")
        self.tree.heading("senha", text="Senha")
        self.tree.heading("atualizado", text="Atualizado")
        
        self.tree.column("cliente", width=150)
        self.tree.column("servico", width=120)
        self.tree.column("usuario", width=120)
        self.tree.column("senha", width=80)
        self.tree.column("atualizado", width=140)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind: ao selecionar, carregar no formulário
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
    def _build_form_panel(self) -> None:
        """Constrói painel direito com formulário."""
        frame = tb.Labelframe(self, text="Detalhes", padding=10)
        frame.grid(row=0, column=1, sticky="nsew")
        
        # Labels e entries
        row = 0
        
        # Cliente com botão de seleção
        tb.Label(frame, text="Cliente (CNPJ):").grid(row=row, column=0, sticky="w", pady=4)
        
        cliente_container = tb.Frame(frame)
        cliente_container.grid(row=row, column=1, sticky="ew", pady=4, padx=(5, 0))
        cliente_container.columnconfigure(0, weight=1)
        
        self.entry_cliente = tb.Entry(cliente_container, width=25)
        self.entry_cliente.grid(row=0, column=0, sticky="ew")
        
        self.btn_selecionar_cliente = tb.Button(
            cliente_container,
            text="Selecionar…",
            width=12,
            command=self._open_clients_picker,
            bootstyle="info-outline",
        )
        self.btn_selecionar_cliente.grid(row=0, column=1, padx=(4, 0))
        row += 1
        
        tb.Label(frame, text="Serviço:").grid(row=row, column=0, sticky="w", pady=4)
        self.entry_servico = tb.Entry(frame, width=30)
        self.entry_servico.grid(row=row, column=1, sticky="ew", pady=4, padx=(5, 0))
        row += 1
        
        tb.Label(frame, text="Usuário:").grid(row=row, column=0, sticky="w", pady=4)
        self.entry_usuario = tb.Entry(frame, width=30)
        self.entry_usuario.grid(row=row, column=1, sticky="ew", pady=4, padx=(5, 0))
        row += 1
        
        # Senha com botão de toggle visibilidade
        tb.Label(frame, text="Senha:").grid(row=row, column=0, sticky="w", pady=4)
        senha_frame = tb.Frame(frame)
        senha_frame.grid(row=row, column=1, sticky="ew", pady=4, padx=(5, 0))
        senha_frame.columnconfigure(0, weight=1)
        
        self.entry_senha = tb.Entry(senha_frame, show="•", width=25)
        self.entry_senha.grid(row=0, column=0, sticky="ew")
        
        self.btn_toggle_senha = tb.Button(
            senha_frame,
            text="👁️",
            width=3,
            command=self._toggle_password_visibility,
            bootstyle="secondary-outline",
        )
        self.btn_toggle_senha.grid(row=0, column=1, padx=(4, 0))
        row += 1
        
        # Notas (Text)
        tb.Label(frame, text="Notas:").grid(row=row, column=0, sticky="nw", pady=4)
        self.text_notas = tk.Text(frame, width=30, height=6, wrap="word")
        self.text_notas.grid(row=row, column=1, sticky="ew", pady=4, padx=(5, 0))
        row += 1
        
        # Espaçador
        tb.Label(frame, text="").grid(row=row, column=0, pady=8)
        row += 1
        
        # Botões de ação
        btn_frame = tb.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        self.btn_adicionar = tb.Button(
            btn_frame,
            text="➕ Adicionar",
            command=self._add_password,
            bootstyle="success",
        )
        self.btn_adicionar.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        
        self.btn_salvar = tb.Button(
            btn_frame,
            text="💾 Salvar",
            command=self._save_password,
            bootstyle="primary",
        )
        self.btn_salvar.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        
        self.btn_excluir = tb.Button(
            btn_frame,
            text="🗑️ Excluir",
            command=self._delete_password,
            bootstyle="danger",
        )
        self.btn_excluir.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        
        self.btn_copiar_usuario = tb.Button(
            btn_frame,
            text="📋 Copiar Usuário",
            command=self._copy_username,
            bootstyle="info",
        )
        self.btn_copiar_usuario.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        
        self.btn_copiar_senha = tb.Button(
            btn_frame,
            text="🔑 Copiar Senha",
            command=self._copy_password,
            bootstyle="warning",
        )
        self.btn_copiar_senha.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        
        self.btn_limpar = tb.Button(
            btn_frame,
            text="🆕 Novo",
            command=self._clear_form,
            bootstyle="secondary",
        )
        self.btn_limpar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        
        frame.columnconfigure(1, weight=1)
        
    def _toggle_password_visibility(self) -> None:
        """Alterna visibilidade da senha no campo de entrada."""
        if self._password_visible:
            self.entry_senha.configure(show="•")
            self.btn_toggle_senha.configure(text="👁️")
            self._password_visible = False
        else:
            self.entry_senha.configure(show="")
            self.btn_toggle_senha.configure(text="🙈")
            self._password_visible = True
    
    def _open_clients_picker(self) -> None:
        """Abre tela de Clientes em modo seleção."""
        if self.main_window is None:
            messagebox.showwarning("Atenção", "Tela de clientes não disponível.")
            return
        
        def _on_client_picked(info: dict):
            cnpj_fmt = (info or {}).get("cnpj", "")
            # Preencher com CNPJ completo (com máscara)
            self.entry_cliente.delete(0, tk.END)
            self.entry_cliente.insert(0, cnpj_fmt)
        
        try:
            self.main_window.open_clients_picker(on_pick=_on_client_picked)
        except Exception as e:
            log.exception("Erro ao abrir seleção de clientes")
            messagebox.showerror("Erro", f"Não foi possível abrir a lista de clientes.\n{e}")
            
    def _on_tree_select(self, event) -> None:
        """Carrega dados do registro selecionado no formulário."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        if not values:
            return
        
        # values: (cliente, servico, usuario, "••••••", atualizado)
        # Precisamos do ID do registro (armazenado em tags)
        tags = self.tree.item(item_id, "tags")
        if not tags:
            return
        
        try:
            record_id = int(tags[0])
        except (ValueError, IndexError):
            return
        
        self._current_id = record_id
        
        # Carregar dados no formulário
        self.entry_cliente.delete(0, tk.END)
        self.entry_cliente.insert(0, values[0])
        
        self.entry_servico.delete(0, tk.END)
        self.entry_servico.insert(0, values[1])
        
        self.entry_usuario.delete(0, tk.END)
        self.entry_usuario.insert(0, values[2])
        
        # Senha: deixar vazia (não exibir a senha criptografada)
        self.entry_senha.delete(0, tk.END)
        
        # Notas: buscar do cache
        self.text_notas.delete("1.0", tk.END)
        for record in getattr(self, "_cached_records", []):
            if record.get("id") == record_id:
                self.text_notas.insert("1.0", record.get("notes", ""))
                break
                
    def _clear_form(self) -> None:
        """Limpa o formulário para criar novo registro."""
        self._current_id = None
        self.entry_cliente.delete(0, tk.END)
        self.entry_servico.delete(0, tk.END)
        self.entry_usuario.delete(0, tk.END)
        self.entry_senha.delete(0, tk.END)
        self.text_notas.delete("1.0", tk.END)
        self.tree.selection_remove(*self.tree.selection())
        
    def _ensure_logged_for_write(self) -> None:
        """Garante que existe sessão válida antes de operação de escrita."""
        # [finalize-notes] import seguro dentro de função
        from infra.supabase_client import get_supabase, bind_postgrest_auth_if_any
        from data.auth_bootstrap import _get_access_token
        from src.ui.login_dialog import LoginDialog
        
        client = get_supabase()
        bind_postgrest_auth_if_any(client)
        
        if not _get_access_token(client):
            # Sessão ausente/expirada -> abrir login
            log.warning("Sessão ausente/expirada - abrindo diálogo de login...")
            dlg = LoginDialog(self.winfo_toplevel())
            self.winfo_toplevel().wait_window(dlg)
            bind_postgrest_auth_if_any(client)
            
            if not _get_access_token(client):
                raise RuntimeError("Sessão ausente após tentativa de login.")
        
    def _add_password(self) -> None:
        """Adiciona novo registro."""
        if not self._org_id or not self._user_id:
            messagebox.showerror("Erro", "Usuário não autenticado ou organização não definida.")
            return
        
        cliente = self.entry_cliente.get().strip()
        servico = self.entry_servico.get().strip()
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get()
        notas = self.text_notas.get("1.0", tk.END).strip()
        
        if not cliente or not servico:
            messagebox.showwarning("Atenção", "Cliente e Serviço são obrigatórios.")
            return
        
        try:
            # Garantir que existe sessão válida antes de escrita
            self._ensure_logged_for_write()
            
            add_password(
                org_id=self._org_id,
                client_name=cliente,
                service=servico,
                username=usuario,
                password_plain=senha,
                notes=notas,
                created_by=self._user_id,
            )
            messagebox.showinfo("Sucesso", "Senha adicionada com sucesso!")
            self._clear_form()
            self.refresh()
        except RuntimeError as e:
            msg = str(e)
            if "sessão" in msg.lower():
                messagebox.showerror("Sessão Expirada", "Sua sessão expirou. Faça login novamente para continuar.")
                return
            raise
        except Exception as e:
            log.exception("Erro ao adicionar senha")
            messagebox.showerror("Erro", f"Falha ao adicionar senha:\n{e}")
            
    def _save_password(self) -> None:
        """Atualiza registro existente."""
        if not self._current_id:
            messagebox.showwarning("Atenção", "Selecione um registro para salvar.")
            return
        
        cliente = self.entry_cliente.get().strip()
        servico = self.entry_servico.get().strip()
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get()
        notas = self.text_notas.get("1.0", tk.END).strip()
        
        if not cliente or not servico:
            messagebox.showwarning("Atenção", "Cliente e Serviço são obrigatórios.")
            return
        
        try:
            # Garantir que existe sessão válida antes de escrita
            self._ensure_logged_for_write()
            
            # Se senha estiver vazia, não atualizar (None = não modificar)
            password_arg = senha if senha else None
            
            update_password(
                id=self._current_id,
                client_name=cliente,
                service=servico,
                username=usuario,
                password_plain=password_arg,
                notes=notas,
            )
            messagebox.showinfo("Sucesso", "Senha atualizada com sucesso!")
            self.refresh()
        except RuntimeError as e:
            msg = str(e)
            if "sessão" in msg.lower():
                messagebox.showerror("Sessão Expirada", "Sua sessão expirou. Faça login novamente para continuar.")
                return
            raise
        except Exception as e:
            log.exception("Erro ao atualizar senha")
            messagebox.showerror("Erro", f"Falha ao atualizar senha:\n{e}")
            
    def _delete_password(self) -> None:
        """Remove registro selecionado."""
        if not self._current_id:
            messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
            return
        
        confirm = messagebox.askyesno(
            "Confirmação",
            "Tem certeza que deseja excluir este registro?\nEsta ação não pode ser desfeita.",
        )
        if not confirm:
            return
        
        try:
            # Garantir que existe sessão válida antes de escrita
            self._ensure_logged_for_write()
            
            delete_password(self._current_id)
            messagebox.showinfo("Sucesso", "Senha excluída com sucesso!")
            self._clear_form()
            self.refresh()
        except RuntimeError as e:
            msg = str(e)
            if "sessão" in msg.lower():
                messagebox.showerror("Sessão Expirada", "Sua sessão expirou. Faça login novamente para continuar.")
                return
            raise
        except Exception as e:
            log.exception("Erro ao excluir senha")
            messagebox.showerror("Erro", f"Falha ao excluir senha:\n{e}")
            
    def _copy_username(self) -> None:
        """Copia usuário para o clipboard."""
        usuario = self.entry_usuario.get().strip()
        if not usuario:
            messagebox.showwarning("Atenção", "Nenhum usuário para copiar.")
            return
        
        try:
            self.clipboard_clear()
            self.clipboard_append(usuario)
            messagebox.showinfo("Sucesso", "Usuário copiado para a área de transferência!")
        except Exception as e:
            log.exception("Erro ao copiar usuário")
            messagebox.showerror("Erro", f"Falha ao copiar:\n{e}")
            
    def _copy_password(self) -> None:
        """
        Descriptografa e copia a senha para o clipboard SEM exibir em tela.
        """
        if not self._current_id:
            messagebox.showwarning("Atenção", "Selecione um registro para copiar a senha.")
            return
        
        # Buscar token criptografado do cache
        password_enc = None
        for record in getattr(self, "_cached_records", []):
            if record.get("id") == self._current_id:
                password_enc = record.get("password_enc", "")
                break
        
        if not password_enc:
            messagebox.showwarning("Atenção", "Senha não encontrada ou vazia.")
            return
        
        try:
            plain = decrypt_for_view(password_enc)
            if not plain:
                messagebox.showwarning("Atenção", "Senha vazia.")
                return
            
            self.clipboard_clear()
            self.clipboard_append(plain)
            messagebox.showinfo("Sucesso", "Senha copiada para a área de transferência!\n(não exibida por segurança)")
        except Exception as e:
            log.exception("Erro ao copiar senha")
            messagebox.showerror("Erro", f"Falha ao copiar senha:\n{e}")
            
    def refresh(self) -> None:
        """Recarrega a lista de senhas do Supabase."""
        if not self._org_id:
            log.warning("refresh() chamado sem org_id definido")
            return
        
        try:
            records = list_passwords(self._org_id)
            self._cached_records = records
            
            # Limpar árvore
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Preencher árvore
            for record in records:
                # Formatar data
                updated = record.get("updated_at", "")
                if updated:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        updated = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                
                # Inserir linha (senha sempre mascarada)
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        record.get("client_name", ""),
                        record.get("service", ""),
                        record.get("username", ""),
                        "••••••",
                        updated,
                    ),
                    tags=(str(record.get("id", "")),),
                )
        except Exception as e:
            log.exception("Erro ao carregar senhas")
            messagebox.showerror("Erro", f"Falha ao carregar senhas:\n{e}")
            
    def on_show(self) -> None:
        """
        Chamado quando a tela é exibida.
        Atualiza org_id/user_id e recarrega dados.
        """
        # Obter org_id e user_id do app
        try:
            from infra.supabase_client import supabase
            self._supabase = supabase  # Salvar referência ao cliente
            user = supabase.auth.get_user()
            if user and hasattr(user, "user") and user.user:
                self._user_id = user.user.id
                
                # Tentar obter org_id via app (main_window)
                app = self.winfo_toplevel()
                if hasattr(app, "_get_org_id_cached"):
                    self._org_id = app._get_org_id_cached(self._user_id)
                    
        except Exception as e:
            log.exception("Erro ao obter user/org info")
            messagebox.showerror("Erro", f"Falha ao obter informações do usuário:\n{e}")
            return
        
        if not self._org_id:
            messagebox.showerror("Erro", "Organização não identificada. Faça login novamente.")
            return
        
        self.refresh()
