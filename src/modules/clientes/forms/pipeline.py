# -*- coding: utf-8 -*-
"""Pipeline helpers reais para salvar_e_upload_docs."""

# Duplicidade (CNPJ/Razão): confirmação é responsabilidade do FORM.
# O pipeline é headless (sem messagebox); o core (salvar_cliente) valida novamente.

from __future__ import annotations

from ._finalize import finalize_state as _finalize_state
from ._prepare import (
    prepare_payload as _prepare_payload,
    traduzir_erro_supabase_para_msg_amigavel,
    validate_inputs as _validate_inputs,
)
from ._upload import perform_uploads as _perform_uploads


def validate_inputs(*args, **kwargs):
    return _validate_inputs(*args, **kwargs)


def prepare_payload(*args, **kwargs):
    return _prepare_payload(*args, **kwargs)


def perform_uploads(*args, **kwargs):
    return _perform_uploads(*args, **kwargs)


def finalize_state(*args, **kwargs):
    return _finalize_state(*args, **kwargs)


__all__ = [
    "traduzir_erro_supabase_para_msg_amigavel",
    "validate_inputs",
    "prepare_payload",
    "perform_uploads",
    "finalize_state",
]
