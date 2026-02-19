# -*- coding: utf-8 -*-
"""Gerenciamento de cache de nomes de autores para HubScreen.

Extrai lógica complexa de carregamento assíncrono de nomes de autores
(profiles.display_name) e sincronização de cache.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from src.modules.hub.async_runner import HubAsyncRunner

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)

# Cooldown para refresh de nomes (evitar chamadas duplicadas)
NAMES_REFRESH_COOLDOWN_S = 30


def should_skip_refresh_by_cooldown(
    last_refresh: Optional[float],
    cooldown_seconds: float,
    force: bool,
) -> bool:
    """Verifica se deve pular refresh baseado em cooldown.

    Args:
        last_refresh: Timestamp do último refresh (ou None)
        cooldown_seconds: Tempo de cooldown em segundos
        force: Se True, ignora cooldown

    Returns:
        True se deve pular refresh, False caso contrário
    """
    if force:
        return False

    if last_refresh is None:
        return False

    elapsed = time.time() - last_refresh
    return elapsed < cooldown_seconds


def refresh_author_names_cache(
    org_id: str,
    async_runner: HubAsyncRunner,
    _current_cache: dict[str, str],  # noqa: ARG001 (usado apenas para referência, atualizado via callback)
    _current_prefix_map: dict[str, str],  # noqa: ARG001 (usado apenas para referência, atualizado via callback)
    last_refresh: Optional[float],
    last_org_id: Optional[str],
    is_refreshing: bool,
    force: bool,
    on_cache_updated: Callable[[dict[str, str], dict[str, str], str], None],
    on_start_refresh: Callable[[], None],
    on_end_refresh: Callable[[], None],
) -> bool:
    """Atualiza cache de nomes de autores de forma assíncrona.

    Args:
        org_id: ID da organização atual
        async_runner: Runner para operações assíncronas
        current_cache: Cache atual de nomes
        current_prefix_map: Mapa atual de prefixos de email
        last_refresh: Timestamp do último refresh
        last_org_id: ID da última organização carregada
        is_refreshing: Flag indicando se já está em processo de refresh
        force: Se True, ignora cooldown e força atualização
        on_cache_updated: Callback chamado quando cache é atualizado
        on_start_refresh: Callback chamado quando refresh inicia
        on_end_refresh: Callback chamado quando refresh termina

    Returns:
        True se refresh foi iniciado, False se foi pulado
    """
    # Evitar reentrância (exceto se force=True)
    if is_refreshing and not force:
        return False

    # Cooldown de 30 segundos (exceto se force=True)
    if should_skip_refresh_by_cooldown(
        last_refresh=last_refresh,
        cooldown_seconds=NAMES_REFRESH_COOLDOWN_S,
        force=force,
    ):
        return False

    # Se organização mudou, invalidar cache
    if last_org_id and last_org_id != org_id:
        logger.info("Cache de nomes invalidado (mudança de organização)")

    # Sinalizar início do refresh
    on_start_refresh()

    # Definir função de carregamento (background)
    def load_names() -> tuple[dict[str, str], dict[str, str]]:
        """Carrega nomes de autores e mapa de prefixos."""
        try:
            from src.core.services.profiles_service import (
                get_display_names_map,
                get_email_prefix_map,
            )

            mapping = get_display_names_map(org_id)
            prefix_map = get_email_prefix_map(org_id)
            return (mapping or {}, prefix_map or {})
        except Exception as e:
            logger.debug("Erro ao carregar nomes de autores: %s", e)
            return ({}, {})

    # Callbacks de sucesso/erro
    def on_success(result: tuple[dict[str, str], dict[str, str]]) -> None:
        """Atualiza cache de nomes com resultado."""
        mapping, prefix_map = result

        # Calcular hash do novo cache
        cache_json = json.dumps(mapping, sort_keys=True, ensure_ascii=False)
        new_hash = hashlib.sha256(cache_json.encode("utf-8")).hexdigest()

        logger.debug(
            "Cache de nomes carregado: %d entradas",
            len(mapping),
        )
        logger.debug(
            "Mapa de prefixos carregado: %d entradas",
            len(prefix_map),
        )

        # Notificar atualização
        on_cache_updated(mapping, prefix_map, new_hash)
        on_end_refresh()

    def on_error(exc: Exception) -> None:
        """Trata erro no carregamento de nomes."""
        logger.debug("Erro ao carregar nomes de autores: %s", exc)
        on_end_refresh()

    # Executar via HubAsyncRunner
    async_runner.run(
        func=load_names,
        on_success=on_success,
        on_error=on_error,
    )

    return True


def calculate_cache_hash(cache: dict[str, str]) -> str:
    """Calcula hash SHA256 do cache de nomes.

    Args:
        cache: Dicionário de nomes de autores

    Returns:
        Hash SHA256 em hexadecimal
    """
    cache_json = json.dumps(cache, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(cache_json.encode("utf-8")).hexdigest()
