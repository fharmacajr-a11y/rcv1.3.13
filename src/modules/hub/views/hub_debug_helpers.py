# -*- coding: utf-8 -*-
"""Helpers de debug e diagnóstico para HubScreen.

═══════════════════════════════════════════════════════════════════════════════
MÓDULO: hub_debug_helpers.py
CONTEXTO: HUB-SPLIT-04 + MF-36 - Centralização de debug
═══════════════════════════════════════════════════════════════════════════════

Este módulo contém helpers de debug e diagnóstico para o Hub, incluindo:
- Logger JSON estruturado (hub_dlog)
- Coleta de dados de debug (collect_notes_debug_data, collect_full_notes_debug)
- Geração de relatórios (show_debug_info)

RESPONSABILIDADES:
- Capturar estado interno do Hub para diagnóstico
- Gerar relatórios JSON de debug (atalho Ctrl+D)
- Fornecer logging estruturado para desenvolvimento

HISTÓRICO:
- HUB-SPLIT-04: Extração inicial de show_debug_info e collect_notes_debug_data
- MF-36: Adição de hub_dlog e collect_full_notes_debug (lógica pesada removida do HubScreen)
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from tkinter import messagebox
from typing import Any, Callable, Dict, Iterable, Optional

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


def hub_dlog(
    tag: str,
    *,
    enabled: bool,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Logger de debug estruturado para o HUB.

    MF-36: Extraído de HubScreen._dlog para centralizar lógica de debug logging.

    Args:
        tag: Tag principal do evento (ex.: 'render_skip_empty').
        enabled: Se False, não loga nada (controle via flag no HubScreen).
        extra: Dict opcional com dados extras (convertidos para JSON).

    Raises:
        Nenhuma exceção é levantada (falhas de logging são silenciosas).
    """
    if not enabled:
        return
    try:
        payload: Dict[str, Any] = {"t": int(time.time() * 1000), "tag": tag}
        if extra:
            payload.update(extra)
        logger.info("[HUB] %s", json.dumps(payload, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logger.debug("[HUB] Falha ao logar debug: %s", exc)


def collect_notes_debug_data(
    get_org_id: Callable[[], Optional[str]],
    notes_last_data: Any,
    notes_last_snapshot: Any,
    author_names_cache: dict[str, str],
    email_prefix_map: dict[str, str],
    notes_cache_loaded: bool,
    notes_last_refresh: Optional[float],
    polling_active: bool,
    live_sync_on: bool,
) -> dict[str, Any]:
    """Coleta informações de debug do sistema de notas.

    Args:
        get_org_id: Função para obter org_id atual
        notes_last_data: Últimos dados de notas
        notes_last_snapshot: Último snapshot de notas
        author_names_cache: Cache de nomes de autores
        email_prefix_map: Mapa de prefixos de email
        notes_cache_loaded: Flag indicando se cache foi carregado
        notes_last_refresh: Timestamp do último refresh
        polling_active: Flag de polling ativo
        live_sync_on: Flag de live sync ativo

    Returns:
        Dicionário com dados de debug
    """
    org_id = get_org_id()

    # Formatar timestamp do último refresh
    last_refresh_str = None
    if notes_last_refresh:
        try:
            last_refresh_str = datetime.fromtimestamp(notes_last_refresh).isoformat()
        except Exception:
            last_refresh_str = str(notes_last_refresh)

    return {
        "timestamp": datetime.now().isoformat(),
        "org_id": org_id,
        "state": {
            "polling_active": polling_active,
            "live_sync_on": live_sync_on,
            "cache_loaded": notes_cache_loaded,
            "last_refresh": last_refresh_str,
        },
        "cache": {
            "author_names_count": len(author_names_cache),
            "email_prefix_count": len(email_prefix_map),
            "author_names": author_names_cache,
            "email_prefixes": email_prefix_map,
        },
        "notes": {
            "last_data_count": len(notes_last_data) if isinstance(notes_last_data, list) else 0,
            "last_snapshot_count": len(notes_last_snapshot) if isinstance(notes_last_snapshot, list) else 0,
            "last_data_type": type(notes_last_data).__name__,
            "last_snapshot_type": type(notes_last_snapshot).__name__,
        },
    }


def show_debug_info(
    parent: Any,
    collect_debug_data: Callable[[], dict[str, Any]],
) -> None:
    """Gera relatório JSON de diagnóstico (atalho Ctrl+D).

    Args:
        parent: Widget pai para mensagens
        collect_debug_data: Função que coleta dados de debug
    """
    try:
        # Coleta informações de debug
        debug_data = collect_debug_data()

        # Gera nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_notes_report_{timestamp}.json"

        # Salva no diretório de trabalho
        filepath = os.path.abspath(filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(debug_data, f, ensure_ascii=False, indent=2)

        # Mostra mensagem com o caminho do arquivo
        messagebox.showinfo(
            "Relatório de Debug Gerado",
            f"Relatório salvo em:\n{filepath}",
            parent=parent,
        )

        # Imprime no console como backup
        logger.info("\n=== DEBUG NOTES REPORT ===")
        logger.info(json.dumps(debug_data, ensure_ascii=False, indent=2))
        logger.info("=== Salvo em: %s ===\n", filepath)

    except Exception as e:
        logger.error("Erro ao gerar relatório de debug: %s", e)
        messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}", parent=parent)


def collect_full_notes_debug(
    *,
    get_org_id: Callable[[], Optional[str]],
    notes_last_data: Optional[Iterable[Any]],
    notes_last_snapshot: Optional[Iterable[Any]],
    author_names_cache: Dict[str, Any],
    email_prefix_map: Dict[str, str],
    notes_cache_loaded: bool,
    notes_last_refresh: Optional[float],
    polling_active: bool,
    live_sync_on: bool,
    current_user_email: Optional[str],
    debug_resolve_author_fn: Callable[[Any, str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Coleta informações detalhadas de debug sobre notas, incluindo samples.

    MF-36: Extraído de HubScreen._collect_notes_debug para centralizar lógica de coleta.

    Esta função combina:
      - collect_notes_debug_data(...) para dados base
      - loop de samples usando debug_resolve_author(...) para análise de autores

    Args:
        get_org_id: Função para obter org_id atual
        notes_last_data: Últimos dados de notas (lista completa)
        notes_last_snapshot: Último snapshot de notas (lista de tuplas)
        author_names_cache: Cache de nomes de autores
        email_prefix_map: Mapa de prefixos de email
        notes_cache_loaded: Flag indicando se cache foi carregado
        notes_last_refresh: Timestamp do último refresh
        polling_active: Flag de polling ativo
        live_sync_on: Flag de live sync ativo
        current_user_email: Email do usuário atual (para comparação)
        debug_resolve_author_fn: Função para resolver autores (ex.: debug_resolve_author(screen, email))

    Returns:
        Dicionário com dados de debug incluindo samples de resolução de autores
    """
    # Coletar dados base
    debug_data = collect_notes_debug_data(
        get_org_id=get_org_id,
        notes_last_data=notes_last_data,
        notes_last_snapshot=notes_last_snapshot,
        author_names_cache=author_names_cache,
        email_prefix_map=email_prefix_map,
        notes_cache_loaded=notes_cache_loaded,
        notes_last_refresh=notes_last_refresh,
        polling_active=polling_active,
        live_sync_on=live_sync_on,
    )

    # Preparar lista de notas para análise
    notes = notes_last_data or notes_last_snapshot or []

    # Função auxiliar para extrair email do autor (normaliza entrada)
    def _author_of(n: Any) -> str:
        if isinstance(n, dict):
            return str(n.get("author_email") or n.get("author") or n.get("email") or "")
        if isinstance(n, (tuple, list)):
            if len(n) >= 2:  # (ts, author, body) ou (author, body)
                return str(n[1])
            if len(n) == 1:
                return str(n[0])
        return str(n)

    # Adicionar samples de resolução de autores
    debug_data["samples"] = []
    debug_data["current_user"] = current_user_email or ""

    for n in list(notes)[:20]:  # Limitar a 20 samples para evitar relatórios gigantes
        try:
            author_email = _author_of(n)
            debug_data["samples"].append(debug_resolve_author_fn(n, author_email))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao resolver autor para sample: %s", exc)
            debug_data["samples"].append({"error": str(exc), "note": str(n)[:100]})

    return debug_data
