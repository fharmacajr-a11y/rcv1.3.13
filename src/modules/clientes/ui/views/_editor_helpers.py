# -*- coding: utf-8 -*-
"""Helpers compartilhados pelos mixins do ClientEditorDialog.

Extraído para eliminar a duplicação entre _editor_data_mixin,
_editor_actions_mixin e client_editor_dialog (3 cópias idênticas).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _safe_get(obj: Any, key: str, default: Any = "") -> Any:
    """Extrai valor de dict OU objeto (aceita ambos).

    Usado para trabalhar com objetos Cliente que podem vir como dict
    (do Supabase) ou como dataclass/model (do ORM).

    Args:
        obj: Dict ou objeto (dataclass, Cliente, etc.)
        key: Chave/atributo a buscar
        default: Valor padrão se não encontrar

    Returns:
        Valor extraído ou default
    """
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _conflict_desc(conflict: Any) -> str:
    """Gera descrição amigável de um conflito de cliente.

    Args:
        conflict: Cliente conflitante (dict ou objeto)

    Returns:
        String formatada: "ID 123 - Nome da Empresa (12.345.678/0001-90)"
    """
    if conflict is None:
        return "cliente desconhecido"

    cid = _safe_get(conflict, "id", "?")
    razao = _safe_get(conflict, "razao_social", "cliente desconhecido")
    cnpj = _safe_get(conflict, "cnpj", "")

    desc = f"ID {cid} - {razao}"
    if cnpj:
        desc += f" ({cnpj})"

    return desc
