# -*- coding: utf-8 -*-
"""
DEPRECATED (UP-05): Pipeline helpers legados para salvar_e_upload_docs.

Mantido apenas para compatibilidade com testes legacy.
Novos fluxos devem usar:
- src.modules.uploads.service (upload_items_for_client)
- src.modules.uploads.views.upload_dialog (UploadDialog)
"""

from __future__ import annotations

from ._finalize import finalize_state as _finalize_state
from ._prepare import (
    prepare_payload as _prepare_payload,
    traduzir_erro_supabase_para_msg_amigavel,
    validate_inputs as _validate_inputs,
)


def validate_inputs(*args, **kwargs):
    return _validate_inputs(*args, **kwargs)


def prepare_payload(*args, **kwargs):
    return _prepare_payload(*args, **kwargs)


def perform_uploads(*args, **kwargs):
    """
    DEPRECATED (UP-05): Removido junto com _upload.py.

    Use src.modules.uploads.service.upload_items_for_client em vez disso.
    """
    raise NotImplementedError(
        "perform_uploads foi removido (UP-05). " "Use src.modules.uploads.service.upload_items_for_client"
    )


def finalize_state(*args, **kwargs):
    return _finalize_state(*args, **kwargs)


__all__ = [
    "traduzir_erro_supabase_para_msg_amigavel",
    "validate_inputs",
    "prepare_payload",
    "perform_uploads",
    "finalize_state",
]
