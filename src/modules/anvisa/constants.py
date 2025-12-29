"""Constantes do módulo ANVISA.

Centraliza tipos de demandas, status e aliases para evitar duplicação.
"""

from __future__ import annotations

from typing import Final, Literal

# Type aliases para clareza
RequestTypeStr = Literal[
    "AFE ANVISA",
    "Alteração da Razão Social",
    "Alteração de Endereço",
    "Alteração de Nome Fantasia",
    "Alteração de Porte",
    "Alteração do Responsável Legal",
    "Alteração do Responsável Técnico",
    "Ampliação de Atividades",
    "Associação ao SNGPC",
    "Cancelamento de AFE",
    "Concessão de AE Manipulação",
    "Concessão de AFE (Inicial)",
    "Importação de Cannabidiol",
    "Redução de Atividades",
]

StatusOpen = Literal["draft", "submitted", "in_progress"]
StatusClosed = Literal["done", "canceled"]
StatusType = Literal["draft", "submitted", "in_progress", "done", "canceled"]

# Tipos de demandas ANVISA (imutável)
REQUEST_TYPES: Final[tuple[RequestTypeStr, ...]] = (
    "AFE ANVISA",
    "Alteração da Razão Social",
    "Alteração de Endereço",
    "Alteração de Nome Fantasia",
    "Alteração de Porte",
    "Alteração do Responsável Legal",
    "Alteração do Responsável Técnico",
    "Ampliação de Atividades",
    "Associação ao SNGPC",
    "Cancelamento de AFE",
    "Concessão de AE Manipulação",
    "Concessão de AFE (Inicial)",
    "Importação de Cannabidiol",
    "Redução de Atividades",
)

# Status permitidos pelo CHECK constraint do banco de dados
STATUS_OPEN: Final[frozenset[StatusOpen]] = frozenset({"draft", "submitted", "in_progress"})
STATUS_CLOSED: Final[frozenset[StatusClosed]] = frozenset({"done", "canceled"})
STATUS_ALL: Final[frozenset[StatusType]] = STATUS_OPEN | STATUS_CLOSED

# Status padrão para finalizar demanda
DEFAULT_CLOSE_STATUS: Final[StatusClosed] = "done"

# Aliases para normalizar status legíveis → status do banco
STATUS_ALIASES: Final[dict[str, StatusType]] = {
    # Status finalizados
    "finalizada": "done",
    "finalizado": "done",
    "fechada": "done",
    "concluida": "done",
    "concluída": "done",
    "cancelada": "canceled",
    "canceled": "canceled",
    # Status abertos
    "aberta": "draft",  # Status legado comum em testes
    "rascunho": "draft",
    "enviada": "submitted",
    "em_andamento": "in_progress",
    "em andamento": "in_progress",
    # Status já normalizados (retornam a si mesmos)
    "done": "done",
    "draft": "draft",
    "submitted": "submitted",
    "in_progress": "in_progress",
}

# Status padrão ao criar uma nova demanda
DEFAULT_CREATE_STATUS: Final[StatusOpen] = "draft"
