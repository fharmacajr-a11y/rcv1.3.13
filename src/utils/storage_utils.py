"""Utilitários para operações de storage/bucket."""

from __future__ import annotations

import os


def get_bucket_name(explicit: str | None = None) -> str:
    """Resolve o nome do bucket de Storage a partir de variáveis de ambiente.

    Prioridade de resolução:
    1. `explicit`: Bucket explicitamente passado pelo chamador
    2. `RC_STORAGE_BUCKET_CLIENTS`: Variável de ambiente padrão (usado em Auditoria/Uploads)
    3. `SUPABASE_BUCKET`: Variável de ambiente legada (versões antigas)
    4. "rc-docs": Fallback padrão

    Args:
        explicit: Nome do bucket fornecido explicitamente (opcional)

    Returns:
        Nome do bucket a ser utilizado

    Examples:
        >>> get_bucket_name()  # Usa env vars ou fallback
        'rc-docs'
        >>> get_bucket_name("custom-bucket")
        'custom-bucket'
        >>> os.environ["RC_STORAGE_BUCKET_CLIENTS"] = "clients-bucket"
        >>> get_bucket_name()
        'clients-bucket'
    """
    candidates = [
        (explicit or "").strip(),
        (os.getenv("RC_STORAGE_BUCKET_CLIENTS") or "").strip(),
        (os.getenv("SUPABASE_BUCKET") or "").strip(),
    ]
    for bucket in candidates:
        if bucket:
            return bucket
    return "rc-docs"
