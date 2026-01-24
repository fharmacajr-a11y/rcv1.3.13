"""Mixin para gerenciamento de popup de histórico de demandas."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any

from src.ui.ctk_config import ctk
from src.ui.widgets import CTkTableView

from src.ui.window_utils import (
    apply_window_icon,
    prepare_hidden_window,
    center_window_simple,
    show_centered_no_flash,
)

log = logging.getLogger(__name__)


class AnvisaHistoryPopupMixin:
    """Mixin com métodos de popup, centralização e foco."""

    def _open_history_popup(
        self, client_id: str, razao: str, cnpj: str, center: bool = True, x: int = 0, y: int = 0
    ) -> None:
        """Abre popup com histórico de demandas do cliente.

        Args:
            client_id: ID do cliente
            razao: Razão social
            cnpj: CNPJ
            center: Se True, centraliza; se False, usa x/y
            x: Posição X da tela (se center=False)
            y: Posição Y da tela (se center=False)
        """
        # Se popup já existe, atualizar e trazer para frente
        if self._history_popup and self._history_popup.winfo_exists():  # type: ignore[attr-defined]
            self._update_history_popup(client_id, razao, cnpj)
            if center:
                center_window_simple(self._history_popup, self.winfo_toplevel())  # type: ignore[attr-defined]
            self._history_popup.lift()  # type: ignore[attr-defined]
            self._history_popup.focus_force()  # type: ignore[attr-defined]
            return

        # Criar novo popup
        self._history_popup = tk.Toplevel(self)  # type: ignore[attr-defined, misc]

        # IMEDIATAMENTE preparar como hidden/offscreen para evitar flash
        prepare_hidden_window(self._history_popup)

        self._history_popup.title("Histórico de regularizações")  # type: ignore[attr-defined]
        self._history_popup.resizable(True, True)  # type: ignore[attr-defined]
        self._history_popup.transient(self.winfo_toplevel())  # type: ignore[attr-defined]
        self._history_popup.grab_set()  # type: ignore[attr-defined]

        # Aplicar ícone do app
        apply_window_icon(self._history_popup)

        # Handler de fechamento
        def on_close():
            if self._history_popup:  # type: ignore[attr-defined]
                self._history_popup.grab_release()  # type: ignore[attr-defined]
                self._history_popup.destroy()  # type: ignore[attr-defined]
            self._history_popup = None  # type: ignore[attr-defined]
            self._history_tree_popup = None  # type: ignore[attr-defined]
            self._history_iid_map.clear()  # type: ignore[attr-defined]

        self._history_popup.protocol("WM_DELETE_WINDOW", on_close)  # type: ignore[attr-defined]

        # Container principal
        main_frame = ctk.CTkFrame(self._history_popup)  # type: ignore[attr-defined]
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        cnpj_fmt = self._format_cnpj(cnpj)  # type: ignore[attr-defined]
        header_text = f"Farmácia: {razao} | CNPJ: {cnpj_fmt}"
        header_label = ctk.CTkLabel(
            main_frame,
            text=header_text,
            font=("Segoe UI", 10, "bold"),
            text_color=("#1976D2", "#64B5F6"),
        )
        header_label.pack(pady=(0, 10))

        # Frame para Treeview + Scrollbar
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Treeview
        history_cols = ("tipo", "status", "criada_em", "atualizada_em")
        self._history_tree_popup = CTkTableView(  # type: ignore[attr-defined]
            tree_frame,
            columns=history_cols,
            show="headings",
            zebra=True,
        )  # TODO: selectmode="browse" -> handle in CTk way

        self._history_tree_popup.heading("tipo", text="Tipo", anchor="w")  # type: ignore[attr-defined]
        self._history_tree_popup.heading("status", text="Status", anchor="center")  # type: ignore[attr-defined]
        self._history_tree_popup.heading("criada_em", text="Criada em", anchor="center")  # type: ignore[attr-defined]
        self._history_tree_popup.heading("atualizada_em", text="Atualizada em", anchor="center")  # type: ignore[attr-defined]

        self._history_tree_popup.column("tipo", width=250, anchor="w")  # type: ignore[attr-defined]
        self._history_tree_popup.column("status", width=120, anchor="center", stretch=False)  # type: ignore[attr-defined]
        self._history_tree_popup.column("criada_em", width=120, anchor="center", stretch=False)  # type: ignore[attr-defined]
        self._history_tree_popup.column("atualizada_em", width=140, anchor="center", stretch=False)  # type: ignore[attr-defined]

        self._history_tree_popup.pack(side="left", fill=BOTH, expand=True)  # type: ignore[attr-defined]

        # Travar redimensionamento de colunas (permite override via _lock_history_tree_columns)
        lock_cols = getattr(self, "_lock_history_tree_columns", None)
        if lock_cols is None:
            from .anvisa_screen import AnvisaScreen

            lock_cols = AnvisaScreen._lock_treeview_columns
        lock_cols(self._history_tree_popup)  # type: ignore[arg-type]

        # Bind seleção para habilitar botões
        self._history_tree_popup.bind("<<TreeviewSelect>>", lambda e: self._on_history_select())  # type: ignore[attr-defined]

        # Bind Delete para excluir demanda selecionada no popup (intercepta antes do bind global)
        def _handle_delete_key_popup(event: Any) -> str:
            self._excluir_demanda_popup(client_id)  # type: ignore[attr-defined]
            return "break"

        self._history_tree_popup.unbind("<Delete>")  # type: ignore[attr-defined]
        self._history_tree_popup.bind("<Delete>", _handle_delete_key_popup)  # type: ignore[attr-defined]

        # Painel de detalhes (Prazo + Observações)
        details_frame = ctk.CTkFrame(
            main_frame
        )  # TODO: text="Detalhes" -> usar CTkLabel separado  # TODO: padding=10 -> usar padx/pady no pack/grid
        details_frame.pack(fill="x", pady=(0, 10))
        details_frame.columnconfigure(1, weight=1)

        self._history_due_var = tk.StringVar(value="-")  # type: ignore[attr-defined]
        self._history_notes_var = tk.StringVar(value="-")  # type: ignore[attr-defined]

        ctk.CTkLabel(details_frame, text="Prazo:").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(details_frame, textvariable=self._history_due_var).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ctk.CTkLabel(details_frame, text="Observações:").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        lbl_notes = ctk.CTkLabel(details_frame, textvariable=self._history_notes_var, justify="left")
        lbl_notes.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        lbl_notes.configure(wraplength=650)

        # Barra inferior com botões
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", pady=(5, 0))

        self._btn_finalizar = ctk.CTkButton(  # type: ignore[attr-defined]
            buttons_frame,
            text="Finalizar Demanda",
            command=lambda: self._finalizar_demanda(client_id),  # type: ignore[attr-defined]
            width=18,
            state="disabled",
        )
        self._btn_finalizar.pack(side=LEFT, padx=(0, 5))  # type: ignore[attr-defined]

        self._btn_cancelar = ctk.CTkButton(  # type: ignore[attr-defined]
            buttons_frame,
            text="Cancelar",
            command=lambda: self._cancelar_demanda(client_id),  # type: ignore[attr-defined]
            width=12,
            state="disabled",
        )
        self._btn_cancelar.pack(side=LEFT, padx=(0, 5))  # type: ignore[attr-defined]

        self._btn_excluir_popup = ctk.CTkButton(  # type: ignore[attr-defined]
            buttons_frame,
            text="Excluir",
            command=lambda: self._excluir_demanda_popup(client_id),  # type: ignore[attr-defined]
            width=12,
            state="disabled",
        )
        self._btn_excluir_popup.pack(side=LEFT, padx=(0, 5))  # type: ignore[attr-defined]

        # Botão Fechar à direita
        ctk.CTkButton(
            buttons_frame,
            text="Fechar",
            command=on_close,
            width=12,
        ).pack(side="right")

        # Carregar demandas
        self._update_history_popup(client_id, razao, cnpj)

        # Centralizar popup SEM FLASH
        if center:
            show_centered_no_flash(
                self._history_popup,  # type: ignore[attr-defined]
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                width=750,
                height=480,
            )
        else:
            self._history_popup.geometry(f"750x480+{x}+{y}")  # type: ignore[attr-defined]
            self._history_popup.deiconify()  # type: ignore[attr-defined]
            self._history_popup.lift()  # type: ignore[attr-defined]
            self._history_popup.focus_force()  # type: ignore[attr-defined]

    def _update_history_popup(self, client_id: str, razao: str, cnpj: str) -> None:
        """Atualiza conteúdo do popup de histórico.

        Args:
            client_id: ID do cliente
            razao: Razão social
            cnpj: CNPJ
        """
        if not self._history_tree_popup:  # type: ignore[attr-defined]
            return

        # Atualizar header se popup existe
        if self._history_popup and self._history_popup.winfo_exists():  # type: ignore[attr-defined]
            cnpj_fmt = self._format_cnpj(cnpj)  # type: ignore[attr-defined]
            header_text = f"Farmácia: {razao} | CNPJ: {cnpj_fmt}"
            # Procurar e atualizar label do header
            for widget in self._history_popup.winfo_children():  # type: ignore[attr-defined]
                if isinstance(widget, ctk.CTkFrame):
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkLabel) and "Farmácia:" in child.cget("text"):
                            child.configure(text=header_text)
                            break

        # Limpar tree
        self._history_tree_popup.clear()  # type: ignore[attr-defined]
        self._history_iid_map.clear()  # type: ignore[attr-defined]

        # Carregar demandas
        demandas = self._load_demandas_for_cliente(client_id)  # type: ignore[attr-defined]

        if not demandas:
            # Mostrar mensagem se vazio
            self._history_tree_popup.insert(  # type: ignore[attr-defined]
                "",
                "end",
                values=["Sem demandas", "", "", ""],
            )
            return

        # Preparar rows via Service (view model com actions)
        rows = self._service.build_history_rows(demandas)  # type: ignore[attr-defined]

        # Criar mapa de request_id -> row completa (para obter actions)
        self._history_rows_by_id = {row["request_id"]: row for row in rows}  # type: ignore[attr-defined]

        # Popular tree
        for row in rows:
            dem_id = row["request_id"]

            iid = self._history_tree_popup.insert(  # type: ignore[attr-defined]
                "",
                "end",
                iid=dem_id,  # Usar request_id como iid para fácil seleção
                values=[row["tipo"], row["status_humano"], row["criada_em"], row["atualizada_em"]],
            )

            # Mapear iid -> demanda_id
            self._history_iid_map[iid] = dem_id  # type: ignore[attr-defined]

        # Auto-selecionar primeira linha (se houver demandas)
        if rows:
            first_iid = rows[0]["request_id"]
            self._history_tree_popup.focus(first_iid)  # type: ignore[attr-defined]
            self._history_tree_popup.selection_set(first_iid)  # type: ignore[attr-defined]
            # Chamar handler de seleção para atualizar prazo e botões
            self._on_history_select()  # type: ignore[attr-defined]

    def _on_history_select(self) -> None:
        """Handler de seleção no histórico do popup.

        Habilita/desabilita botões usando actions pré-calculadas pelo Service.
        Atualiza painel de detalhes com prazo e observações.
        """
        if not self._history_tree_popup:  # type: ignore[attr-defined]
            return

        item_id = self._history_tree_popup.get_selected_iid()  # type: ignore[attr-defined]
        if not item_id:
            # Nenhuma seleção válida
            if hasattr(self, "_btn_finalizar"):
                self._btn_finalizar.configure(state="disabled")  # type: ignore[attr-defined]
            if hasattr(self, "_btn_cancelar"):
                self._btn_cancelar.configure(state="disabled")  # type: ignore[attr-defined]
            if hasattr(self, "_btn_excluir_popup"):
                self._btn_excluir_popup.configure(state="disabled")  # type: ignore[attr-defined]
            # Limpar detalhes
            if hasattr(self, "_history_due_var"):
                self._history_due_var.set("-")  # type: ignore[attr-defined]
            if hasattr(self, "_history_notes_var"):
                self._history_notes_var.set("-")  # type: ignore[attr-defined]
            return

        # Verificar se item selecionado é "Sem demandas"
        item = self._history_tree_popup.item(item_id)  # type: ignore[attr-defined]
        values = item["values"]

        if not values or values[0] == "Sem demandas":
            if hasattr(self, "_btn_finalizar"):
                self._btn_finalizar.configure(state="disabled")  # type: ignore[attr-defined]
            if hasattr(self, "_btn_cancelar"):
                self._btn_cancelar.configure(state="disabled")  # type: ignore[attr-defined]
            if hasattr(self, "_btn_excluir_popup"):
                self._btn_excluir_popup.configure(state="disabled")  # type: ignore[attr-defined]
            # Limpar detalhes
            if hasattr(self, "_history_due_var"):
                self._history_due_var.set("-")  # type: ignore[attr-defined]
            if hasattr(self, "_history_notes_var"):
                self._history_notes_var.set("-")  # type: ignore[attr-defined]
            return

        # Obter row com actions pré-calculadas
        request_id = selection[0]
        row = self._history_rows_by_id.get(request_id) if hasattr(self, "_history_rows_by_id") else None  # type: ignore[attr-defined]

        if not row:
            # Fallback: desabilitar tudo se não encontrar row
            if hasattr(self, "_btn_finalizar"):
                self._btn_finalizar.configure(state="disabled")  # type: ignore[attr-defined]
            if hasattr(self, "_btn_cancelar"):
                self._btn_cancelar.configure(state="disabled")  # type: ignore[attr-defined]
            if hasattr(self, "_btn_excluir_popup"):
                self._btn_excluir_popup.configure(state="normal")  # type: ignore[attr-defined]
            # Limpar detalhes
            if hasattr(self, "_history_due_var"):
                self._history_due_var.set("-")  # type: ignore[attr-defined]
            if hasattr(self, "_history_notes_var"):
                self._history_notes_var.set("-")  # type: ignore[attr-defined]
            return

        # Usar actions pré-calculadas pelo Service
        actions = row.get("actions", {})

        # Habilitar/desabilitar botões baseado nas ações permitidas
        if hasattr(self, "_btn_finalizar"):
            state = "normal" if actions.get("close", False) else "disabled"
            self._btn_finalizar.configure(state=state)  # type: ignore[attr-defined]

        if hasattr(self, "_btn_cancelar"):
            state = "normal" if actions.get("cancel", False) else "disabled"
            self._btn_cancelar.configure(state=state)  # type: ignore[attr-defined]

        if hasattr(self, "_btn_excluir_popup"):
            state = "normal" if actions.get("delete", True) else "disabled"
            self._btn_excluir_popup.configure(state=state)  # type: ignore[attr-defined]

        # Atualizar painel de detalhes
        if hasattr(self, "_history_due_var"):
            prazo = row.get("prazo") or "-"
            self._history_due_var.set(prazo if prazo else "-")  # type: ignore[attr-defined]
        if hasattr(self, "_history_notes_var"):
            obs = row.get("observacoes") or "-"
            self._history_notes_var.set(obs if obs else "-")  # type: ignore[attr-defined]

    def _focus_history_item(self, demanda_id: str) -> None:
        """Foca/seleciona item no histórico por demanda_id.

        Abre popup se necessário e foca a demanda.

        Args:
            demanda_id: ID da demanda para focar
        """
        # Obter cliente da demanda para abrir popup correto
        # Procurar na lista principal
        for item_id in self.tree_requests.get_children():  # type: ignore[attr-defined]
            item = self.tree_requests.item(item_id)  # type: ignore[attr-defined]
            values = item["values"]
            if len(values) >= 3:
                client_id = str(values[0])
                razao = str(values[1])
                cnpj = str(values[2])

                # Verificar se essa demanda pertence a este cliente
                demandas = self._load_demandas_for_cliente(client_id)  # type: ignore[attr-defined]
                for dem in demandas:
                    if str(dem.get("id", "")) == demanda_id:
                        # Encontrou! Abrir popup
                        self._open_history_popup(client_id, razao, cnpj, center=False, x=100, y=100)

                        # Focar item no popup
                        if self._history_tree_popup and demanda_id in self._history_iid_map.values():  # type: ignore[attr-defined]
                            self._history_tree_popup.selection_set(demanda_id)  # type: ignore[attr-defined]
                            self._history_tree_popup.focus(demanda_id)  # type: ignore[attr-defined]
                            self._history_tree_popup.see(demanda_id)  # type: ignore[attr-defined]
                        return
