# ui/forms/forms.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import logging

from ui.components import toolbar_button, labeled_entry
from ui.utils import center_on_parent
from core.services.clientes_service import salvar_cliente, checar_duplicatas_info
from ui.forms.actions import preencher_via_pasta, salvar_e_importar

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

    # preencher valores iniciais
    if row:
        pk, numero, nome, razao, cnpj, ult, obs = row
        ents["Razão Social"].insert(0, razao or "")
        ents["CNPJ"].insert(0, cnpj or "")
        ents["Nome"].insert(0, nome or "")
        ents["WhatsApp"].insert(0, numero or "")
        ents["Observações"].insert("1.0", obs or "")
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

    def _confirmar_duplicatas(val: dict) -> bool:
        """Mostra popup com campos/IDs que batem; retorna True se o usuário quiser continuar."""
        info = checar_duplicatas_info(
            numero=val["WhatsApp"], cnpj=val["CNPJ"], nome=val["Nome"], razao=val["Razão Social"]
        )
        ids = info.get("ids") or []
        # se estiver editando, não considerar o próprio registro
        try:
            if row and ids and row[0] in ids:
                ids = [i for i in ids if i != row[0]]
        except Exception:
            pass
        if not ids:
            return True  # nada a avisar

        campos_batidos = ", ".join(info.get("campos") or [])
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

        # confirmar duplicatas antes de persistir
        if not _confirmar_duplicatas(val):
            return

        try:
            salvar_cliente(row, val)
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
    btns.grid(row=len(campos), column=0, columnspan=2, pady=10)

    toolbar_button(btns, text="Salvar", command=_salvar).pack(side="left", padx=5)
    toolbar_button(btns, text="Cartão CNPJ",
                   command=lambda: preencher_via_pasta(ents)).pack(side="left", padx=5)
    toolbar_button(
        btns, text="Salvar + Importar Pasta...",
        command=lambda: salvar_e_importar(self, row, ents, win)
    ).pack(side="left", padx=5)
    toolbar_button(btns, text="Cancelar", command=win.destroy).pack(side="left", padx=5)

    # centraliza e mostra
    win.update_idletasks()
    center_on_parent(self, win, win.winfo_width(), win.winfo_height())
    win.deiconify()
    win.grab_set()
    win.focus_force()
