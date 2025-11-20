"""Helpers de status compartilhados entre view e viewmodel da Auditoria."""

from __future__ import annotations

from src.modules.auditoria import viewmodel as vm

DEFAULT_AUDITORIA_STATUS = vm.DEFAULT_AUDITORIA_STATUS
STATUS_LABELS = vm.STATUS_LABELS
canonical_status = vm.canonical_status
status_to_label = vm.status_to_label

# valores aceitos no BD (ajuste se sua tabela tiver outros)
STATUS_OPEN = {"em_andamento", "pendente", "em_processo"}
STATUS_MENU_ITEMS = tuple(STATUS_LABELS.keys())
STATUS_OPEN_CANONICAL = {canonical_status(status) for status in STATUS_OPEN}


def label_to_status(label: str | None) -> str:
    """Converte um rótulo exibido em tela de volta para o valor salvo no banco."""
    if not label:
        return canonical_status("")
    lowered = label.strip().lower()
    for key, friendly in STATUS_LABELS.items():
        if friendly.lower() == lowered:
            return key
    raw = lowered.replace(" ", "_")
    return canonical_status(raw)


def is_status_open(value: str | None) -> bool:
    """Retorna True se o status estiver entre os considerados 'abertos'."""
    return canonical_status(value) in STATUS_OPEN_CANONICAL
