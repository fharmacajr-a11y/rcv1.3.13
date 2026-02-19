# -*- coding: utf-8 -*-
"""Funções puras (sem UI) para o dashboard center.

ORG-005: Extraído de dashboard_center.py para reduzir complexidade.
Contém funções de formatação e transformação de dados sem dependências de tkinter.
"""

from __future__ import annotations

from datetime import date, timedelta


def format_deadline_line(deadline: dict) -> str:
    """Formata uma linha de vencimento.

    Args:
        deadline: Dict com due_date, client_name, kind, title, status.

    Returns:
        String formatada com os dados do vencimento.
    """
    due_date = deadline.get("due_date", "—")
    client_name = deadline.get("client_name", "—")
    kind = deadline.get("kind", "—")
    title = deadline.get("title", "—")
    status = deadline.get("status", "—")

    return f"{due_date} – {client_name} – {kind} – {title} – {status}"


def format_task_line(task: dict) -> str:
    """Formata uma linha de tarefa pendente.

    Args:
        task: Dict com due_date, client_name, title, priority.

    Returns:
        String formatada com os dados da tarefa.
    """
    due_date = task.get("due_date", "—")
    client_name = task.get("client_name", "—")
    title = task.get("title", "—")
    priority = task.get("priority", "normal")

    # Adiciona emoji de prioridade
    priority_emoji = ""
    if priority == "urgent":
        priority_emoji = "🔴 "
    elif priority == "high":
        priority_emoji = "🟡 "

    return f"{priority_emoji}{due_date} – {client_name} – {title}"


def format_day_label(day: date, today: date) -> str:
    """Formata o label do dia para exibição.

    Args:
        day: Data a ser formatada.
        today: Data de hoje para comparação.

    Returns:
        String formatada: "Hoje", "Ontem" ou "dd/MM".
    """
    if day == today:
        return "Hoje"
    elif day == today - timedelta(days=1):
        return "Ontem"
    else:
        return day.strftime("%d/%m")


def _norm_key_client(task: dict) -> str:
    """Normaliza a chave do cliente para agrupamento.

    Args:
        task: Dict com client_id e/ou client_name.

    Returns:
        String normalizada para usar como chave de agrupamento.
    """
    client_id = task.get("client_id")
    if client_id is not None:
        return f"id:{client_id}"

    client_name = task.get("client_name", "—")
    return f"name:{client_name.strip().lower()}"


def _priority_rank(priority: str) -> int:
    """Retorna ranking numérico da prioridade para ordenação.

    Args:
        priority: String de prioridade (urgent, high, normal, low).

    Returns:
        Int representando ordem (menor = mais urgente).
    """
    priority_map = {
        "urgent": 0,
        "high": 1,
        "normal": 2,
        "low": 3,
    }
    return priority_map.get(priority.lower(), 2)


def group_tasks_for_display(
    tasks: list[dict],
    max_clients: int = 5,
    max_items_per_client: int = 2,
) -> list[str]:
    """Agrupa tarefas por cliente para exibição sem repetição de nomes.

    Args:
        tasks: Lista de dicts com due_date, client_name, title, priority, client_id.
        max_clients: Máximo de clientes a exibir.
        max_items_per_client: Máximo de tarefas por cliente.

    Returns:
        Lista de strings, cada uma é um bloco multi-linha para um cliente.
        Formato:
        - Linha 1: [emoji] Nome do Cliente
        - Linhas seguintes: • due_date – title
        - Última linha (se necessário): • +X outras...
    """
    from collections import defaultdict

    if not tasks:
        return []

    # Agrupar por cliente
    grouped: dict[str, list[dict]] = defaultdict(list)
    client_display_names: dict[str, str] = {}

    for task in tasks:
        key = _norm_key_client(task)
        grouped[key].append(task)

        # Guardar nome de exibição
        if key not in client_display_names:
            client_display_names[key] = task.get("client_name", "—")

    # Ordenar clientes por prioridade máxima (mais urgente primeiro)
    def client_priority(key: str) -> int:
        client_tasks = grouped[key]
        return min(_priority_rank(t.get("priority", "normal")) for t in client_tasks)

    sorted_clients = sorted(grouped.keys(), key=client_priority)[:max_clients]

    # Formatar blocos
    blocks = []
    for client_key in sorted_clients:
        client_tasks = grouped[client_key]
        client_name = client_display_names[client_key]

        # Ordenar tarefas do cliente por prioridade
        client_tasks_sorted = sorted(client_tasks, key=lambda t: _priority_rank(t.get("priority", "normal")))

        # Header do cliente usa tracinho (sem emoji de prioridade)
        # Montar bloco
        lines = [f"- {client_name}"]

        # Adicionar até max_items_per_client tarefas
        visible_tasks = client_tasks_sorted[:max_items_per_client]
        for task in visible_tasks:
            due_date = task.get("due_date", "—")
            title = task.get("title", "—")
            lines.append(f"  • {due_date} – {title}")

        # Indicar se há mais tarefas
        remaining = len(client_tasks) - len(visible_tasks)
        if remaining > 0:
            lines.append(f"  • +{remaining} outra{'s' if remaining > 1 else ''}...")

        blocks.append("\n".join(lines))

    return blocks


def group_deadlines_for_display(
    deadlines: list[dict],
    max_clients: int = 5,
    max_items_per_client: int = 2,
    hide_kind: bool = False,
) -> list[str]:
    """Agrupa prazos por cliente para exibição sem repetição de nomes.

    Args:
        deadlines: Lista de dicts com due_date, client_name, kind, title, status, client_id.
        max_clients: Máximo de clientes a exibir.
        max_items_per_client: Máximo de prazos por cliente.
        hide_kind: Se True, não exibe o campo 'kind' (usado em ANVISA-only).

    Returns:
        Lista de strings, cada uma é um bloco multi-linha para um cliente.
        Formato:
        - Linha 1: 📅 Nome do Cliente
        - Linhas seguintes: • due_date – [kind –] title – status
        - Última linha (se necessário): • +X outras...
    """
    from collections import defaultdict

    if not deadlines:
        return []

    # Agrupar por cliente
    grouped: dict[str, list[dict]] = defaultdict(list)
    client_display_names: dict[str, str] = {}

    for deadline in deadlines:
        key = _norm_key_client(deadline)
        grouped[key].append(deadline)

        # Guardar nome de exibição
        if key not in client_display_names:
            client_display_names[key] = deadline.get("client_name", "—")

    # Pegar primeiros max_clients (já vem ordenado por due_date do service)
    sorted_clients = list(grouped.keys())[:max_clients]

    # Formatar blocos
    blocks = []
    for client_key in sorted_clients:
        client_deadlines = grouped[client_key]
        client_name = client_display_names[client_key]

        # Montar bloco
        lines = [f"📅 {client_name}"]

        # Adicionar até max_items_per_client prazos
        visible_deadlines = client_deadlines[:max_items_per_client]
        for deadline in visible_deadlines:
            due_date = deadline.get("due_date", "—")
            title = deadline.get("title", "—")
            status = deadline.get("status", "—")

            if hide_kind:
                # ANVISA-only: não mostrar kind (redundante)
                lines.append(f"  • {due_date} – {title} – {status}")
            else:
                kind = deadline.get("kind", "—")
                lines.append(f"  • {due_date} – {kind} – {title} – {status}")

        # Indicar se há mais prazos
        remaining = len(client_deadlines) - len(visible_deadlines)
        if remaining > 0:
            lines.append(f"  • +{remaining} outra{'s' if remaining > 1 else ''}...")

        blocks.append("\n".join(lines))

    return blocks
