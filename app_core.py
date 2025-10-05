from __future__ import annotations

import logging
import sqlite3
import os
from tkinter import messagebox

from ui.forms import form_cliente
from ui.lixeira import abrir_lixeira
from ui.subpastas.dialog import open_subpastas_dialog
from core.services import lixeira_service
from core.services.path_resolver import resolve_unique_path  # usa o mesmo resolver do service
from config.paths import DB_PATH, DOCS_DIR
from utils.file_utils import ensure_subpastas, write_marker
from app_utils import safe_base_from_fields
from utils.subpastas_config import load_subpastas_config

logger = logging.getLogger(__name__)
log = logger

MARKER_NAME = ".rc_client_id"


# -------- CRUD --------
def novo_cliente(app) -> None:
    log.info("app_core: novo_cliente -> abrir form")
    form_cliente(app)


def editar_cliente(app, pk: int) -> None:
    log.info("app_core: editar_cliente -> pk=%s", pk)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT ID,NUMERO,NOME,RAZAO_SOCIAL,CNPJ,ULTIMA_ALTERACAO,OBS FROM clientes WHERE ID=?",
        (pk,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        form_cliente(app, row)


# -------- Pastas / Path helpers --------
def dir_base_cliente_from_pk(pk: int) -> str:
    """
    Resolve o caminho da pasta do cliente usando o *mesmo* resolver da camada de serviços.
    - Reutiliza marcadores/slug (resolve_unique_path) em vez de varrer o diretório inteiro (O(N)).
    - Se não encontrar, faz um fallback determinístico para DOCS_DIR usando os campos do banco.
    """
    try:
        path, loc = resolve_unique_path(pk)  # loc: "live" | "trash" | None
        if path:
            log.debug("app_core: resolve_unique_path -> pk=%s path=%s loc=%s", pk, path, loc)
            return path
    except Exception:
        log.exception("app_core: resolve_unique_path falhou (pk=%s); aplicando fallback", pk)

    # fallback: compõe um nome estável a partir dos campos
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT NUMERO,CNPJ,RAZAO_SOCIAL FROM clientes WHERE ID=?", (pk,))
    row = cur.fetchone() or ("", "", "")
    conn.close()

    numero, cnpj, razao = row
    base = safe_base_from_fields(cnpj or "", numero or "", razao or "", pk)
    p = os.path.join(DOCS_DIR, base)
    log.debug("app_core: fallback path para pk=%s -> %s", pk, p)
    return p


def _ensure_live_folder_ready(pk: int) -> str:
    """
    Centraliza a garantia de que a pasta do cliente existe, tem subpastas e o marcador.
    - Usa dir_base_cliente_from_pk (que já usa o path_resolver).
    - Cria a pasta caso não exista.
    - Escreve/atualiza o marcador e garante subpastas.
    """
    path = dir_base_cliente_from_pk(pk)
    try:
        os.makedirs(path, exist_ok=True)
        ensure_subpastas(path)
        # só regrava o marcador se estiver ausente ou incorreto
        marker = os.path.join(path, MARKER_NAME)
        need_write = True
        if os.path.isfile(marker):
            try:
                with open(marker, "r", encoding="utf-8") as f:
                    need_write = (f.read().strip() != str(pk))
            except Exception:
                need_write = True
        if need_write:
            write_marker(path, pk)
    except Exception:
        log.exception("app_core: _ensure_live_folder_ready falhou (pk=%s)", pk)
        raise
    return path


def abrir_pasta(app, pk: int) -> None:
    path = _ensure_live_folder_ready(pk)
    os.startfile(path)


def ver_subpastas(app, pk: int) -> None:
    path = _ensure_live_folder_ready(pk)

    # carrega listas (achatadas) do YAML
    try:
        subps, extras = load_subpastas_config()
    except Exception:
        log.exception("app_core: load_subpastas_config falhou; usando listas vazias")
        subps, extras = [], []

    # abre o diálogo modular com as listas
    open_subpastas_dialog(app, path, subps, extras)


# -------- Lixeira (UI) --------
def abrir_lixeira_ui(app, *a, **kw):
    log.info("app_core: abrir_lixeira_ui")
    abrir_lixeira(app, *a, **kw)


def restore_ids_ui(app, ids: list[int], parent=None):
    ok_db, processadas, falhas = lixeira_service.restore_ids(ids)
    if falhas:
        messagebox.showerror("Erro", f"Falha ao restaurar {len(falhas)} cliente(s).", parent=parent)
    else:
        messagebox.showinfo("Sucesso", f"{processadas} pasta(s) restaurada(s) e {ok_db} registro(s) reativado(s).", parent=parent)
    try:
        app.carregar()
    except Exception:
        pass
    return ok_db, processadas, falhas


def purge_ids_ui(app, ids: list[int], parent=None):
    ok_db, removidas = lixeira_service.purge_ids(ids)
    if removidas:
        messagebox.showinfo("Sucesso", f"{removidas} cliente(s) apagados permanentemente!", parent=parent)
    try:
        app.carregar()
    except Exception:
        pass
    return ok_db, removidas


def enviar_para_lixeira(app, ids: list[int], parent=None) -> None:
    """
    Versão com tratamento correto de pastas ausentes:
    - Confirma com o usuário.
    - Usa o service (que já trata markers/slugs).
    - Se nada foi movido porque pastas não foram encontradas, a UI é informada.
    """
    if not ids:
        return
    if not messagebox.askyesno("Confirmar", f"Enviar {len(ids)} cliente(s) para a Lixeira?", parent=parent):
        log.info("app_core: envio para Lixeira cancelado pelo usuário. ids=%s", ids)
        return

    try:
        ok_list, falhas = lixeira_service.enviar_para_lixeira(ids)
    except Exception:
        log.exception("app_core: falha no enviar_para_lixeira (service)")
        messagebox.showerror("Erro", "Falha ao enviar para a Lixeira. Veja os logs.", parent=parent)
        return

    if not ok_list and falhas:
        # todas falharam (em geral porque pastas não foram encontradas)
        messagebox.showwarning(
            "Nada movido",
            "Nenhuma pasta foi movida.\n"
            "Possíveis causas: pastas não encontradas para os cliente(s) selecionado(s).",
            parent=parent,
        )
    elif falhas:
        messagebox.showwarning(
            "Parcial",
            f"{len(ok_list)} enviado(s), {len(falhas)} falhou(aram) para Lixeira.",
            parent=parent,
        )
    else:
        messagebox.showinfo("Sucesso", f"{len(ok_list)} cliente(s) enviados para Lixeira.", parent=parent)

    try:
        app.carregar()
    except Exception:
        pass


def restore_db_only_ui(app, ids: list[int], parent=None):
    reativados, ignorados = lixeira_service.restore_db_only(ids)
    if reativados and ignorados:
        messagebox.showwarning("Parcial", f"{reativados} reativado(s) no banco; {ignorados} ignorado(s) (tem pasta na Lixeira).", parent=parent)
    elif reativados:
        messagebox.showinfo("Sucesso", f"{reativados} cliente(s) reativado(s) no banco.", parent=parent)
    else:
        messagebox.showerror("Erro", "Nenhum cliente foi reativado. Verifique a Lixeira.", parent=parent)
    try:
        app.carregar()
    except Exception:
        pass
    return reativados, ignorados


# -------- vincular pasta manualmente --------
def vincular_pasta_ui(app, pk: int, parent=None):
    from tkinter import filedialog
    # escolher pasta
    path = filedialog.askdirectory(title="Selecione a pasta do cliente", initialdir=DOCS_DIR, parent=parent)
    if not path:
        return False, ""
    if not os.path.isdir(path):
        messagebox.showerror("Erro", "Pasta inválida.", parent=parent); return False, ""
    # não permitir _LIXEIRA
    base = os.path.basename(path)
    if base.strip().upper() == "_LIXEIRA":
        messagebox.showwarning("Aviso", "Selecione uma pasta dentro de CLIENTES, não a Lixeira.", parent=parent)
        return False, ""
    try:
        write_marker(path, str(pk))
        ensure_subpastas(path)
        messagebox.showinfo("Sucesso", f"Pasta vinculada ao cliente ID {pk}.", parent=parent)
    except Exception:
        logger.exception("Falha ao vincular pasta para ID=%s", pk)
        messagebox.showerror("Erro", "Falha ao vincular pasta. Veja o log.", parent=parent)
        return False, ""
    try:
        app.carregar()
    except Exception:
        pass
    return True, path
