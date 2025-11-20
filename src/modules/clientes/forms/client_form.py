# -*- coding: utf-8 -*-

# ui/forms/forms.py

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from src.modules.clientes.components.helpers import STATUS_CHOICES, STATUS_PREFIX_RE
from src.modules.clientes.components.status import apply_status_prefix
from src.modules.clientes.service import (
    checar_duplicatas_para_form,
    salvar_cliente_a_partir_do_form,
)
from src.ui.components import labeled_entry, toolbar_button
from src.ui.forms.actions import preencher_via_pasta, salvar_e_upload_docs
from src.ui.utils import center_on_parent
from ._collect import coletar_valores as _collect_values
from ._dupes import (
    ask_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)

logger = logging.getLogger(__name__)
log = logger


def form_cliente(self, row=None, preset: dict | None = None) -> None:
    win = tk.Toplevel(self)
    win.withdraw()
    win.title("Editar Cliente" if row else "Novo Cliente")
    win.transient(self)
    win.resizable(False, False)
    campos = ["Razão Social", "CNPJ", "Nome", "WhatsApp", "Observações"]
    ents: dict[str, tk.Widget] = {}
    for i, lbl in enumerate(campos):
        if lbl == "Observações":
            ttk.Label(win, text=lbl).grid(row=i, column=0, sticky="nw", padx=6, pady=4)
            ent = tk.Text(win, width=50, height=6)
            ent.grid(row=i, column=1, padx=6, pady=4, sticky="ew")
        else:
            lbl_widget, ent = labeled_entry(win, lbl)
            lbl_widget.grid(row=i, column=0, sticky="w", padx=6, pady=4)
            ent.grid(row=i, column=1, padx=6, pady=4, sticky="ew")
        ents[lbl] = ent
    win.columnconfigure(1, weight=1)
    try:
        current_client_id = int(row[0]) if row else None
    except Exception:
        current_client_id = None
    initializing: list[bool] = [True]
    _upload_button_ref: dict[str, ttk.Button | None] = {"btn": None}

    def _set_button_enabled(button: ttk.Button | None, enabled: bool) -> None:
        if button is None:
            return
        try:
            if enabled:
                button.state(["!disabled"])
            else:
                button.state(["disabled"])
        except Exception:
            try:
                button.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass

    def _refresh_send_button() -> None:
        _set_button_enabled(_upload_button_ref["btn"], True)

    class _EditFormState:
        def __init__(self, client_id: Optional[int]) -> None:
            self.client_id = client_id
            self.is_dirty = False

        def mark_dirty(self, *_args, **_kwargs) -> None:
            if initializing[0]:
                return
            if not self.is_dirty:
                self.is_dirty = True

        def mark_clean(self) -> None:
            if self.is_dirty:
                self.is_dirty = False

        def save_silent(self) -> bool:
            return _perform_save(show_success=False, close_window=False, refresh_list=True, update_row=True)

    state = _EditFormState(current_client_id)
    _refresh_send_button()

    def _bind_dirty(widget: tk.Widget) -> None:
        try:
            widget.bind("<KeyRelease>", state.mark_dirty, add="+")
            widget.bind("<<Paste>>", state.mark_dirty, add="+")
            widget.bind("<<Cut>>", state.mark_dirty, add="+")
        except Exception:
            pass

    if hasattr(self, "register_edit_form"):
        try:
            self.register_edit_form(win, state)
        except Exception:
            pass
    # --- Seção: Status do Cliente ---
    status_frame = ttk.LabelFrame(win, text="Status do Cliente")
    status_frame.grid(row=len(campos), column=0, columnspan=2, sticky="ew", padx=6, pady=(2, 6))
    status_var = tk.StringVar(value="")
    cb_status = ttk.Combobox(status_frame, textvariable=status_var, values=STATUS_CHOICES, state="readonly")
    cb_status.grid(row=0, column=0, sticky="w", padx=6, pady=6)
    ents["Status do Cliente"] = cb_status
    # preencher valores iniciais
    if row:
        pk, razao, cnpj, nome, numero, obs, ult = row
        ents["Razão Social"].insert(0, razao or "")
        ents["CNPJ"].insert(0, cnpj or "")
        ents["Nome"].insert(0, nome or "")
        ents["WhatsApp"].insert(0, numero or "")
        ents["Observações"].insert("1.0", obs or "")
        # Pré-preenche status ao editar
        try:
            obs_raw = ents["Observações"].get("1.0", "end").strip()
            m = STATUS_PREFIX_RE.match(obs_raw)
            if m:
                status_var.set(m.group("st"))
                ents["Observações"].delete("1.0", "end")
                ents["Observações"].insert("1.0", STATUS_PREFIX_RE.sub("", obs_raw, count=1).strip())
        except Exception:
            pass
    elif preset:
        if preset.get("razao"):
            ents["Razão Social"].insert(0, preset["razao"])
        if preset.get("cnpj"):
            ents["CNPJ"].insert(0, preset["cnpj"])
    for widget in ents.values():
        _bind_dirty(widget)
    cb_status.bind("<<ComboboxSelected>>", state.mark_dirty, add="+")
    status_var.trace_add("write", lambda *_: state.mark_dirty())

    def _confirmar_duplicatas(val: dict, row=None, win=None, *, exclude_id: Optional[int] = None) -> bool:
        info = checar_duplicatas_para_form(val, row=row, exclude_id=exclude_id)
        if has_cnpj_conflict(info):
            show_cnpj_warning_and_abort(win, info)
            return False
        if has_razao_conflict(info):
            if not ask_razao_confirm(win, info):
                return False
        return True

    def _perform_save(
        *,
        show_success: bool,
        close_window: bool,
        refresh_list: bool = True,
        update_row: bool = True,
    ) -> bool:
        nonlocal row
        val = _collect_values(ents)
        obs = val.get("Observações", "")
        chosen = status_var.get().strip()
        val["Observações"] = apply_status_prefix(obs, chosen)
        if not _confirmar_duplicatas(val, row=row, win=win, exclude_id=current_client_id):
            return False
        try:
            saved_id, _ = salvar_cliente_a_partir_do_form(row, val)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=win)
            return False
        state.client_id = saved_id
        state.mark_clean()
        if update_row:
            if row:
                row = (saved_id,) + tuple(row[1:])
            else:
                row = (saved_id,)
        try:
            _refresh_send_button()
        except Exception:
            pass
        if refresh_list:
            try:
                self.carregar()
            except Exception:
                pass
        if show_success:
            messagebox.showinfo("Sucesso", "Cliente salvo.", parent=win)
        if close_window:
            try:
                if hasattr(self, "unregister_edit_form"):
                    self.unregister_edit_form(win)
            except Exception:
                pass
            win.destroy()
        return True

    def _persist_client(*, refresh_list: bool = False, update_row: bool = False) -> bool:
        """
        Salva cliente sem fechar a janela nem for?ar refresh da lista.
        """
        return _perform_save(
            show_success=False,
            close_window=False,
            refresh_list=refresh_list,
            update_row=update_row,
        )

    def _salvar():
        ok = _perform_save(show_success=True, close_window=True)
        return ok

    def _salvar_e_enviar():
        nonlocal row
        recem_criado_no_envio = False
        if state.client_id is None:
            # cria o cliente sem fechar/refresh de lista
            created_ok = _persist_client(
                refresh_list=False,
                update_row=False,
            )
            if not created_ok:
                return
            recem_criado_no_envio = True
            try:
                row = (state.client_id,)
            except Exception:
                pass
            try:
                self._force_client_id_for_upload = state.client_id
                self._upload_force_is_new = True
            except Exception:
                pass
        else:
            try:
                self._force_client_id_for_upload = state.client_id
            except Exception:
                pass

        # Pipeline completo: subpasta, sele??o de PASTA e barra de progresso
        if recem_criado_no_envio:
            try:
                state.is_dirty = False
            except Exception:
                pass
        salvar_e_upload_docs(self, row, ents, None, win, skip_duplicate_prompt=True)

    # --- Botões ---
    btns = ttk.Frame(win)
    btns.grid(row=len(campos) + 1, column=0, columnspan=2, pady=10)
    toolbar_button(btns, text="Salvar", command=_salvar).pack(side="left", padx=5)
    # Botão Cartão CNPJ com bloqueio de múltiplas aberturas
    btn_cartao_cnpj = toolbar_button(btns, text="Cartão CNPJ", command=lambda: None)
    btn_cartao_cnpj.pack(side="left", padx=5)
    # Flag para controlar reentrância
    _cnpj_busy = [False]  # usar lista para mutabilidade em closure

    def _on_cartao_cnpj():
        """Handler com bloqueio de múltiplos cliques."""
        if _cnpj_busy[0]:
            return
        _cnpj_busy[0] = True
        try:
            # Desativa visualmente o botão
            try:
                btn_cartao_cnpj.state(["disabled"])
            except Exception:
                try:
                    btn_cartao_cnpj.configure(state="disabled")
                except Exception:
                    pass
            # Chama a função original de preenchimento
            preencher_via_pasta(ents)
            state.mark_dirty()
        finally:
            # Reativa o botão após o processamento
            _cnpj_busy[0] = False
            try:
                btn_cartao_cnpj.state(["!disabled"])
            except Exception:
                try:
                    btn_cartao_cnpj.configure(state="normal")
                except Exception:
                    pass

    btn_cartao_cnpj.configure(command=_on_cartao_cnpj)
    btn_salvar_enviar = toolbar_button(
        btns,
        text="Enviar documentos",
        command=_salvar_e_enviar,
    )
    btn_salvar_enviar.pack(side="left", padx=5)
    _upload_button_ref["btn"] = btn_salvar_enviar
    _refresh_send_button()

    def _cancelar():
        try:
            if hasattr(self, "unregister_edit_form"):
                self.unregister_edit_form(win)
        except Exception:
            pass
        win.destroy()

    toolbar_button(btns, text="Cancelar", command=_cancelar).pack(side="left", padx=5)

    def _on_close() -> None:
        try:
            if hasattr(self, "unregister_edit_form"):
                self.unregister_edit_form(win)
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)
    initializing[0] = False
    # centraliza e mostra
    win.update_idletasks()
    center_on_parent(win, self)
    win.deiconify()
    win.grab_set()
    win.focus_force()
