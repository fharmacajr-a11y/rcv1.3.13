# ui/forms/forms.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, Listbox
import logging

from ui.components import toolbar_button, labeled_entry
from core.services.clientes_service import salvar_cliente, checar_duplicatas_info
from ui.forms.actions import preencher_via_pasta, salvar_e_enviar_para_supabase
from infra.supabase_client import supabase  # cliente Supabase

try:
    from ui import center_on_parent
except Exception:  # pragma: no cover
    try:
        from ui.utils import center_on_parent
    except Exception:  # pragma: no cover
        def center_on_parent(win, parent=None, pad=0):
            return win

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

    # --- Seção: Documentos no Supabase (somente informativa) ---
    docs_frame = ttk.LabelFrame(win, text="Documentos no Supabase")
    docs_frame.grid(row=len(campos), column=0, columnspan=2, sticky="nsew", padx=6, pady=(2, 6))
    docs_frame.columnconfigure(0, weight=1)
    listbox_docs = Listbox(docs_frame, height=5)
    listbox_docs.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(docs_frame, orient="vertical", command=listbox_docs.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    listbox_docs.configure(yscrollcommand=scrollbar.set)

    # preencher valores iniciais
    if row:
        pk, razao, cnpj, nome, numero, obs, ult = row
        ents["Razão Social"].insert(0, razao or "")
        ents["CNPJ"].insert(0, cnpj or "")
        ents["Nome"].insert(0, nome or "")
        ents["WhatsApp"].insert(0, numero or "")
        ents["Observações"].insert("1.0", obs or "")
        # carregar docs existentes (opcional)
        try:
            resp = supabase.table('documents').select('title').eq('client_id', pk).execute()
            for doc in (resp.data or []):
                listbox_docs.insert("end", f"{doc.get('title') or '-'} (já no Supabase)")
        except Exception as e:
            log.warning("Erro ao carregar docs existentes: %s", e)
    elif preset:
        if preset.get("razao"): ents["Razão Social"].insert(0, preset["razao"])
        if preset.get("cnpj"):  ents["CNPJ"].insert(0, preset["cnpj"])

    def _coletar_valores() -> dict:
        return {
            "Razão Social": ents["Razão Social"].get().strip(),
            "CNPJ":         ents["CNPJ"].get().strip(),
            "Nome":         ents["Nome"].get().strip(),
            "WhatsApp":     ents["WhatsApp"].get().strip(),
            "Observações":  ents["Observações"].get("1.0", "end").strip(),
        }

    def _confirmar_duplicatas(val: dict, row=None, win=None) -> bool:
        # Passa nome/numero para respeitar a assinatura; vamos filtrar depois
        info = checar_duplicatas_info(
            cnpj=val.get("CNPJ"),
            razao=val.get("Razão Social"),
            numero=val.get("WhatsApp"),
            nome=val.get("Nome"),
        )
        # Se estiver editando, remova o próprio ID
        ids = (info.get("ids") or [])[:]
        try:
            if row and ids and int(row[0]) in ids:
                ids = [i for i in ids if i != int(row[0])]
        except Exception:
            pass

        # Considere apenas CNPJ / RAZAO_SOCIAL para alertar
        campos_info = [c for c in (info.get("campos") or []) if c in ("CNPJ", "RAZAO_SOCIAL")]
        if not ids or not campos_info:
            return True
        campos_batidos = ", ".join(campos_info)
        ids_str = ", ".join(str(i) for i in ids)
        msg = (
            "Possível duplicata detectada.\n\n"
            f"Campos que bateram: {campos_batidos or '-'}\n"
            f"IDs encontrados: {ids_str}\n\n"
            "Deseja continuar mesmo assim?"
        )
        return messagebox.askokcancel("Possível duplicata", msg, parent=win)

    def _salvar():
        val = _coletar_valores()
        if not _confirmar_duplicatas(val):
            return
        try:
            salvar_cliente(row, val)  # mantém assinatura original (service decide insert/update)
        except Exception as e:
            messagebox.showerror("Erro", str(e)); return
        win.destroy()
        try:
            self.carregar()
        except Exception:
            pass
        messagebox.showinfo("Sucesso", "Cliente salvo.")

    # --- Botões ---
    btns = ttk.Frame(win)
    btns.grid(row=len(campos)+1, column=0, columnspan=2, pady=10)

    toolbar_button(btns, text="Salvar", command=_salvar).pack(side="left", padx=5)
    toolbar_button(btns, text="Cartão CNPJ",
                   command=lambda: preencher_via_pasta(ents)).pack(side="left", padx=5)
    toolbar_button(
        btns, text="Salvar + Enviar para Supabase",
        command=lambda: salvar_e_enviar_para_supabase(self, row, ents, win)
    ).pack(side="left", padx=5)
    toolbar_button(btns, text="Cancelar", command=win.destroy).pack(side="left", padx=5)

    # centraliza e mostra
    win.update_idletasks()
    center_on_parent(win, self)
    win.deiconify()
    win.grab_set()
    win.focus_force()
