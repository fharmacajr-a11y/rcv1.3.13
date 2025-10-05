# ui/forms/actions.py
from __future__ import annotations

import os
import shutil
import logging
from tkinter import filedialog, messagebox

from utils.file_utils import list_and_classify_pdfs, find_cartao_cnpj_pdf
from utils.pdf_reader import read_pdf_text
from utils.text_utils import extract_company_fields
from core.services.clientes_service import salvar_cliente, checar_duplicatas_info

log = logging.getLogger(__name__)
DEFAULT_IMPORT_SUBFOLDER = "SIFAP"


def preencher_via_pasta(ents: dict) -> None:
    """Preenche campos a partir de uma pasta contendo Cartão CNPJ/PDF."""
    base = filedialog.askdirectory(title="Escolha a pasta do cliente (com o Cartão CNPJ)")
    if not base:
        return

    docs = list_and_classify_pdfs(base)
    cnpj = razao = None
    for d in docs:
        if d.get("type") == "cnpj_card":
            meta = d.get("meta") or {}
            cnpj = meta.get("cnpj")
            razao = meta.get("razao_social")
            break

    if not (cnpj or razao):
        pdf = find_cartao_cnpj_pdf(base)
        if pdf:
            text = read_pdf_text(pdf) or ""
            fields = extract_company_fields(text) if text else {}
            cnpj = fields.get("cnpj")
            razao = fields.get("razao_social")

    if not (cnpj or razao):
        messagebox.showwarning("Atenção", "Nenhum Cartão CNPJ válido encontrado.")
        return

    if "Razão Social" in ents:
        ents["Razão Social"].delete(0, "end")
        if razao: ents["Razão Social"].insert(0, razao)
    if "CNPJ" in ents:
        ents["CNPJ"].delete(0, "end")
        if cnpj: ents["CNPJ"].insert(0, cnpj)


def salvar_e_importar(self, row, ents: dict, win=None) -> None:
    """Salva o cliente e, em seguida, importa uma pasta para SIFAP dentro da pasta do cliente."""
    valores = {
        "Razão Social": ents["Razão Social"].get().strip(),
        "CNPJ":         ents["CNPJ"].get().strip(),
        "Nome":         ents["Nome"].get().strip(),
        "WhatsApp":     ents["WhatsApp"].get().strip(),
        "Observações":  ents["Observações"].get("1.0", "end-1c").strip(),
    }

    # Preflight de duplicatas (mesma regra do botão Salvar)
    try:
        info = checar_duplicatas_info(
            numero=valores.get('WhatsApp'),
            cnpj=valores.get('CNPJ'),
            nome=valores.get('Nome'),
            razao=valores.get('Razão Social'),
        )
        ids = info.get('ids') or []
        try:
            if row and ids and int(row[0]) in ids:
                ids = [i for i in ids if i != int(row[0])]
        except Exception:
            pass
        if ids:
            campos = ', '.join(info.get('campos') or [])
            ids_str = ', '.join(str(i) for i in ids)
            campos_txt = campos or '-'
            msg = (
                'Possível duplicata detectada.\n\n'
                f'Campos que bateram: {campos_txt}\n'
                f'IDs encontrados: {ids_str}\n\n'
                'Deseja continuar mesmo assim?'
            )
            if not messagebox.askokcancel('Possível duplicata', msg):
                return
    except Exception:
        pass

    try:
        _, pasta = salvar_cliente(row, valores)
    except Exception as e:
        messagebox.showerror("Erro", str(e))
        return

    src = filedialog.askdirectory(title="Escolha a pasta já existente para importar")
    if not src:
        # salvou sem importar
        try: self.carregar()
        except Exception: pass
        messagebox.showinfo("Sucesso", "Cliente salvo.")
        if win: win.destroy()
        return

    dst = os.path.join(pasta, DEFAULT_IMPORT_SUBFOLDER)
    os.makedirs(dst, exist_ok=True)

    falhas = 0
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        try:
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        except Exception:
            falhas += 1
            log.exception("Falha ao copiar %s -> %s", s, d)

    try: self.carregar()
    except Exception: pass

    msg = "Pasta importada para SIFAP." if falhas == 0 else f"Pasta importada com {falhas} falha(s)."
    messagebox.showinfo("Sucesso", msg)
    if win:
        win.destroy()
