# -*- coding: utf-8 -*-
"""Dashboard center panel builder for HubScreen.

Builds the central dashboard panel with operational indicators,
hot items, and upcoming deadlines.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT, W, X

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import DashboardViewState


# ============================================================================
# CONSTANTES
# ============================================================================

CARD_PAD_X = 10
CARD_PAD_Y = 8
CARD_VALUE_FONT: Any = ("Segoe UI", 24, "bold")
CARD_LABEL_FONT: tuple[str, int] = ("Segoe UI", 10)
SECTION_TITLE_FONT: Any = ("Segoe UI", 11, "bold")
SECTION_ITEM_FONT: tuple[str, int] = ("Segoe UI", 10)
SECTION_DAY_HEADER_FONT: Any = ("Segoe UI", 9, "bold")

# Limite de atividades exibidas no dashboard
MAX_ACTIVITY_ITEMS_DASHBOARD = 5

# Mensagens padrão
MSG_NO_HOT_ITEMS = "Nenhum alerta crítico por enquanto 😀"
MSG_NO_UPCOMING = "Nenhuma obrigação pendente nos próximos dias."


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def _clear_children(parent: tb.Frame) -> None:
    """Remove todos os widgets filhos de um frame."""
    for child in parent.winfo_children():
        child.destroy()


def _build_indicator_card(
    parent: tb.Frame,
    label: str,
    value: int | float,
    bootstyle: str = "primary",
    value_text: str | None = None,  # Texto customizado para o valor (com ícones, etc.)
    on_click: Callable[[], None] | None = None,  # Callback ao clicar no card
) -> tb.Frame:
    """Constrói um card de indicador com valor e label.

    Args:
        parent: Frame pai onde o card será criado.
        label: Texto descritivo do indicador.
        value: Valor numérico a ser exibido.
        bootstyle: Estilo do card (primary, success, warning, danger, etc.).
        value_text: Texto customizado para exibir no lugar do valor (ex: "2 ⚠").
        on_click: Callback opcional quando o card é clicado (navegação contextual).

    Returns:
        Frame contendo o card criado.
    """
    card = tb.Frame(parent, bootstyle=bootstyle, padding=(CARD_PAD_X, CARD_PAD_Y))

    # Tornar card clicável se callback fornecido
    if on_click is not None:
        card.configure(cursor="hand2")
        # Bind no frame e em todos os labels internos para capturar clique em qualquer parte
        card.bind("<Button-1>", lambda e: on_click())

    # Valor grande (usa value_text se fornecido, senão converte value)
    display_text = (
        value_text if value_text is not None else (str(int(value)) if isinstance(value, float) else str(value))
    )
    value_label = tb.Label(
        card,
        text=display_text,
        font=CARD_VALUE_FONT,
        bootstyle=f"{bootstyle}-inverse",
    )
    value_label.pack(anchor="center")

    # Propagar evento de clique para labels também
    if on_click is not None:
        value_label.bind("<Button-1>", lambda e: on_click())

    # Label descritivo
    text_label = tb.Label(
        card,
        text=label,
        font=CARD_LABEL_FONT,
        bootstyle=f"{bootstyle}-inverse",
    )
    text_label.pack(anchor="center")

    # Propagar evento de clique para labels também
    if on_click is not None:
        text_label.bind("<Button-1>", lambda e: on_click())

    return card


def _build_section_frame(
    parent: tb.Frame,
    title: str,
) -> tuple[tb.Labelframe, tb.Frame]:
    """Constrói um frame de seção com título.

    Args:
        parent: Frame pai.
        title: Título da seção.

    Returns:
        Tupla (section_frame, content_frame) para adicionar conteúdo.
    """
    section = tb.Labelframe(parent, text=title, padding=10)

    content = tb.Frame(section)
    content.pack(fill=X)

    return section, content


def _format_deadline_line(deadline: dict) -> str:
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


def _format_task_line(task: dict) -> str:
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


def _build_risk_radar_section(
    parent: tb.Frame,
    radar: dict[str, dict[str, Any]],
) -> None:
    """Constrói a seção do radar de riscos regulatórios.

    Args:
        parent: Frame pai onde a seção será construída.
        radar: Dicionário com 3 quadrantes (ANVISA, SNGPC, SIFAP).
    """
    section, content = _build_section_frame(parent, title="🎯 Radar de riscos regulatórios")
    section.pack(fill=X, pady=(0, 15))

    # Grid 1x3 para os quadrantes (uma linha com 3 colunas)
    grid_frame = tb.Frame(content)
    grid_frame.pack(fill=X)

    quadrants = [
        ("ANVISA", 0, 0),
        ("SNGPC", 0, 1),
        ("SIFAP", 0, 2),
    ]

    for name, row, col in quadrants:
        data = radar.get(name, {"pending": 0, "overdue": 0, "status": "green"})
        pending = data.get("pending", 0)
        overdue = data.get("overdue", 0)
        status = data.get("status", "green")

        # Map status to bootstyle
        bootstyle_map = {
            "green": "success",
            "yellow": "warning",
            "red": "danger",
        }
        bootstyle = bootstyle_map.get(status, "secondary")

        # Create quadrant frame
        quad_frame = tb.Frame(grid_frame, bootstyle=bootstyle, padding=10)
        quad_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Quadrant name
        name_font: Any = ("Segoe UI", 10, "bold")
        lbl_name = tb.Label(
            quad_frame,
            text=name,
            font=name_font,
            bootstyle=f"{bootstyle}-inverse",
        )
        lbl_name.pack(anchor="center")

        # Counts
        text = f"Pendentes: {pending} – Atrasadas: {overdue}"
        counts_font: tuple[str, int] = ("Segoe UI", 9)
        lbl_counts = tb.Label(
            quad_frame,
            text=text,
            font=counts_font,
            bootstyle=f"{bootstyle}-inverse",
        )
        lbl_counts.pack(anchor="center")

    # Configure grid weights for equal sizing (3 colunas)
    grid_frame.columnconfigure(0, weight=1)
    grid_frame.columnconfigure(1, weight=1)
    grid_frame.columnconfigure(2, weight=1)


def _build_recent_activity_section(
    parent: tb.Frame,
    activities: list[dict[str, Any]],
    *,
    on_view_all: Callable[[], None] | None = None,
) -> None:
    """Constrói a seção de atividade recente da equipe.

    Args:
        parent: Frame pai onde a seção será construída.
        activities: Lista de atividades recentes.
        on_view_all: Callback opcional para visualizar todas as atividades.
    """
    section, content = _build_section_frame(parent, title="📋 Atividade recente da equipe")
    section.pack(fill=X, pady=(0, 15))

    if not activities:
        # Nenhuma atividade
        lbl_no_activity = tb.Label(
            content,
            text="Nenhuma atividade recente.",
            font=SECTION_ITEM_FONT,
        )
        lbl_no_activity.pack(anchor=W, pady=2)
    else:
        # Limitar atividades exibidas
        limited_activities = activities[:MAX_ACTIVITY_ITEMS_DASHBOARD]

        # Agrupar por dia
        today = date.today()
        grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)

        for activity in limited_activities:
            timestamp = activity.get("timestamp")
            if timestamp is not None and hasattr(timestamp, "date"):
                activity_date = timestamp.date()
            else:
                activity_date = today  # Fallback
            grouped[activity_date].append(activity)

        # Ordenar datas em ordem decrescente (mais recente primeiro)
        sorted_dates = sorted(grouped.keys(), reverse=True)

        # Renderizar grupos
        for day in sorted_dates:
            day_activities = grouped[day]

            # Cabeçalho do dia
            day_label_text = _format_day_label(day, today)
            day_label = tb.Label(
                content,
                text=day_label_text,
                font=SECTION_DAY_HEADER_FONT,
                foreground="#666666",
            )
            day_label.pack(anchor=W, pady=(4, 2))

            # Atividades do dia
            for activity in day_activities:
                timestamp = activity.get("timestamp")
                user_name = activity.get("user_name") or ""

                # Get text with fallback for backward compatibility
                raw_text = activity.get("text") or activity.get("title") or activity.get("message") or ""
                text = str(raw_text).strip()

                # If no text but has user_name, use user_name
                if not text and user_name:
                    text = user_name
                elif not text:
                    text = "(atividade sem descrição)"

                # Format timestamp (apenas hora)
                if timestamp is not None and hasattr(timestamp, "strftime"):
                    time_str = timestamp.strftime("%H:%M")
                else:
                    time_str = "—"

                line = f"{time_str} – {text}"
                lbl_activity = tb.Label(
                    content,
                    text=line,
                    font=SECTION_ITEM_FONT,
                )
                lbl_activity.pack(anchor=W, pady=1, padx=(10, 0))

        # Botão "Ver todos" (se houver callback e mais atividades que o limite)
        if on_view_all is not None and len(activities) > MAX_ACTIVITY_ITEMS_DASHBOARD:
            btn_ver_todos = tb.Button(
                content,
                text="Ver todos",
                bootstyle="link",
                command=on_view_all,
            )
            btn_ver_todos.pack(anchor="e", pady=(4, 0))


def _format_day_label(day: date, today: date) -> str:
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


# ============================================================================
# BUILDER PRINCIPAL
# ============================================================================


def build_dashboard_center(
    parent: tb.Frame,
    state: "DashboardViewState",
    *,
    on_new_task: Callable[[], None] | None = None,
    on_new_obligation: Callable[[], None] | None = None,
    on_view_all_activity: Callable[[], None] | None = None,
    on_card_clients_click: Callable[["DashboardViewState"], None] | None = None,
    on_card_pendencias_click: Callable[["DashboardViewState"], None] | None = None,
    on_card_tarefas_click: Callable[["DashboardViewState"], None] | None = None,
) -> None:
    """Constrói o painel central do dashboard na HubScreen.

    Limpa o parent e constrói:
    1. Linha de cards de indicadores (Clientes ativos, Pendências, Tarefas hoje)
    2. Botões de ação ("+ Nova Tarefa", "+ Nova Obrigação")
    3. Bloco "O que está bombando hoje" (hot_items)
    4. Bloco "Próximos vencimentos" (upcoming_deadlines)

    Args:
        parent: Frame pai onde o dashboard será construído.
        state: DashboardViewState com dados agregados e cards formatados.
        on_new_task: Callback opcional para criar nova tarefa.
        on_new_obligation: Callback opcional para criar nova obrigação.
        on_view_all_activity: Callback opcional para visualizar todas as atividades.
        on_card_clients_click: Callback opcional para clique no card de Clientes Ativos.
            Recebe DashboardViewState como parâmetro.
        on_card_pendencias_click: Callback opcional para clique no card de Pendências.
            Recebe DashboardViewState como parâmetro.
        on_card_tarefas_click: Callback opcional para clique no card de Tarefas Hoje.
            Recebe DashboardViewState como parâmetro.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.debug("[build_dashboard_center] Iniciando construção do dashboard...")

    # Extrair snapshot para uso em seções que ainda precisam dele
    snapshot = state.snapshot
    if snapshot is None:
        # Estado inválido, não renderizar nada
        logger.warning("[build_dashboard_center] snapshot é None, não renderizando")
        return

    # Limpar widgets existentes
    _clear_children(parent)

    # Container principal com padding
    main_container = tb.Frame(parent, padding=10)
    main_container.pack(fill=BOTH, expand=True)

    # -------------------------------------------------------------------------
    # 1. LINHA DE CARDS DE INDICADORES (usando DashboardCardView do state)
    # -------------------------------------------------------------------------
    cards_frame = tb.Frame(main_container)
    cards_frame.pack(fill=X, pady=(0, 15))

    # Card: Clientes ativos (consome state.card_clientes)
    if state.card_clientes:
        card_clientes = _build_indicator_card(
            cards_frame,
            label=state.card_clientes.label,
            value=state.card_clientes.value,
            bootstyle=state.card_clientes.bootstyle,
            value_text=state.card_clientes.value_text,
            on_click=(lambda s=state: on_card_clients_click(s)) if on_card_clients_click else None,
        )
        card_clientes.pack(side=LEFT, padx=(0, 10), fill=X, expand=True)

    # Card: Pendências regulatórias (consome state.card_pendencias)
    if state.card_pendencias:
        card_pendencias = _build_indicator_card(
            cards_frame,
            label=state.card_pendencias.label,
            value=state.card_pendencias.value,
            bootstyle=state.card_pendencias.bootstyle,
            value_text=state.card_pendencias.value_text,
            on_click=(lambda s=state: on_card_pendencias_click(s)) if on_card_pendencias_click else None,
        )
        card_pendencias.pack(side=LEFT, padx=(0, 10), fill=X, expand=True)

    # Card: Tarefas hoje (consome state.card_tarefas)
    if state.card_tarefas:
        card_tarefas = _build_indicator_card(
            cards_frame,
            label=state.card_tarefas.label,
            value=state.card_tarefas.value,
            bootstyle=state.card_tarefas.bootstyle,
            value_text=state.card_tarefas.value_text,
            on_click=(lambda s=state: on_card_tarefas_click(s)) if on_card_tarefas_click else None,
        )
        card_tarefas.pack(side=LEFT, fill=X, expand=True)

    # -------------------------------------------------------------------------
    # 1.1. RADAR DE RISCOS REGULATÓRIOS
    # -------------------------------------------------------------------------
    _build_risk_radar_section(main_container, snapshot.risk_radar)

    # -------------------------------------------------------------------------
    # 1.2. BOTÕES DE AÇÃO
    # -------------------------------------------------------------------------
    if on_new_task is not None or on_new_obligation is not None:
        button_frame = tb.Frame(main_container)
        button_frame.pack(fill=X, pady=(0, 15))

        if on_new_task is not None:
            new_task_button = tb.Button(
                button_frame,
                text="➕ Nova Tarefa",
                command=on_new_task,
                bootstyle="success-outline",
                width=20,
            )
            new_task_button.pack(side=LEFT, padx=(0, 10))

        if on_new_obligation is not None:
            new_obligation_button = tb.Button(
                button_frame,
                text="➕ Nova Obrigação",
                command=on_new_obligation,
                bootstyle="secondary-outline",
                width=20,
            )
            new_obligation_button.pack(side=LEFT)

    # -------------------------------------------------------------------------
    # 2. BLOCO "O QUE ESTÁ BOMBANDO HOJE"
    # -------------------------------------------------------------------------
    hot_section, hot_content = _build_section_frame(
        main_container,
        title="🔥 O que está bombando hoje",
    )
    hot_section.pack(fill=X, pady=(0, 15))

    if not snapshot.hot_items:
        # Nenhum alerta
        lbl_no_hot = tb.Label(
            hot_content,
            text=MSG_NO_HOT_ITEMS,
            font=SECTION_ITEM_FONT,
        )
        lbl_no_hot.pack(anchor=W, pady=2)
    else:
        # Exibir cada hot_item com prefixo de alerta
        for item in snapshot.hot_items:
            lbl_item = tb.Label(
                hot_content,
                text=f"⚠ {item}",  # Adiciona ícone de alerta
                font=SECTION_ITEM_FONT,
                bootstyle="danger",
            )
            lbl_item.pack(anchor=W, pady=2)

    # -------------------------------------------------------------------------
    # 2.1. BLOCO "TAREFAS PENDENTES"
    # -------------------------------------------------------------------------
    tasks_section, tasks_content = _build_section_frame(
        main_container,
        title="✅ Tarefas pendentes (até 5)",
    )
    tasks_section.pack(fill=X, pady=(0, 15))

    if not snapshot.pending_tasks:
        # Nenhuma tarefa pendente
        lbl_no_tasks = tb.Label(
            tasks_content,
            text="Nenhuma tarefa pendente no momento.",
            font=SECTION_ITEM_FONT,
        )
        lbl_no_tasks.pack(anchor=W, pady=2)
    else:
        # Exibir cada tarefa (até 5)
        for task in snapshot.pending_tasks[:5]:
            line = _format_task_line(task)
            lbl_task = tb.Label(
                tasks_content,
                text=line,
                font=SECTION_ITEM_FONT,
            )
            lbl_task.pack(anchor=W, pady=2)

    # -------------------------------------------------------------------------
    # 2.2. BLOCO "CLIENTES DO DIA"
    # -------------------------------------------------------------------------
    clients_section, clients_content = _build_section_frame(
        main_container,
        title="📌 Clientes do dia",
    )
    clients_section.pack(fill=X, pady=(0, 15))

    if not snapshot.clients_of_the_day:
        # Nenhum cliente com obrigação hoje
        lbl_no_clients = tb.Label(
            clients_content,
            text="Nenhum cliente com obrigação para hoje.",
            font=SECTION_ITEM_FONT,
        )
        lbl_no_clients.pack(anchor=W, pady=2)
    else:
        # Exibir cada cliente
        for item in snapshot.clients_of_the_day:
            client_name = item.get("client_name") or f"Cliente #{item.get('client_id')}"
            kinds = item.get("obligation_kinds") or []
            kinds_str = ", ".join(kinds) if kinds else "obrigação"
            text = f"{client_name} – {kinds_str}"
            lbl_client = tb.Label(
                clients_content,
                text=text,
                font=SECTION_ITEM_FONT,
            )
            lbl_client.pack(anchor=W, pady=2)

    # -------------------------------------------------------------------------
    # 2.3. BLOCO "ATIVIDADE RECENTE DA EQUIPE"
    # -------------------------------------------------------------------------
    _build_recent_activity_section(
        main_container,
        snapshot.recent_activity,
        on_view_all=on_view_all_activity,
    )

    # -------------------------------------------------------------------------
    # 3. BLOCO "PRÓXIMOS VENCIMENTOS"
    # -------------------------------------------------------------------------
    deadlines_section, deadlines_content = _build_section_frame(
        main_container,
        title="📅 Próximos vencimentos (até 5)",
    )
    deadlines_section.pack(fill=X, pady=(0, 10))

    if not snapshot.upcoming_deadlines:
        # Nenhum vencimento
        lbl_no_deadlines = tb.Label(
            deadlines_content,
            text=MSG_NO_UPCOMING,
            font=SECTION_ITEM_FONT,
        )
        lbl_no_deadlines.pack(anchor=W, pady=2)
    else:
        # Exibir cada deadline (até 5)
        for deadline in snapshot.upcoming_deadlines[:5]:
            line = _format_deadline_line(deadline)
            lbl_deadline = tb.Label(
                deadlines_content,
                text=line,
                font=SECTION_ITEM_FONT,
            )
            lbl_deadline.pack(anchor=W, pady=2)


def build_dashboard_error(parent: tb.Frame, message: str | None = None) -> None:
    """Constrói uma mensagem de erro amigável no painel central.

    Args:
        parent: Frame pai onde a mensagem será exibida.
        message: Mensagem de erro customizada. Se None, usa mensagem padrão.
    """
    _clear_children(parent)

    error_msg = message or "Não foi possível carregar o dashboard agora. Tente novamente mais tarde."

    container = tb.Frame(parent, padding=20)
    container.pack(fill=BOTH, expand=True)

    # Ícone de erro
    icon_font: Any = ("Segoe UI", 32)
    lbl_icon = tb.Label(
        container,
        text="⚠️",
        font=icon_font,
    )
    lbl_icon.pack(pady=(20, 10))

    # Mensagem
    msg_font: Any = ("Segoe UI", 11)
    lbl_msg = tb.Label(
        container,
        text=error_msg,
        font=msg_font,
        wraplength=300,
        justify="center",
    )
    lbl_msg.pack(pady=10)
