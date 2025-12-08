# -*- coding: utf-8 -*-
"""Normalização canônica de texto (remoção de acentos/diacríticos).

Este módulo centraliza todas as operações de normalização de texto,
especialmente remoção de acentos e conversão para ASCII.

**Implementações canônicas** para o projeto RC - Gestor de Clientes.
Todas as outras funções de normalização devem delegar para estas.
"""

from __future__ import annotations

import unicodedata as _ud

__all__ = [
    "strip_diacritics",
    "normalize_ascii",
]


def strip_diacritics(value: str | None) -> str:
    """Remove acentos/diacríticos de uma string usando normalização Unicode NFD.

    **Implementação canônica** de remoção de diacríticos no projeto.
    Todas as outras funções _strip_diacritics devem delegar para esta.

    Estratégia:
    - Usa normalização Unicode NFD (Canonical Decomposition)
    - Remove caracteres combinantes (categoria Mn - Nonspacing Mark)
    - Recompõe usando NFC (Canonical Composition) para forma canônica

    Regras:
    - None → "" (string vazia)
    - "" → ""
    - Remove apenas diacríticos, preserva estrutura base
    - Mantém espaços, pontuação e outros caracteres

    Args:
        value: String para processar, ou None

    Returns:
        String sem diacríticos, ou string vazia se None

    Examples:
        >>> strip_diacritics("Olá, João!")
        'Ola, Joao!'
        >>> strip_diacritics("AÇÃO")
        'ACAO'
        >>> strip_diacritics("çãõü")
        'caou'
        >>> strip_diacritics(None)
        ''
        >>> strip_diacritics("")
        ''
    """
    if value is None:
        return ""

    text = str(value)
    # NFD: Canonical Decomposition (separa base + diacrítico)
    decomposed = _ud.normalize("NFD", text)
    # Remove caracteres combinantes (Mn = Nonspacing Mark)
    without_marks = "".join(ch for ch in decomposed if _ud.category(ch) != "Mn")
    # NFC: Canonical Composition (recompõe forma canônica)
    return _ud.normalize("NFC", without_marks)


def normalize_ascii(value: str | None) -> str:
    """Converte string para versão ASCII pura, removendo caracteres não-ASCII.

    **Implementação canônica** de normalização ASCII no projeto.

    Estratégia:
    - Primeiro remove diacríticos usando strip_diacritics()
    - Depois converte para ASCII, ignorando caracteres não convertíveis
    - Útil para comparações, chaves de storage, URLs, etc.

    Regras:
    - None → ""
    - "" → ""
    - Remove acentos primeiro
    - Remove emojis, símbolos e caracteres não-ASCII
    - Mantém apenas caracteres ASCII (0x00-0x7F)

    Args:
        value: String para processar, ou None

    Returns:
        String ASCII pura, ou string vazia se None

    Examples:
        >>> normalize_ascii("Olá, João!")
        'Ola, Joao!'
        >>> normalize_ascii("çãõü")
        'caou'
        >>> normalize_ascii("Hello 👋")
        'Hello '
        >>> normalize_ascii(None)
        ''
        >>> normalize_ascii("")
        ''
    """
    if value is None:
        return ""

    # Remove diacríticos primeiro
    stripped = strip_diacritics(value)
    # Converte para ASCII, ignorando caracteres não convertíveis
    return stripped.encode("ascii", errors="ignore").decode("ascii")
