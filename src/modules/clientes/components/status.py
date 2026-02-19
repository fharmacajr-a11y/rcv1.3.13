# -*- coding: utf-8 -*-
"""Helpers relacionados ao prefixo de status dos clientes."""

from __future__ import annotations

from src.modules.clientes.core.constants import STATUS_PREFIX_RE


def apply_status_prefix(obs: str, status: str) -> str:
    """
    Remove o prefixo antigo de status de ``obs`` e aplica o novo no mesmo formato.
    """

    body = STATUS_PREFIX_RE.sub("", str(obs or ""), count=1).strip()
    status_clean = (status or "").strip()
    if status_clean:
        return f"[{status_clean}] {body}".strip()
    return body


__all__ = ["apply_status_prefix"]
