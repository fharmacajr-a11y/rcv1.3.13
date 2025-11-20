"""Utilitários para classificação e tratamento de erros de storage."""

from __future__ import annotations

from typing import Literal

# Tipos de erro de storage que identificamos
StorageErrorKind = Literal["invalid_key", "rls", "exists", "other"]


def classify_storage_error(exc: Exception) -> StorageErrorKind:
    """Classifica um erro de storage em categorias conhecidas.

    Analisa a mensagem de exceção para identificar tipos comuns de erro:
    - 'invalid_key': Chave/path inválido no storage
    - 'rls': Erro de Row-Level Security (permissões)
    - 'exists': Arquivo já existe (409 Conflict)
    - 'other': Erro não classificado

    Args:
        exc: Exceção capturada durante operação de storage

    Returns:
        Categoria do erro (uma das strings do tipo StorageErrorKind)

    Examples:
        >>> try:
        ...     adapter.upload(...)
        ... except Exception as e:
        ...     kind = classify_storage_error(e)
        ...     if kind == "rls":
        ...         show_permission_error()
    """
    s = str(exc).lower()

    # Erro de chave inválida
    if "invalidkey" in s or "invalid key" in s:
        return "invalid_key"

    # Erro de permissão (Row-Level Security)
    if "row-level security" in s or "rls" in s or "42501" in s or "403" in s:
        return "rls"

    # Arquivo já existe (conflito)
    if "already exists" in s or "keyalreadyexists" in s or "409" in s:
        return "exists"

    # Erro não classificado
    return "other"
