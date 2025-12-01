from __future__ import annotations

import hashlib
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta
from src.modules.uploads.external_upload_service import (
    salvar_e_enviar_para_supabase_service,
)

# LAZY IMPORT: form_service movido para dentro de salvar_e_upload_docs (quebra ciclo)
# from src.modules.uploads.form_service import salvar_e_upload_docs_service
from src.modules.uploads.storage_browser_service import (
    download_file_service,
    list_storage_objects_service,
)
from src.utils.validators import only_digits

from src.modules.uploads.uploader_supabase import _select_pdfs_dialog

# ui/forms/actions.py

# Phase 1: shared helpers with defensive fallbacks
try:
    from src.utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover

    def _sha256(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()


log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# utils locais
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Preenchimento via Cartão CNPJ
# -----------------------------------------------------------------------------
def preencher_via_pasta(ents: dict) -> None:
    """
    Preenche campos do formulário a partir de Cartão CNPJ em pasta (UI layer).

    Responsabilidades:
    - Abrir diálogo de seleção de pasta (UI)
    - Delegar extração de dados ao service
    - Mostrar messagebox de aviso se não encontrar (UI)
    - Preencher campos do formulário (UI)
    """
    # 1. SELEÇÃO DE PASTA (UI)
    base = filedialog.askdirectory(title="Escolha a pasta do cliente (com o Cartão CNPJ)")
    if not base:
        return

    # 2. DELEGAR EXTRAÇÃO AO SERVICE (headless)
    result = extrair_dados_cartao_cnpj_em_pasta(base)
    cnpj = result.get("cnpj")
    razao = result.get("razao_social")

    # 3. VALIDAR RESULTADO E MOSTRAR AVISO SE NECESSÁRIO (UI)
    if not (cnpj or razao):
        messagebox.showwarning("Atenção", "Nenhum Cartão CNPJ válido encontrado.")
        return

    # 4. PREENCHER CAMPOS DO FORMULÁRIO (UI)
    if "Razão Social" in ents:
        ents["Razão Social"].delete(0, "end")
        if razao:
            ents["Razão Social"].insert(0, razao)

    if "CNPJ" in ents:
        ents["CNPJ"].delete(0, "end")
        if cnpj:
            ents["CNPJ"].insert(0, only_digits(cnpj))


# -----------------------------------------------------------------------------
# Upload com telinha (thread) – usado por "Salvar + Enviar para Supabase"
# -----------------------------------------------------------------------------
def salvar_e_enviar_para_supabase(self, row, ents, win=None):
    """
    Orquestra o fluxo de salvar + enviar documentos para armazenamento externo (UI layer).

    Responsabilidades:
    - Coletar seleção de arquivos via diálogo (UI)
    - Montar o contexto com dados coletados
    - Delegar a lógica de negócio ao service headless
    - Reagir ao resultado (exibir messageboxes se necessário)
    """
    # 1. SELEÇÃO DE ARQUIVOS (responsabilidade UI)
    parent = win or self
    files = _select_pdfs_dialog(parent=parent)

    # 2. MONTAR CONTEXTO PARA O SERVICE
    ctx = {
        "self": self,
        "row": row,
        "ents": ents,
        "win": win,
        "files": files,
    }

    # 3. DELEGAR AO SERVICE (headless, sem Tk)
    service_result = salvar_e_enviar_para_supabase_service(ctx)

    # 4. REAGIR AO RESULTADO (UI: messageboxes)
    # O service indica se deve mostrar UI e qual tipo de mensagem
    if service_result.get("should_show_ui"):
        msg_type = service_result.get("ui_message_type")
        title = service_result.get("ui_message_title", "")
        body = service_result.get("ui_message_body", "")

        win_parent: tk.Misc | None = win if isinstance(win, tk.Misc) else None

        if msg_type == "warning":
            messagebox.showwarning(title, body, parent=win_parent)
        elif msg_type == "error":
            messagebox.showerror(title, body, parent=win_parent)
        elif msg_type == "info":
            messagebox.showinfo(title, body, parent=win_parent)

    return service_result.get("result")


# -----------------------------------------------------------------------------
# “Ver Subpastas” – manter compatível com app_gui
# -----------------------------------------------------------------------------
def list_storage_objects(bucket_name: str | None, prefix: str = "") -> list:
    """
    Lista objetos do Storage (delega ao service, trata UI).

    Responsabilidades:
    - Montar contexto com bucket_name e prefix
    - Delegar ao service headless
    - Reagir a erros (exibir messagebox se necessário)
    - Retornar lista de objetos para compatibilidade
    """
    # 1. MONTAR CONTEXTO
    ctx = {
        "bucket_name": bucket_name,
        "prefix": prefix,
    }

    # 2. DELEGAR AO SERVICE
    service_result = list_storage_objects_service(ctx)

    # 3. REAGIR A ERROS (UI)
    if not service_result["ok"]:
        error_type = service_result.get("error_type")
        if error_type == "bucket_not_found":
            messagebox.showerror(
                "Erro ao listar arquivos",
                "Não foi possível acessar o bucket de arquivos. Verifique a configuração de storage e tente novamente.",
            )
        # Para outros erros, apenas log (já feito pelo service)

    # 4. RETORNAR LISTA DE OBJETOS (compatibilidade)
    return service_result.get("objects", [])


def download_file(bucket_name: str | None, file_path: str, local_path: str | None = None):
    """
    Faz download de arquivo do Storage (delega ao service).

    Responsabilidades:
    - Detectar chamada compacta download_file(remote, local)
    - Montar contexto
    - Delegar ao service headless

    Nota: Esta função não mostra UI (apenas logs), pois é usada
    por outros módulos que tratam erros de forma específica.
    """
    # 1. DETECTAR CHAMADA COMPACTA
    compact_call = local_path is None

    # 2. MONTAR CONTEXTO
    ctx = {
        "bucket_name": bucket_name,
        "file_path": file_path,
        "local_path": local_path,
        "compact_call": compact_call,
    }

    # 3. DELEGAR AO SERVICE
    download_file_service(ctx)

    # 4. SEM REAGIR A ERROS AQUI (callers tratam)
    # O service já faz log dos erros
    # Retorno implícito None (compatibilidade)


def salvar_e_upload_docs(self, row, ents: dict, arquivos_selecionados: list | None, win=None, **kwargs):
    """
    Orquestra o fluxo de salvar + upload de documentos (UI layer).

    Responsabilidades:
    - Montar o contexto com dados coletados da UI
    - Delegar a lógica de negócio ao service
    - Reagir ao resultado (UI: messageboxes, atualização de estado)
    """
    # LAZY IMPORT: quebra ciclo form_service → pipeline → client_form → actions
    from src.modules.uploads.form_service import salvar_e_upload_docs_service

    # Montar contexto para o service (sem lógica de negócio, apenas coleta de dados)
    ctx = {
        "self": self,
        "row": row,
        "ents": ents,
        "arquivos_selecionados": arquivos_selecionados,
        "win": win,
        "kwargs": dict(kwargs),
        "skip_duplicate_prompt": kwargs.get("skip_duplicate_prompt", False),
    }

    # Delegar ao service (headless, sem Tk)
    service_result = salvar_e_upload_docs_service(ctx)

    # TODO: Aqui poderíamos adicionar reações de UI baseadas em service_result
    # Por enquanto, mantemos compatibilidade total com o comportamento original
    # (o pipeline já mostra messageboxes internamente)

    return service_result.get("result")


def __getattr__(name: str):
    if name == "SubpastaDialog":
        from src.modules.clientes.forms import SubpastaDialog as _subpasta_dialog

        return _subpasta_dialog
    raise AttributeError(f"module {__name__} has no attribute {name!r}")
