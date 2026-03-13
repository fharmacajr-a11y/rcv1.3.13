"""Helpers de status da tela principal de Clientes.

Extraidos de src.ui.main_screen para reutilizacao e testes.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

DEFAULT_STATUS_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Status gerais",
        [
            "Novo cliente",
            "Sem resposta",
            "Aguardando documento",
            "Aguardando pagamento",
            "Em cadastro",
            "Finalizado",
            "Follow-up hoje",
            "Follow-up amanhã",
        ],
    ),
    (
        "SIFAP",
        [
            "Análise da Caixa",
            "Análise do Ministério",
            "Cadastro pendente",
        ],
    ),
]
DEFAULT_STATUS_CHOICES = [label for _, values in DEFAULT_STATUS_GROUPS for label in values]


def _load_status_groups() -> list[tuple[str, list[str]]]:
    """Load grouped statuses from RC_STATUS_GROUPS or fall back to the defaults."""
    raw = (os.getenv("RC_STATUS_GROUPS") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data:
                groups: list[tuple[str, list[str]]] = []
                for key, values in data.items():
                    if not values:
                        continue
                    if not isinstance(values, (list, tuple)):
                        continue
                    items = [str(v).strip() for v in values if str(v).strip()]
                    if items:
                        groups.append((str(key), items))
                if groups:
                    return groups
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao carregar RC_STATUS_GROUPS: %s", exc)
    return list(DEFAULT_STATUS_GROUPS)


STATUS_GROUPS = _load_status_groups()
STATUS_CHOICES = [label for _, values in STATUS_GROUPS for label in values]
STATUS_PREFIX_RE = re.compile(r"^\s*\[(?P<st>[^\]]+)\]\s*")

__all__ = [
    "_load_status_groups",
    "STATUS_CHOICES",
    "STATUS_PREFIX_RE",
]
