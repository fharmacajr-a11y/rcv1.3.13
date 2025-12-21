"""Constantes do módulo ANVISA.

Centraliza tipos de demandas, status e aliases para evitar duplicação.
"""

from __future__ import annotations

# Tipos de demandas ANVISA
REQUEST_TYPES = [
    "Alteração do Responsável Legal",
    "Alteração do Responsável Técnico",
    "Alteração da Razão Social",
    "Associação ao SNGPC",
    "Alteração de Porte",
    "Cancelamento de AFE",
]

# Status permitidos pelo CHECK constraint do banco de dados
STATUS_OPEN = {"draft", "submitted", "in_progress"}
STATUS_CLOSED = {"done", "canceled"}
STATUS_ALL = STATUS_OPEN | STATUS_CLOSED

# Status padrão para finalizar demanda
DEFAULT_CLOSE_STATUS = "done"

# Aliases para normalizar status legíveis → status do banco
STATUS_ALIASES = {
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
DEFAULT_CREATE_STATUS = "draft"

# Status padrão ao finalizar uma demanda
DEFAULT_CLOSE_STATUS = "done"
