# -*- coding: utf-8 -*-
"""HubDialogs - Diálogos modais do HUB (edição de notas, confirmações).

Este módulo contém diálogos especializados que eram anteriormente métodos
do HubScreen. Extraído em MF-10 para reduzir tamanho e complexidade.

Responsabilidades:
- show_note_editor: Diálogo para criar/editar notas
- confirm_delete_note: Diálogo de confirmação de exclusão
- show_error/show_info: Wrappers de messageboxes
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from tkinter import messagebox
from typing import Any, Literal, Sequence

import ttkbootstrap as tb

from src.helpers.formatters import format_cnpj

logger = logging.getLogger(__name__)


def show_note_editor(
    parent: tk.Misc,
    note_data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Mostra editor de nota em diálogo modal.

    Args:
        parent: Widget pai (para modal)
        note_data: Dados da nota para editar (None para criar nova).

    Returns:
        Dict com dados atualizados se confirmado, None se cancelado.

    Dict retornado contém:
        - body: str - Texto da nota
        - id: str | None - ID da nota (None para nova)
        - is_pinned: bool - Se está fixada
        - is_done: bool - Se está marcada como concluída
    """
    # Dialog setup
    dialog = tk.Toplevel(parent)
    dialog.title("Editar Nota" if note_data else "Nova Nota")
    dialog.geometry("500x350")
    dialog.transient(parent)
    dialog.grab_set()

    # Center dialog
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    # Result container (mutable para closures)
    result = {"confirmed": False, "data": None}

    # Build UI
    frame = tb.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)

    # Label
    tb.Label(frame, text="Texto da nota:").pack(anchor="w", pady=(0, 5))

    # Text widget with scrollbar
    text_frame = tb.Frame(frame)
    text_frame.pack(fill="both", expand=True, pady=(0, 10))

    scrollbar = tb.Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")

    text_widget = tk.Text(
        text_frame,
        wrap="word",
        yscrollcommand=scrollbar.set,
        font=("Segoe UI", 10),
    )
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_widget.yview)

    # Populate text if editing
    if note_data and "body" in note_data:
        text_widget.insert("1.0", note_data["body"])
        text_widget.mark_set("insert", "1.0")  # Cursor no início

    # Focus on text
    text_widget.focus_set()

    # Buttons frame
    btn_frame = tb.Frame(frame)
    btn_frame.pack(fill="x")

    def on_confirm():
        """Handler para confirmação."""
        body = text_widget.get("1.0", "end-1c").strip()
        if not body:
            messagebox.showwarning(
                "Campo vazio",
                "O texto da nota não pode estar vazio.",
                parent=dialog,
            )
            return

        result["confirmed"] = True
        result["data"] = {
            "body": body,
            "id": note_data.get("id") if note_data else None,
            "is_pinned": note_data.get("is_pinned", False) if note_data else False,
            "is_done": note_data.get("is_done", False) if note_data else False,
        }
        dialog.destroy()

    def on_cancel():
        """Handler para cancelamento."""
        result["confirmed"] = False
        dialog.destroy()

    # Buttons
    tb.Button(
        btn_frame,
        text="Confirmar",
        bootstyle="success",
        command=on_confirm,
    ).pack(side="left", padx=(0, 5))

    tb.Button(
        btn_frame,
        text="Cancelar",
        bootstyle="secondary",
        command=on_cancel,
    ).pack(side="left")

    # Keyboard bindings
    dialog.bind("<Control-Return>", lambda _e: on_confirm())
    dialog.bind("<Escape>", lambda _e: on_cancel())

    # Wait for dialog
    dialog.wait_window()

    # Return result
    return result["data"] if result["confirmed"] else None


def confirm_delete_note(parent: tk.Misc, note_data: dict[str, Any]) -> bool:
    """Confirma exclusão de nota.

    Args:
        parent: Widget pai (para modal)
        note_data: Dados da nota a ser deletada.

    Returns:
        True se confirmado, False se cancelado.
    """
    body = note_data.get("body", "")
    preview = body[:50] + "..." if len(body) > 50 else body
    return messagebox.askyesno(
        "Confirmar exclusão",
        f"Excluir anotação:\n\n{preview}",
        parent=parent,
    )


