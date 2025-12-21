"""Utilitários de tratamento de erros para o módulo ANVISA.

Fornece helpers para extrair informações de erros PostgREST/Supabase e
gerar mensagens amigáveis para o usuário.
"""

import logging
from typing import Any


def extract_postgrest_error(exc: Exception) -> dict[str, Any]:
    """Extrai informações estruturadas de um erro PostgREST/Supabase.

    Args:
        exc: Exceção a processar.

    Returns:
        Dicionário com:
        - code: Código SQLSTATE (ex: "23514")
        - message: Mensagem do erro
        - details: Detalhes adicionais
        - hint: Dica para resolver o problema

    Examples:
        >>> exc = APIError({"code": "23514", "message": "Check constraint"})
        >>> extract_postgrest_error(exc)
        {'code': '23514', 'message': 'Check constraint', 'details': None, 'hint': None}
    """
    error_dict: dict[str, Any] = {
        "code": None,
        "message": str(exc),
        "details": None,
        "hint": None,
    }

    # Tenta extrair de postgrest.exceptions.APIError
    if hasattr(exc, "code"):
        error_dict["code"] = getattr(exc, "code", None)
    if hasattr(exc, "message"):
        error_dict["message"] = getattr(exc, "message", None)
    if hasattr(exc, "details"):
        error_dict["details"] = getattr(exc, "details", None)
    if hasattr(exc, "hint"):
        error_dict["hint"] = getattr(exc, "hint", None)

    # Tenta extrair de dict (se for um erro com payload JSON)
    if hasattr(exc, "args") and exc.args and isinstance(exc.args[0], dict):
        payload = exc.args[0]
        error_dict["code"] = payload.get("code", error_dict["code"])
        error_dict["message"] = payload.get("message", error_dict["message"])
        error_dict["details"] = payload.get("details", error_dict["details"])
        error_dict["hint"] = payload.get("hint", error_dict["hint"])

    return error_dict


def user_message_from_error(
    err: dict[str, Any],
    *,
    default: str = "Erro ao processar operação. Verifique os logs para mais detalhes.",
) -> str:
    """Gera mensagem amigável para o usuário baseada no erro.

    Args:
        err: Dicionário de erro (resultado de extract_postgrest_error).
        default: Mensagem padrão se não houver mapeamento específico.

    Returns:
        Mensagem amigável para exibir ao usuário.

    Examples:
        >>> user_message_from_error({"code": "23514"})
        'Dados inválidos para o status/tipo. Verifique a configuração e tente novamente.'

        >>> user_message_from_error({"code": "42501"})
        'Sem permissão para executar esta ação.'
    """
    code = err.get("code")
    message = err.get("message", "")

    # Mapeamento de SQLSTATE codes para mensagens amigáveis
    error_messages = {
        # Constraint violations
        "23514": "Dados inválidos para o status/tipo. Verifique a configuração e tente novamente.",
        "23503": "Referência inválida (cliente ou organização não encontrados).",
        "23505": "Esta operação geraria uma duplicação de registro.",
        # Permissions
        "42501": "Sem permissão para executar esta ação.",
        # Not found
        "PGRST116": "Registro não encontrado.",
        # Network/connection
        "08000": "Erro de conexão com o banco de dados.",
        "08006": "Conexão perdida com o banco de dados.",
    }

    # Tenta encontrar mensagem específica por código
    if code and code in error_messages:
        user_msg = error_messages[code]

        # Adiciona detalhe se disponível (mas mantém mensagem curta)
        if message and len(message) < 100:
            user_msg += f"\n\nDetalhes: {message}"

        return user_msg

    # Fallback: usa mensagem padrão
    result = default
    if message and len(message) < 150:
        result += f"\n\nDetalhes: {message}"

    return result


def log_exception(
    log: logging.Logger,
    msg: str,
    exc: Exception,
    **ctx: Any,
) -> None:
    """Loga exceção com stacktrace completo e contexto.

    Args:
        log: Logger a usar.
        msg: Mensagem descritiva do erro.
        exc: Exceção a logar.
        **ctx: Contexto adicional (org_id, client_id, request_id, action, etc).

    Examples:
        >>> log_exception(
        ...     logger,
        ...     "Erro ao criar demanda",
        ...     exc,
        ...     org_id="org-123",
        ...     client_id=456,
        ...     action="create"
        ... )
    """
    from .anvisa_logging import fmt_ctx

    # Formata contexto
    ctx_str = fmt_ctx(**ctx)

    # Loga com stacktrace completo
    if ctx_str:
        log.exception(f"{msg} [{ctx_str}]", exc_info=exc)
    else:
        log.exception(msg, exc_info=exc)
