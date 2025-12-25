# -*- coding: utf-8 -*-
"""Helper para slugificar nomes de processos ANVISA.

Converte nomes de processos em slugs válidos para uso como nomes de pastas.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final, cast

from src.modules.anvisa.constants import REQUEST_TYPES, RequestTypeStr

# Type alias
SlugStr = str  # Slug válido (lowercase, a-z0-9, underscores)


def slugify_process(process_name: str) -> SlugStr:
    """Converte nome do processo ANVISA em slug para uso como pasta.

    Args:
        process_name: Nome do processo (ex: "Alteração do Responsável Legal")

    Returns:
        Slug do processo (ex: "alteracao_responsavel_legal")

    Example:
        >>> slugify_process("Alteração do Responsável Legal")
        'alteracao_responsavel_legal'
        >>> slugify_process("Associação ao SNGPC")
        'associacao_sngpc'
    """
    # Normalizar para NFD (decompor acentos)
    normalized = unicodedata.normalize("NFD", process_name)

    # Remover marcas diacríticas (acentos)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    # Converter para minúsculas
    lowercase = without_accents.lower()

    # Substituir espaços e caracteres especiais por underscore
    slug = re.sub(r"[^a-z0-9]+", "_", lowercase)

    # Remover underscores duplicados e das extremidades
    slug = re.sub(r"_+", "_", slug).strip("_")

    return slug


# Mapeamento de processos conhecidos para slugs (cache)
# Gerado dinamicamente a partir de constants.REQUEST_TYPES
# Inclui todos os 6 tipos oficiais (incluindo "Cancelamento de AFE")
PROCESS_SLUGS: Final[dict[RequestTypeStr, SlugStr]] = {process: slugify_process(process) for process in REQUEST_TYPES}


def get_process_slug(process_name: str) -> SlugStr:
    """Obtém slug do processo, usando cache se disponível.

    Args:
        process_name: Nome do processo

    Returns:
        Slug do processo

    Example:
        >>> get_process_slug("Alteração do Responsável Legal")
        'alteracao_responsavel_legal'
    """
    # cast: process_name em runtime pode ser qualquer str, mas assumimos que é válido
    return PROCESS_SLUGS.get(cast(RequestTypeStr, process_name), slugify_process(process_name))
