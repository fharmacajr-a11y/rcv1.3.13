# -*- coding: utf-8 -*-
"""
shared/subfolders.py

Camada centralizada para lógica de subpastas/subfolders no Storage.
Unifica sanitização, sugestão de nomes e listagem de subpastas.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.core.text_normalization import strip_diacritics as _strip_diacritics
from src.utils.subpastas_config import get_mandatory_subpastas, join_prefix

logger = logging.getLogger(__name__)

# Padrão de sanitização: mantém apenas letras, números, hífen e underscore
_SANITIZE_PATTERN = re.compile(r"[^\w\-]+")


def sanitize_subfolder_name(raw: str | None) -> str:
    """
    Sanitiza nome de subpasta removendo caracteres inválidos.

    Args:
        raw: Nome bruto da subpasta

    Returns:
        Nome sanitizado (apenas letras, números, hífen, underscore, sem acentos)
    """
    if not raw:
        return ""
    # Remove diacríticos primeiro
    s = _strip_diacritics(str(raw).strip())
    # Remove caracteres especiais
    clean = _SANITIZE_PATTERN.sub("", s)
    return clean


def suggest_client_subfolder(org_id: str, client_id: int, default: str = "GERAL") -> str:
    """
    Sugere nome de subpasta para cliente.

    Args:
        org_id: ID da organização
        client_id: ID do cliente
        default: Nome padrão se não houver sugestão específica

    Returns:
        Nome de subpasta sugerido (sanitizado)
    """
    # Por enquanto retorna o default, mas pode ser expandido com lógica de negócio
    # (ex.: verificar tipo de cliente, tags, etc.)
    return sanitize_subfolder_name(default) or "GERAL"


def list_storage_subfolders(
    storage_client: Any,
    prefix: str,
    bucket: str = "rc-docs",
) -> list[str]:
    """
    Lista subpastas existentes no Storage a partir de um prefixo.

    Args:
        storage_client: Cliente Supabase Storage
        prefix: Prefixo base (ex.: "org123/client456/")
        bucket: Nome do bucket (default: rc-docs)

    Returns:
        Lista de nomes de subpastas encontradas
    """
    try:
        # Garante que prefix termina com /
        prefix_normalized = prefix.rstrip("/") + "/" if prefix else ""

        result = storage_client.list(bucket, path=prefix_normalized)
        if not result:
            return []

        # Extrai nomes de pastas (objetos que terminam com /)
        folders = []
        for item in result:
            name = item.get("name", "")
            if name and name.endswith("/"):
                # Remove prefix e barra final
                folder_name = name[len(prefix_normalized) :].rstrip("/")
                if folder_name:
                    folders.append(folder_name)

        return sorted(set(folders))

    except Exception as exc:
        logger.exception("Erro ao listar subpastas do Storage: %s", exc)
        return []


def get_mandatory_subfolder_names() -> tuple[str, ...]:
    """
    Retorna tuple de nomes de subpastas obrigatórias.

    Returns:
        Tuple com nomes de subpastas obrigatórias
    """
    return get_mandatory_subpastas()


def build_storage_path(org_id: str, client_id: int, subfolder: str = "") -> str:
    """
    Constrói path completo para Storage.

    Args:
        org_id: ID da organização
        client_id: ID do cliente
        subfolder: Nome da subpasta (opcional)

    Returns:
        Path formatado (ex.: "org123/client456/GERAL/")
    """
    base = f"{org_id}/client{client_id}"
    if subfolder:
        clean_subfolder = sanitize_subfolder_name(subfolder)
        return join_prefix(base, clean_subfolder)
    return join_prefix(base)
