# -*- coding: utf-8 -*-
"""
Service layer para fluxo de upload externo de documentos (seleção via diálogo).

Este módulo centraliza a lógica de negócio (não-UI) do fluxo de "salvar e enviar
para Supabase", onde o usuário seleciona PDFs externamente via diálogo de arquivos.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from infra.supabase_client import get_supabase_state, is_really_online
from uploader_supabase import (
    build_items_from_files,
    upload_files_to_supabase,
)

log = logging.getLogger(__name__)


def salvar_e_enviar_para_supabase_service(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Service headless para o fluxo de salvar e enviar documentos para o armazenamento externo.

    Este service implementa a lógica de negócio (sem Tk) para:
    1. Validar conexão online
    2. Validar seleção de arquivos
    3. Construir items de upload
    4. Extrair CNPJ do cliente
    5. Executar upload via upload_files_to_supabase

    Parâmetros:
        ctx: dicionário com todos os dados necessários:
            - self: instância do form (para acessar state/supabase)
            - row: dados da linha selecionada
            - ents: dicionário com widgets/dados do formulário
            - win: referência à janela (para contexto UI)
            - files: lista de arquivos selecionados (paths)
            - kwargs adicionais

    Retorna:
        dict com resultado do processamento:
            {
                "ok": True/False,
                "result": (ok_count, failed_count) ou None,
                "errors": lista de erros (se houver),
                "message": mensagem descritiva,
                "should_show_ui": bool (indica se a UI deve mostrar mensagens),
                "ui_message_type": "warning"|"error"|"info"|None,
                "ui_message_title": str,
                "ui_message_body": str
            }
    """
    result: Dict[str, Any] = {
        "ok": False,
        "result": None,
        "errors": [],
        "message": "",
        "should_show_ui": False,
        "ui_message_type": None,
        "ui_message_title": "",
        "ui_message_body": "",
    }

    try:
        # 1. Validação de conexão online
        if not is_really_online():
            state, description = get_supabase_state()

            result["ok"] = False
            result["should_show_ui"] = True
            result["ui_message_type"] = "warning"

            if state == "unstable":
                result["ui_message_title"] = "Conexão Instável"
                result["ui_message_body"] = f"A conexão com o Supabase está instável.\n\n{description}\n\n" "Não é possível enviar dados no momento."
            else:
                result["ui_message_title"] = "Sistema Offline"
                result["ui_message_body"] = f"Não foi possível conectar ao Supabase.\n\n{description}\n\n" "Verifique sua conexão e tente novamente."

            log.warning("Service: Envio bloqueado - Estado = %s", state.upper())
            return result

        # 2. Validar arquivos selecionados
        files = ctx.get("files", [])
        if not files:
            result["ok"] = False
            result["should_show_ui"] = True
            result["ui_message_type"] = "info"
            result["ui_message_title"] = "Envio"
            result["ui_message_body"] = "Nenhum arquivo selecionado."
            log.info("Service: Nenhum arquivo selecionado")
            return result

        # 3. Construir items de upload
        items = build_items_from_files(files)
        if not items:
            result["ok"] = False
            result["should_show_ui"] = True
            result["ui_message_type"] = "warning"
            result["ui_message_title"] = "Envio"
            result["ui_message_body"] = "Nenhum PDF valido foi selecionado."
            log.warning("Service: Nenhum PDF válido nos arquivos selecionados")
            return result

        # 4. Extrair CNPJ do cliente
        ents = ctx.get("ents", {})
        row = ctx.get("row")

        cnpj_val = ""
        try:
            widget = ents.get("CNPJ")
            if widget is not None:
                cnpj_val = widget.get().strip()
        except Exception as e:
            log.debug("Service: Erro ao obter CNPJ do widget: %s", e)
            cnpj_val = ""

        if not cnpj_val and row and len(row) >= 3:
            try:
                cnpj_val = (row[2] or "").strip()
            except Exception as e:
                log.debug("Service: Erro ao obter CNPJ da row: %s", e)
                cnpj_val = ""

        # 5. Executar upload
        self_ref = ctx.get("self")
        win = ctx.get("win")
        parent = win or self_ref

        # Validar que temos uma referência válida para o app
        if self_ref is None:
            result["ok"] = False
            result["errors"].append("Referência ao app (self) não encontrada no contexto")
            result["message"] = "Erro interno: contexto inválido"
            log.error("Service: self_ref is None no contexto")
            return result

        cliente = {"cnpj": cnpj_val}

        log.info("Service: Executando upload_files_to_supabase com %d items, CNPJ=%s", len(items), cnpj_val or "(vazio)")

        ok_count, failed_count = upload_files_to_supabase(
            self_ref,
            cliente,
            items,
            subpasta=None,
            parent=parent,
        )

        result["ok"] = True
        result["result"] = (ok_count, failed_count)
        result["message"] = f"Upload concluído: {ok_count} sucesso(s), {failed_count} falha(s)"

        log.info("Service: Upload concluído - ok=%d failed=%d", ok_count, failed_count)
        return result

    except Exception as exc:
        log.error("Service: Erro inesperado no upload externo: %s", exc, exc_info=True)
        result["ok"] = False
        result["errors"].append(str(exc))
        result["message"] = f"Erro inesperado ao enviar documentos: {exc}"
        return result
