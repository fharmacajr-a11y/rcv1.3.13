# -*- coding: utf-8 -*-
"""Core string utilities for the RC Gestor de Clientes application.

This module provides canonical implementations of commonly used string
manipulation functions to prevent duplication across the codebase.
"""

from __future__ import annotations

import re

__all__ = ["only_digits"]

# Pre-compiled regex for performance
_ONLY_DIGITS_REGEX = re.compile(r"\D")


def only_digits(s: str | None) -> str:
    """Remove all non-digit characters from a string.

    This is the canonical implementation used throughout the project for
    normalizing strings to contain only numeric characters (0-9).

    Common use cases:
    - Normalizing CNPJ/CPF (removing dots, slashes, hyphens)
    - Normalizing phone numbers (removing parentheses, spaces, dashes)
    - Extracting numeric values from formatted strings

    Args:
        s: Input string to process. Can be None for convenience.

    Returns:
        String containing only digit characters (0-9). Returns empty string
        if input is None or contains no digits.

    Examples:
        >>> only_digits("12.345.678/0001-90")
        '12345678000190'
        >>> only_digits("(11) 98765-4321")
        '11987654321'
        >>> only_digits(None)
        ''
        >>> only_digits("abc123def456")
        '123456'
    """
    return _ONLY_DIGITS_REGEX.sub("", s or "")
