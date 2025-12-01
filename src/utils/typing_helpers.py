"""Helpers de TypeGuard para checagem de tipo em runtime.

As funcoes abaixo ajudam a estreitar tipos Unknown/Any para tipos concretos
aproveitando o suporte de Pyright/Pylance ao TypeGuard (PEP 647).
"""

from __future__ import annotations

from typing import Any, Iterable, TypeGuard, cast


def is_str(value: Any) -> TypeGuard[str]:
    """Retorna True se o valor for exatamente str (TypeGuard para estreitar o tipo)."""
    return isinstance(value, str)


def is_non_empty_str(value: Any) -> TypeGuard[str]:
    """Retorna True apenas para strings com conteudo nao vazio (desconsidera espacos)."""
    return isinstance(value, str) and bool(value.strip())


def is_str_dict(value: Any) -> TypeGuard[dict[str, str]]:
    """Confere se o valor eh um dict[str, str] (todas as chaves e valores sao str)."""
    if not isinstance(value, dict):
        return False

    for k_raw, v_raw in value.items():  # type: ignore[reportUnknownVariableType]
        k = cast(Any, k_raw)
        v = cast(Any, v_raw)
        if not isinstance(k, str) or not isinstance(v, str):
            return False

    return True


def is_str_iterable(value: Any) -> TypeGuard[Iterable[str]]:
    """Valida se o valor e um iteravel de strings; pode consumir o iteravel ao checar."""
    try:
        # Try to iterate (avoid consuming generators by converting to list)
        items = list(value) if not isinstance(value, (list, tuple)) else value  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False

    for item_raw in items:  # type: ignore[reportUnknownVariableType]
        item = cast(Any, item_raw)
        if not isinstance(item, str):
            return False

    return True


def is_optional_str(value: Any) -> TypeGuard[str | None]:
    """Retorna True para str ou None (TypeGuard de opcional)."""
    return value is None or isinstance(value, str)


__all__ = [
    "is_str",
    "is_non_empty_str",
    "is_str_dict",
    "is_str_iterable",
    "is_optional_str",
]