def show_error(parent: tk.Misc, title: str, message: str) -> None:
    """Mostra mensagem de erro.

    Args:
        parent: Widget pai (para modal)
        title: Título do diálogo
        message: Mensagem de erro
    """
    messagebox.showerror(title, message, parent=parent)


def show_info(parent: tk.Misc, title: str, message: str) -> None:
    """Mostra mensagem informativa.

    Args:
        parent: Widget pai (para modal)
        title: Título do diálogo
        message: Mensagem informativa
    """
    messagebox.showinfo(title, message, parent=parent)


# =============================================================================
# ANVISA: Seletor de histórico
# =============================================================================

AnvisaPickAction = Literal["history", "anvisa"]


def _parse_date_flexible(date_str: str) -> date | None:
    """Parse data em múltiplos formatos (ISO e BR).

    Args:
        date_str: String de data ("YYYY-MM-DD", "DD/MM/YYYY", etc.)

    Returns:
        date ou None se falhar
    """
    from datetime import datetime

    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()
    if not date_str or date_str == "—":
        return None

    # Tentar ISO: YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(date_str.split("+")[0].split("Z")[0], fmt).date()
        except (ValueError, AttributeError):
            continue

    # Tentar BR: DD/MM/YYYY
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        pass

    return None


def _calculate_deadline_status(due_date_str: str) -> str:
    """Calcula situação do prazo baseado na data.

    Args:
        due_date_str: String da data de vencimento

    Returns:
        String com status: "Hoje", "Atrasada Xd", "Em Xd", ou "Sem prazo"
    """
    from datetime import date as date_type

    due_date = _parse_date_flexible(due_date_str)
    if not due_date:
        return "Sem prazo"

    today = date_type.today()
    delta = (due_date - today).days

    if delta == 0:
        return "Hoje"
    elif delta < 0:
        return f"Atrasada {abs(delta)}d"
    else:
        return f"Em {delta}d"


