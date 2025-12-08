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
from src.ui.components.upload_feedback import show_upload_result_message

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
    parent_widget: tk.Misc | None = None
    if isinstance(win, tk.Misc):
        parent_widget = win
    elif isinstance(self, tk.Misc):
        parent_widget = self

    try:
        service_result = salvar_e_enviar_para_supabase_service(ctx)
    except Exception as exc:  # noqa: BLE001
        log.error("UI: falha ao executar service de upload: %s", exc, exc_info=True)
        messagebox.showerror(
            "Envio",
            "Ocorreu um erro inesperado ao enviar os arquivos. Tente novamente.",
            parent=parent_widget,
        )
        return None

    show_upload_result_message(parent_widget, service_result)
    return service_result.get("result") if isinstance(service_result, dict) else None


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
    - Retornar resultado estruturado para o caller verificar sucesso/erro

    Retorna:
        dict com {"ok": bool, "errors": list, "message": str, "local_path": str | None}
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

    # 3. DELEGAR AO SERVICE E RETORNAR RESULTADO
    return download_file_service(ctx)


def salvar_e_upload_docs(self, row, ents: dict, arquivos_selecionados: list | None, win=None, **kwargs):
    """
    DEPRECATED (UP-05): Use UploadDialog em vez disso.

    Orquestra o fluxo de salvar + upload de documentos (UI layer) - LEGADO.

    Novos fluxos devem usar:
    - src.modules.uploads.views.upload_dialog.UploadDialog
    - src.modules.uploads.service.upload_items_for_client
    """
    from tkinter import messagebox

    log.warning(
        "DEPRECATED: salvar_e_upload_docs foi chamado. " "Use src.modules.uploads.views.upload_dialog.UploadDialog"
    )

    parent_widget = win if isinstance(win, tk.Misc) else (self if isinstance(self, tk.Misc) else None)

    messagebox.showerror(
        "Função Removida",
        "Este fluxo de upload foi descontinuado.\n\n" "Use o botão 'Enviar documentos' no formulário de clientes.",
        parent=parent_widget,
    )

    return None


def __getattr__(name: str):
    if name == "SubpastaDialog":
        from src.modules.clientes.forms import SubpastaDialog

        return SubpastaDialog
    raise AttributeError(f"module {__name__} has no attribute {name!r}")
