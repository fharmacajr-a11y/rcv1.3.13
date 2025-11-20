# -*- coding: utf-8 -*-
"""INTERNAL: implementação particionada do pipeline de clientes; API pública exposta por pipeline.py."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any, Dict, Optional, Tuple

from src.core.logger import get_logger

from ._prepare import UploadCtx, _unpack_call

LOGGER_NAME = "src.modules.clientes.forms.pipeline"
logger = get_logger(LOGGER_NAME)


def _cleanup_ctx(self) -> None:
    if hasattr(self, "_upload_ctx"):
        delattr(self, "_upload_ctx")


def finalize_state(*args, ctx_override: Optional[UploadCtx] = None, **kwargs) -> Tuple[tuple, Dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx = ctx_override or getattr(self, "_upload_ctx", None)
    if not ctx:
        return args, kwargs
    if ctx.abort and not ctx.finalize_ready:
        _cleanup_ctx(self)
        return args, kwargs
    if not ctx.finalize_ready:
        return args, kwargs

    try:
        if ctx.busy_dialog:
            ctx.busy_dialog.close()
    except Exception:
        pass

    prefix_info = ""
    if ctx.misc.get("storage_prefix"):
        prefix_info = f"\n\nPrefixo no Storage: {ctx.misc['storage_prefix']}"

    arquivos_falhados = ctx.misc.get("arquivos_falhados", [])
    falhas_info = ""
    if arquivos_falhados:
        lista = arquivos_falhados[:10]
        falhas_info = "\n\nArquivos que falharam:\n- " + "\n- ".join(lista)
        if len(arquivos_falhados) > 10:
            falhas_info += f"\n... e mais {len(arquivos_falhados) - 10} arquivo(s)"
        logger.warning("Arquivos que falharam no upload: %s", ", ".join(arquivos_falhados))

    msg = (
        f"Cliente salvo e documentos enviados com sucesso!{prefix_info}"
        if ctx.falhas == 0
        else f"Cliente salvo com {ctx.falhas} falha(s) no envio de arquivos.{falhas_info}{prefix_info}"
    )

    try:
        if ctx.parent_win is not None:
            messagebox.showinfo("Sucesso", msg, parent=ctx.parent_win)
        else:
            messagebox.showinfo("Sucesso", msg)
    except Exception:
        pass

    try:
        if ctx.win and hasattr(ctx.win, "destroy"):
            ctx.win.destroy()
    except Exception:
        pass

    try:
        self.carregar()
    except Exception:
        pass

    _cleanup_ctx(self)
    return args, kwargs


__all__ = ["finalize_state"]
