# -*- coding: utf-8 -*-
"""
Service layer para fluxo de salvar + upload de documentos.

Este módulo centraliza a lógica de negócio (não-UI) do fluxo de upload,
delegando para o pipeline existente (validate_inputs, prepare_payload,
perform_uploads, finalize_state).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.modules.clientes.forms.pipeline import (
    finalize_state,
    perform_uploads,
    prepare_payload,
    validate_inputs,
)

log = logging.getLogger(__name__)


def salvar_e_upload_docs_service(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executa o fluxo completo de salvar + upload de documentos para um cliente.

    Este service é a camada de lógica de negócio (headless, sem Tk) que:
    1. Valida os inputs
    2. Prepara o payload
    3. Executa os uploads
    4. Finaliza o estado

    Parâmetros:
        ctx: dicionário com todos os dados necessários:
            - self: instância do form (para acessar state interno se necessário)
            - row: dados da linha selecionada
            - ents: dicionário com widgets/dados do formulário
            - arquivos_selecionados: lista de arquivos para upload
            - win: referência à janela (para contexto, se necessário)
            - kwargs adicionais do pipeline

    Retorna:
        dict com resultado do processamento:
            {
                "ok": True/False,
                "result": valor retornado por _salvar_e_upload_docs_impl,
                "errors": lista de erros (se houver),
                "message": mensagem descritiva
            }
    """
    try:
        # Extrair parâmetros do contexto
        self_ref = ctx.get("self")
        row = ctx.get("row")
        ents = ctx.get("ents", {})
        arquivos_selecionados = ctx.get("arquivos_selecionados")
        win = ctx.get("win")
        pipeline_kwargs = ctx.get("kwargs", {})

        # Montar args para o pipeline (mesma ordem que actions.py usa)
        args = (self_ref, row, ents, arquivos_selecionados, win)

        # 1. Validação de inputs
        log.debug("Service: executando validate_inputs")
        args, pipeline_kwargs = validate_inputs(*args, **pipeline_kwargs)

        # 2. Preparação do payload
        skip_duplicate_prompt = pipeline_kwargs.pop("skip_duplicate_prompt", ctx.get("skip_duplicate_prompt", False))
        log.debug("Service: executando prepare_payload (skip_duplicate_prompt=%s)", skip_duplicate_prompt)
        args, pipeline_kwargs = prepare_payload(*args, skip_duplicate_prompt=skip_duplicate_prompt, **pipeline_kwargs)

        # 3. Implementação do salvar (lógica original de _salvar_e_upload_docs_impl)
        # Por enquanto, mantemos a mesma estrutura mínima:
        log.debug("Service: executando lógica de _salvar_e_upload_docs_impl")
        result = _execute_impl_logic(*args, **pipeline_kwargs)

        # 4. Executar uploads
        log.debug("Service: executando perform_uploads")
        perform_uploads(*args, **pipeline_kwargs)

        # 5. Finalizar estado
        log.debug("Service: executando finalize_state")
        finalize_state(*args, **pipeline_kwargs)

        return {"ok": True, "result": result, "errors": [], "message": "Upload concluído com sucesso"}

    except Exception as e:
        log.error("Erro no service de upload: %s", e, exc_info=True)
        return {"ok": False, "result": None, "errors": [str(e)], "message": f"Erro durante o upload: {e}"}


def _execute_impl_logic(self, row, ents: dict, arquivos_selecionados: list | None, win=None, **kwargs) -> None:
    """
    Lógica interna de _salvar_e_upload_docs_impl.

    Por enquanto, mantemos a mesma verificação mínima que existe em actions.py.
    Esta função pode ser expandida conforme necessário nas próximas fases.
    """
    ctx = getattr(self, "_upload_ctx", None)
    if not ctx:
        log.warning("_upload_ctx não encontrado no self")
        return None

    if ctx.abort:
        log.warning("Upload abortado pelo usuário (ctx.abort=True)")
        return None

    # TODO: Aqui pode-se adicionar mais lógica de negócio conforme necessário
    return None