def pick_anvisa_history_target(
    parent: tk.Misc,
    items: Sequence[dict[str, Any]],
) -> tuple[AnvisaPickAction, str] | None:
    """Diálogo modal para escolher qual cliente abrir no histórico ANVISA.

    items pode vir de:
      - snapshot.clients_of_the_day (preferível): {client_id, client_name, obligation_kinds[]}
      - snapshot.pending_tasks (fallback): {client_id, client_name, title, due_date?}

    Args:
        parent: Widget pai (para modal)
        items: Sequência de items com informações de clientes e tarefas

    Returns:
        ("history", client_id) | ("anvisa","") | None
    """
    # Importar STATUS_OPEN para filtrar apenas demandas abertas
    try:
        from src.modules.anvisa.constants import STATUS_OPEN

        open_status = STATUS_OPEN
    except ImportError:
        # Fallback se constants não disponível
        open_status = frozenset({"draft", "submitted", "in_progress"})
    # Normalizar e agrupar por cliente preservando ordem
    order: list[str] = []
    by_client: dict[str, dict[str, Any]] = {}

    for raw in items:
        try:
            client_id = str(raw.get("client_id", "")).strip()
        except Exception:
            client_id = ""
        if not client_id:
            continue

        client_name = str(raw.get("client_name") or f"Cliente #{client_id}").strip()

        if client_id not in by_client:
            by_client[client_id] = {
                "client_id": client_id,
                "client_name": client_name,
                "cnpj": str(raw.get("cnpj") or "").strip(),  # Capturar CNPJ dos raw items
                "details": [],
                "due_dates": [],  # Lista de datas de vencimento
                "created_dates": [],  # Lista de datas de criação
            }
            order.append(client_id)

        details_list: list[str] = by_client[client_id]["details"]
        due_dates_list: list[str] = by_client[client_id]["due_dates"]
        created_dates_list: list[str] = by_client[client_id]["created_dates"]

        # Coletar due_date e created_at
        due_date = str(raw.get("due_date") or "").strip()
        created_at = str(raw.get("created_at") or raw.get("criada_em") or "").strip()

        if due_date and due_date != "—":
            due_dates_list.append(due_date)
        if created_at and created_at != "—":
            created_dates_list.append(created_at)

        # Preferir obligation_kinds (clients_of_the_day)
        kinds = raw.get("obligation_kinds")
        if isinstance(kinds, list) and kinds:
            for k in kinds:
                ks = str(k).strip()
                if ks and ks not in details_list:
                    details_list.append(ks)
            continue

        # Fallback para pending_tasks
        title = str(raw.get("title") or "").strip()
        due = str(raw.get("due_date") or "").strip()
        if title and due:
            line = f"{due} — {title}"
            if line not in details_list:
                details_list.append(line)
        elif title:
            if title not in details_list:
                details_list.append(title)

    if not order:
        return None

    # =========================================================================
    # Buscar demandas ANVISA reais para enriquecer dados
    # =========================================================================
    anvisa_requests_by_client: dict[str, list[dict[str, Any]]] = {}
    anvisa_service = None

    try:
        from src.helpers.auth_utils import resolve_org_id
        from src.infra.repositories.anvisa_requests_repository import AnvisaRequestsRepositoryAdapter
        from src.modules.anvisa.services.anvisa_service import AnvisaService

        org_id = resolve_org_id()
        if not org_id:
            logger.warning("pick_anvisa_history_target: org_id não disponível, colunas ficarão vazias")
        else:
            repo = AnvisaRequestsRepositoryAdapter()
            anvisa_service = AnvisaService(repo)
            all_requests = repo.list_requests(org_id)

            # Filtrar apenas clientes exibidos e agrupar
            client_ids_set = set(order)
            for req in all_requests:
                req_client_id = str(req.get("client_id", "")).strip()
                if req_client_id in client_ids_set:
                    if req_client_id not in anvisa_requests_by_client:
                        anvisa_requests_by_client[req_client_id] = []
                    anvisa_requests_by_client[req_client_id].append(req)

    except Exception as e:
        logger.warning(f"pick_anvisa_history_target: falha ao buscar demandas ANVISA: {e}")
        # Continuar mesmo sem dados ANVISA (colunas ficarão com "—")

    # =========================================================================
    # PASSO A: Extrair CNPJs do embed do join (req["clients"]["cnpj"])
    # =========================================================================
    join_cnpj_map: dict[str, str] = {}

    for cid, requests in anvisa_requests_by_client.items():
        if not requests:
            continue
        # Pegar primeira demanda que tenha CNPJ no embed
        for req in requests:
            clients_embed = req.get("clients") or {}
            cnpj_from_join = (clients_embed.get("cnpj") or "").strip()
            if cnpj_from_join:
                join_cnpj_map[cid] = cnpj_from_join
                break  # Já encontrou CNPJ deste cliente

    logger.info(f"pick_anvisa_history_target: CNPJs do join: {len(join_cnpj_map)} de {len(order)} clientes")

    # =========================================================================
    # PASSO B: Bulk query em clients (apenas para IDs sem CNPJ no join)
    # =========================================================================
    bulk_cnpj_map: dict[str, str] = {}

    # Identificar IDs que ainda não têm CNPJ
    missing_ids_str = [cid for cid in order if cid not in join_cnpj_map]

    if not missing_ids_str:
        # Guard clause: join já cobriu tudo
        logger.info("pick_anvisa_history_target: bulk CNPJ skip (join já cobriu todos os clientes)")
    else:
        # Só executar bulk se realmente faltar CNPJ
        try:
            # Converter para int (garantindo list[int])
            missing_ids = []
            for cid in missing_ids_str:
                try:
                    missing_ids.append(int(cid))
                except (ValueError, TypeError):
                    logger.warning(f"pick_anvisa_history_target: ID inválido para int: {cid}")
                    continue

            if missing_ids:
                logger.info(f"pick_anvisa_history_target: buscando CNPJs faltantes para {len(missing_ids)} clientes")

                # Import DENTRO do bloco condicional (só quando necessário)
                from src.infra.supabase_client import get_supabase
                from src.helpers.auth_utils import resolve_org_id

                org_id = resolve_org_id()
                sb = get_supabase()

                # Tentar primeiro COM org_id e deleted_at
                try:
                    resp = (
                        sb.table("clients")
                        .select("id,cnpj")
                        .eq("org_id", org_id)
                        .is_("deleted_at", "null")
                        .in_("id", missing_ids)
                        .execute()
                    )

                    if resp.data:
                        logger.info(f"pick_anvisa_history_target: bulk query retornou {len(resp.data)} CNPJs")
                        for row in resp.data:
                            client_id_str = str(row.get("id", ""))
                            cnpj_value = (row.get("cnpj") or "").strip()
                            if client_id_str and cnpj_value:
                                bulk_cnpj_map[client_id_str] = cnpj_value
                    else:
                        logger.warning(
                            f"pick_anvisa_history_target: bulk query retornou 0 linhas para {len(missing_ids)} IDs"
                        )
                        logger.warning(
                            f"pick_anvisa_history_target: missing_ids={missing_ids[:10]}..."
                        )  # Log primeiros 10

                except Exception as inner_e:
                    # Fallback: tentar SEM filtros de org_id/deleted_at
                    logger.warning(f"pick_anvisa_history_target: erro com filtros, tentando sem filtros: {inner_e}")
                    try:
                        resp = sb.table("clients").select("id,cnpj").in_("id", missing_ids).execute()
                        if resp.data:
                            logger.info(
                                f"pick_anvisa_history_target: bulk query (sem filtros) retornou {len(resp.data)} CNPJs"
                            )
                            for row in resp.data:
                                client_id_str = str(row.get("id", ""))
                                cnpj_value = (row.get("cnpj") or "").strip()
                                if client_id_str and cnpj_value:
                                    bulk_cnpj_map[client_id_str] = cnpj_value
                    except Exception as fallback_e:
                        logger.warning(f"pick_anvisa_history_target: fallback também falhou: {fallback_e}")

        except Exception as e:
            logger.warning(f"pick_anvisa_history_target: erro geral ao buscar CNPJs: {e}")
            # Continuar com CNPJs vazios (fallback "—")

    # =========================================================================
    # Escolher demanda representativa por cliente e calcular colunas
    # =========================================================================
    def _choose_representative_request(requests: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Escolhe a demanda mais representativa do cliente.

        Critério:
        1. APENAS demandas abertas (draft, submitted, in_progress)
        2. Entre abertas, escolher a com prazo mais urgente (atrasada > hoje > futura próxima > sem prazo)
        3. Se não houver aberta, retornar None (cliente não aparece no picker)
        """
        if not requests:
            return None

        # Filtrar APENAS abertas usando STATUS_OPEN
        open_requests = [r for r in requests if r.get("status", "") in open_status]

        if open_requests:
            # Ordenar abertas por urgência de prazo
            def urgency_key(req: dict[str, Any]) -> tuple[int, date | None]:
                payload = req.get("payload") or {}
                due_str = payload.get("due_date", "")
                parsed = _parse_date_flexible(due_str)
                today = date.today()

                if parsed is None:
                    return (4, None)  # Sem prazo por último
                elif parsed < today:
                    return (1, parsed)  # Atrasadas primeiro (mais antiga = mais urgente)
                elif parsed == today:
                    return (2, parsed)  # Hoje
                else:
                    return (3, parsed)  # Futuras (mais próxima primeiro)

            open_requests.sort(key=urgency_key)
            return open_requests[0]

        # Se não há aberta, cliente NÃO aparece no picker
        return None

    for cid in order:
        data = by_client[cid]

        # Buscar demanda representativa
        client_requests = anvisa_requests_by_client.get(cid, [])
        representative_req = _choose_representative_request(client_requests)

        # SKIP: se não há demanda aberta, não mostrar cliente no picker
        if not representative_req:
            continue

        if representative_req and anvisa_service:
            # Extrair dados da demanda representativa usando AnvisaService
            payload = representative_req.get("payload") or {}

            # created_at - usar format_dt_local_dash do service (padrão: DD/MM/YYYY HH:MM)
            created_at_str = representative_req.get("created_at", "")
            created_dt_utc = anvisa_service._parse_iso_datetime(created_at_str)
            data["criada_em_display"] = anvisa_service.format_dt_local_dash(created_dt_utc) if created_dt_utc else "—"

            # Adicionar inicial do criador, se disponível
            created_by = str(payload.get("created_by") or "").strip()
            if data["criada_em_display"] != "—" and created_by:
                initial = anvisa_service.resolve_initial_from_email(created_by)
                if initial:
                    data["criada_em_display"] = f"{data['criada_em_display']} ({initial})"

            # due_date (prazo) - usar format_due_date_iso_to_br do service
            due_date_str = payload.get("due_date", "")
            data["prazo_display"] = anvisa_service.format_due_date_iso_to_br(due_date_str)
            data["prazo_parsed"] = _parse_date_flexible(due_date_str)

            # situacao (status + prazo se aberto)
            status_raw = representative_req.get("status", "")
            status_humano = anvisa_service.human_status(status_raw)

            # Se "Em aberto", adicionar contexto de prazo
            if status_humano == "Em aberto" and due_date_str:
                deadline_status = _calculate_deadline_status(due_date_str)
                if deadline_status != "Sem prazo":
                    data["situacao"] = f"{status_humano} — {deadline_status}"
                else:
                    data["situacao"] = status_humano
            else:
                data["situacao"] = status_humano

            # request_type para melhorar descrição
            request_type = payload.get("request_type", "")
            if request_type and not data["details"]:
                data["details"].append(request_type)

        else:
            # Fallback: sem demanda ANVISA encontrada
            data["criada_em_display"] = "—"
            data["prazo_display"] = "—"
            data["situacao"] = "—"
            data["prazo_parsed"] = None

    # =========================================================================
    # Ordenar por prioridade: status + prazo
    # =========================================================================
    # Picker só mostra ABERTAS, ordenadas por urgência:
    # 1) Em aberto + Atrasada (mais dias atrasado primeiro)
    # 2) Em aberto + Hoje
    # 3) Em aberto + Em Xd (menor X primeiro)
    # 4) Em aberto sem prazo
    def sort_key(cid: str) -> tuple[int, date | None]:
        data = by_client[cid]
        parsed = data.get("prazo_parsed")
        today = date.today()

        # Todas são abertas (fechadas já foram filtradas)
        if parsed is None:
            return (4, None)  # Em aberto sem prazo
        elif parsed < today:
            return (1, parsed)  # Em aberto + Atrasada (mais antiga primeiro)
        elif parsed == today:
            return (2, parsed)  # Em aberto + Hoje
        else:
            return (3, parsed)  # Em aberto + Futura (mais próxima primeiro)

    order.sort(key=sort_key)

    dialog = tk.Toplevel(parent)
    dialog.title("Escolher histórico ANVISA")
    dialog.geometry("1280x450")
    dialog.minsize(1250, 420)  # Tamanho mínimo para caber todas as colunas
    dialog.transient(parent)
    dialog.grab_set()

    # Centralizar
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    result: dict[str, Any] = {"action": None, "client_id": ""}

    frame = tb.Frame(dialog, padding=10)
    frame.pack(fill="both", expand=True)

    tb.Label(
        frame,
        text="Selecione o cliente para abrir o histórico de regularizações:",
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(0, 8))

    tree_frame = tb.Frame(frame)
    tree_frame.pack(fill="both", expand=True)

    # Scrollbar vertical (única - sem horizontal)
    scrollbar_y = tb.Scrollbar(tree_frame, orient="vertical")
    scrollbar_y.pack(side="right", fill="y")

    tree = tb.Treeview(
        tree_frame,
        columns=("cliente_id", "cnpj", "regularizacoes", "criada_em", "prazo", "situacao"),
        show="headings",
        height=10,
    )
    tree.pack(side="left", fill="both", expand=True)

    # Configurar apenas scrollbar vertical
    scrollbar_y.config(command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)

    # Configurar headings e columns - TUDO CENTRALIZADO
    tree.heading("cliente_id", text="Cliente", anchor="center")
    tree.heading("cnpj", text="CNPJ", anchor="center")
    tree.heading("regularizacoes", text="Regularizações", anchor="center")
    tree.heading("criada_em", text="Criada em", anchor="center")
    tree.heading("prazo", text="Prazo", anchor="center")
    tree.heading("situacao", text="Situação", anchor="center")

    # Constantes de largura para layout sem scrollbar horizontal
    w_cliente_id = 90
    w_cnpj = 170
    w_criada = 190
    w_prazo = 120
    w_sit = 260
    reg_min = 360
    margin = 40

    # Larguras fixas para colunas (stretch=False)
    tree.column("cliente_id", width=w_cliente_id, minwidth=80, anchor="center", stretch=False)
    tree.column("cnpj", width=w_cnpj, minwidth=150, anchor="center", stretch=False)
    tree.column("criada_em", width=w_criada, minwidth=170, anchor="center", stretch=False)
    tree.column("prazo", width=w_prazo, minwidth=110, anchor="center", stretch=False)
    tree.column("situacao", width=w_sit, minwidth=240, anchor="center", stretch=False)

    # Helper para aplicar layout de "Regularizações" usando espaço disponível
    def _apply_picker_column_layout() -> None:
        """Ajusta largura de 'regularizacoes' dinamicamente para usar espaço restante."""
        tree.update_idletasks()
        total = tree.winfo_width()
        if total <= 1:
            total = 1250  # Fallback

        fixed = w_cliente_id + w_cnpj + w_criada + w_prazo + w_sit + margin
        reg = max(reg_min, total - fixed)

        tree.column("regularizacoes", width=reg, minwidth=reg_min, anchor="center", stretch=True)

    # Aplicar layout inicial
    dialog.update_idletasks()
    _apply_picker_column_layout()

    # Reajustar layout ao redimensionar janela (com debounce)
    _pending_layout: str | None = None

    def _on_tree_configure(_event: Any) -> None:
        """Handler de <Configure> com debounce para reajustar layout."""
        nonlocal _pending_layout
        if _pending_layout is not None:
            tree.after_cancel(_pending_layout)
        _pending_layout = tree.after(50, _apply_picker_column_layout)

    tree.bind("<Configure>", _on_tree_configure)

    # Travar redimensionamento e arrasto de colunas
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    AnvisaScreen._lock_treeview_columns(tree)

    # Inserir apenas clientes com demandas abertas (já filtrados no loop anterior)
    for cid in order:
        # Verificar se cliente tem demanda aberta
        client_requests = anvisa_requests_by_client.get(cid, [])
        if not _choose_representative_request(client_requests):
            continue  # Cliente sem abertas, skip

        data = by_client[cid]
        details = data.get("details") or []
        if isinstance(details, list):
            detail_str = ", ".join(str(x) for x in details if str(x).strip())
        else:
            detail_str = str(details)

        # CNPJ com prioridade: join → bulk → fallback
        cnpj_raw = join_cnpj_map.get(cid) or bulk_cnpj_map.get(cid) or ""
        cnpj_fmt = format_cnpj(cnpj_raw)
        cnpj_display = cnpj_fmt if cnpj_fmt else "—"

        tree.insert(
            "",
            "end",
            iid=cid,
            values=(
                cid,  # ID do cliente
                cnpj_display,  # CNPJ
                detail_str,  # Regularizações
                data.get("criada_em_display", "—"),
                data.get("prazo_display", "—"),
                data.get("situacao", "Sem prazo"),
            ),
        )

    btn_frame = tb.Frame(frame)
    btn_frame.pack(fill="x", pady=(10, 0))

    btn_open_history = tb.Button(
        btn_frame,
        text="Abrir histórico",
        bootstyle="primary",
        state="disabled",
    )
    btn_open_history.pack(side="left")

    def _selected_client_id() -> str:
        sel = tree.selection()
        return str(sel[0]) if sel else ""

    def on_open_history() -> None:
        cid = _selected_client_id()
        if not cid:
            return
        result["action"] = "history"
        result["client_id"] = cid
        dialog.destroy()

    def on_cancel() -> None:
        dialog.destroy()

    btn_open_history.configure(command=on_open_history)

    tb.Button(
        btn_frame,
        text="Cancelar",
        bootstyle="secondary",
        command=on_cancel,
    ).pack(side="left", padx=(8, 0))

    def on_select(_event: Any = None) -> None:
        btn_open_history.configure(state="normal" if _selected_client_id() else "disabled")

    tree.bind("<<TreeviewSelect>>", on_select, add="+")
    tree.bind("<Double-1>", lambda _e: on_open_history(), add="+")
    dialog.bind("<Return>", lambda _e: on_open_history(), add="+")
    dialog.bind("<Escape>", lambda _e: on_cancel(), add="+")
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    # Selecionar 1º item por padrão
    try:
        first = order[0]
        tree.selection_set(first)
        tree.focus(first)
        tree.see(first)
        on_select()
    except Exception:
        # Swallow: se falhar ao selecionar primeiro item, dialog continua utilizável
        logger.debug("Erro ao selecionar primeiro item no picker", exc_info=True)

    dialog.wait_window()

    action = result.get("action")
    if action in ("history", "anvisa"):
        return (action, str(result.get("client_id") or ""))
    return None
