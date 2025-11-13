"""Type narrowing helpers using TypeGuard for runtime type checking.

This module provides TypeGuard-based helpers for narrowing Unknown/Any types
to specific types with runtime validation. Follows PEP 647 recommendations.

References:
- PEP 647: https://peps.python.org/pep-0647/
- typing.TypeGuard: https://docs.python.org/3/library/typing.html#typing.TypeGuard
"""

from __future__ import annotations

from typing import Any, Iterable, TypeGuard, cast


def is_str(value: Any) -> TypeGuard[str]:
    """Check if value is a str (for type narrowing).

    Args:
        value: Any value to check

    Returns:
        True if value is str, allowing Pyright to narrow the type

    Examples:
        >>> val: Any = "hello"
        >>> if is_str(val):
        ...     # val is now str in this block
        ...     print(val.upper())
        HELLO
    """
    return isinstance(value, str)


def is_non_empty_str(value: Any) -> TypeGuard[str]:
    """Check if value is a non-empty str (for type narrowing).

    Args:
        value: Any value to check

    Returns:
        True if value is a non-empty str (after stripping whitespace)

    Examples:
        >>> val: Any = "  hello  "
        >>> if is_non_empty_str(val):
        ...     # val is now str in this block
        ...     print(val.strip())
        hello
    """
    return isinstance(value, str) and bool(value.strip())


def is_str_dict(value: Any) -> TypeGuard[dict[str, str]]:
    """Check if value is a dict[str, str] (for type narrowing).

    Args:
        value: Any value to check

    Returns:
        True if value is a dict with all str keys and str values

    Examples:
        >>> val: Any = {"key": "value"}
        >>> if is_str_dict(val):
        ...     # val is now dict[str, str] in this block
        ...     print(val["key"].upper())
        VALUE
    """
    if not isinstance(value, dict):
        return False

    for k_raw, v_raw in value.items():  # type: ignore[reportUnknownVariableType]
        k = cast(Any, k_raw)
        v = cast(Any, v_raw)
        if not isinstance(k, str) or not isinstance(v, str):
            return False

    return True


def is_str_iterable(value: Any) -> TypeGuard[Iterable[str]]:
    """Check if value is an iterable of str (for type narrowing).

    Args:
        value: Any value to check

    Returns:
        True if value is an iterable with all str elements

    Examples:
        >>> val: Any = ["hello", "world"]
        >>> if is_str_iterable(val):
        ...     # val is now Iterable[str] in this block
        ...     print([s.upper() for s in val])
        ['HELLO', 'WORLD']

    Note:
        This function consumes the iterable, so it's best used with
        lists/tuples rather than generators.
    """
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
    """Check if value is str or None (for type narrowing).

    Args:
        value: Any value to check

    Returns:
        True if value is str or None

    Examples:
        >>> val: Any = None
        >>> if is_optional_str(val):
        ...     # val is now str | None in this block
        ...     print(val if val else "default")
        default
    """
    return value is None or isinstance(value, str)


__all__ = [
    "is_str",
    "is_non_empty_str",
    "is_str_dict",
    "is_str_iterable",
    "is_optional_str",
]
