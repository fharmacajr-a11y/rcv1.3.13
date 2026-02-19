# -*- coding: utf-8 -*-
"""Contratos de colunas de banco de dados (schemas).

Este módulo centraliza as definições de colunas usadas em queries SELECT
para prevenir schema drift e erros 42703 (undefined_column).

REGRAS:
- SEMPRE use *_SELECT_FIELDS como default em queries normais
- SEMPRE use *_SELECT_FIELDS_SAFE em fallbacks/retry de erro 42703
- NUNCA hardcode strings de colunas diretamente no código

REFERÊNCIAS:
- Erro 42703: https://www.postgresql.org/docs/current/errcodes-appendix.html
- Supabase/PostgREST select: https://postgrest.org/en/stable/api.html#horizontal-filtering-columns
"""

from __future__ import annotations

# ==============================================================================
# RC_NOTES - Tabela de notas compartilhadas (Hub)
# ==============================================================================

# Campos completos (usado normalmente)
RC_NOTES_SELECT_FIELDS = "id,org_id,author_email,body,created_at,is_done"

# Campos seguros (usado em fallback quando schema drift é detectado)
# Remove is_done para máxima compatibilidade
RC_NOTES_SELECT_FIELDS_SAFE = "id,org_id,author_email,body,created_at"

# Campos mínimos para listagem simples
RC_NOTES_SELECT_FIELDS_LIST = "id,author_email,body,created_at"

# ==============================================================================
# ORG_NOTIFICATIONS - Tabela de notificações da organização
# ==============================================================================

# Campos completos (usado normalmente)
ORG_NOTIFICATIONS_SELECT_FIELDS = (
    "id,org_id,module,event,message,actor_email,actor_user_id,request_id,client_id,is_read,created_at"
)

# Campos seguros (usado em fallback)
# Remove actor_user_id, request_id, client_id para máxima compatibilidade
ORG_NOTIFICATIONS_SELECT_FIELDS_SAFE = "id,org_id,module,event,message,actor_email,is_read,created_at"

# Campos para listagem (UI)
ORG_NOTIFICATIONS_SELECT_FIELDS_LIST = "id,created_at,message,is_read,module,event,client_id,request_id,actor_email"

# Campos mínimos para count
ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT = "id"

# ==============================================================================
# CLIENTS - Tabela de clientes
# ==============================================================================
# IMPORTANTE: db_manager.py define CLIENT_COLUMNS =
# "id,numero,nome,razao_social,cnpj,cnpj_norm,ultima_alteracao,ultima_por,obs,org_id,deleted_at"
# Mantemos compatibilidade com esse schema (campos mais simples)

# Campos usados no db_manager.py (padrão atual do sistema)
CLIENTS_SELECT_FIELDS = "id,numero,nome,razao_social,cnpj,cnpj_norm,ultima_alteracao,ultima_por,obs,org_id,deleted_at"

# Campos seguros (mínimo garantido)
CLIENTS_SELECT_FIELDS_SAFE = "id,numero,nome,razao_social,cnpj,org_id"

# Campos para count
CLIENTS_SELECT_FIELDS_COUNT = "id"

# Alias para compatibilidade com db_manager.py
CLIENT_COLUMNS = CLIENTS_SELECT_FIELDS

# ==============================================================================
# MEMBERSHIPS - Tabela de membros/usuários da organização
# ==============================================================================

MEMBERSHIPS_SELECT_FIELDS = "user_id,org_id,role,created_at"
MEMBERSHIPS_SELECT_FIELDS_SAFE = "user_id,org_id"

# Variantes específicas (usadas em queries específicas)
MEMBERSHIPS_SELECT_ORG_ID = "org_id"
MEMBERSHIPS_SELECT_ROLE = "role"
MEMBERSHIPS_SELECT_ORG_ROLE = "org_id, role"  # Nota: espaço após vírgula (como no código atual)

# ==============================================================================
# HELPERS
# ==============================================================================


def select_fields(*cols: str) -> str:
    """Helper para construir string de colunas para .select().

    Args:
        *cols: Nomes das colunas

    Returns:
        String com colunas separadas por vírgula

    Example:
        >>> select_fields("id", "name", "email")
        'id,name,email'
    """
    return ",".join(cols)


def is_schema_drift_error(exception: Exception) -> bool:
    """Detecta se exceção é erro 42703 (coluna indefinida).

    Args:
        exception: Exceção capturada

    Returns:
        True se for erro de schema drift (42703)

    Example:
        >>> try:
        ...     query.select("nonexistent_column")
        ... except Exception as e:
        ...     if is_schema_drift_error(e):
        ...         # Retry com campos SAFE
        ...         query.select(RC_NOTES_SELECT_FIELDS_SAFE)
    """
    from postgrest.exceptions import APIError

    if not isinstance(exception, APIError):
        return False

    error_str = str(exception)
    return "42703" in error_str or "undefined_column" in error_str.lower()
