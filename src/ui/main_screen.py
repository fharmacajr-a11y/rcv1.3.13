# -*- coding: utf-8 -*-
"""Main screen frame extracted from app_gui (clients list)."""

from __future__ import annotations

import json
import logging
import os
import re
import tkinter as tk
import urllib.parse
import webbrowser
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

try:
    import ttkbootstrap as tb
except Exception:
    tb = ttk  # fallback


from infra.supabase_client import get_cloud_status_for_ui, get_supabase_state
from src.core.db_manager import get_cliente_by_id, update_status_only
from src.core.search import search_clientes
from src.core.textnorm import join_and_normalize, normalize_search
from src.ui.components import (
    create_clients_treeview,
)
from src.ui.components import create_footer_buttons as create_footer
from src.ui.components import (
    create_search_controls,
)
from src.utils.phone_utils import normalize_br_whatsapp
from src.utils.prefs import load_columns_visibility, save_columns_visibility

log = logging.getLogger("app_gui")

DEFAULT_ORDER_LABEL = "Razao Social (A->Z)"
ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = {
    "Razao Social (A->Z)": ("razao_social", False),
    "CNPJ (A->Z)": ("cnpj", False),
    "Nome (A->Z)": ("nome", False),
    "ID (1→9)": ("id", False),
    "ID (9→1)": ("id", True),
    "Ultima Alteracao (mais recente)": ("ultima_alteracao", False),
    "Ultima Alteracao (mais antiga)": ("ultima_alteracao", True),
}


def _load_status_choices() -> list[str]:
    default = [
        "Novo lead",
        "Sem resposta",
        "Aguardando documento",
        "Aguardando pagamento",
        "Em cadastro",
        "Finalizado",
        "Follow-up hoje",
        "Follow-up amanhã",
    ]
    raw = (os.getenv("RC_STATUS_CHOICES") or "").strip()
    if not raw:
        return default
    try:
        if raw.startswith("["):
            choices = json.loads(raw)
        else:
            choices = [s.strip() for s in raw.split(",") if s.strip()]
        return [str(s) for s in choices if s]
    except Exception:
        return default


def _load_status_groups() -> list[tuple[str, list[str]]]:
    """Load grouped statuses from RC_STATUS_GROUPS or fall back to a single group."""
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
        except Exception:
            pass
    return [("Status gerais", _load_status_choices())]


def _build_status_menu(menu: tk.Menu, on_pick: Callable[[str], None]) -> None:
    """Rebuild the status menu adding group headers, separators, and clear option."""
    menu.delete(0, "end")

    groups = _load_status_groups()
    for gi, (name, items) in enumerate(groups):
        if gi > 0:
            menu.add_separator()
        menu.add_command(label=f"— {name} —", state="disabled")
        for label in items:
            menu.add_command(label=label, command=lambda l=label: on_pick(l))  # noqa: E741

    menu.add_separator()
    menu.add_command(label="Limpar", command=lambda: on_pick(""))


STATUS_CHOICES = [label for _, values in _load_status_groups() for label in values]
STATUS_PREFIX_RE = re.compile(r"^\s*\[(?P<st>[^\]]+)\]\s*")

__all__ = ["MainScreenFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]


class MainScreenFrame(tb.Frame):  # pyright: ignore[reportGeneralTypeIssues]
    """
    Frame da tela principal (lista de clientes + ações).
    Recebe callbacks do App para operações de negócio.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_new: Optional[Callable[[], None]] = None,
        on_edit: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_upload: Optional[Callable[[], None]] = None,
        on_open_subpastas: Optional[Callable[[], None]] = None,
        on_open_lixeira: Optional[Callable[[], None]] = None,
        app: Optional[Any] = None,
        order_choices: Optional[Dict[str, Tuple[Optional[str], bool]]] = None,
        default_order_label: str = DEFAULT_ORDER_LABEL,
        on_upload_folder: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self.app = app
        self.on_new = on_new
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_upload = on_upload
        self.on_upload_folder = on_upload_folder
        self.on_open_subpastas = on_open_subpastas
        self.on_open_lixeira = on_open_lixeira

        self._order_choices = order_choices or ORDER_CHOICES
        self._default_order_label = default_order_label or DEFAULT_ORDER_LABEL
        self._buscar_after: Optional[str] = None

        # Modo de seleção (para integração com Senhas)
        self._pick_mode: bool = False
        self._on_pick = None  # callable(dict_cliente)
        self._return_to = None  # callable() que volta pra tela anterior
        self._saved_toolbar_state = {}  # Armazena estado dos botões CRUD
        self._search_norm_cache: Dict[str, str] = {}

        search_controls = create_search_controls(
            self,
            order_choices=list(self._order_choices.keys()),
            default_order=self._default_order_label,
            on_search=self._buscar,
            on_clear=self._limpar_busca,
            on_order_change=self.carregar,
            on_status_change=self.apply_filters,
            status_choices=STATUS_CHOICES,
        )
        search_controls.frame.pack(fill="x", padx=10, pady=10)
        self.var_busca = search_controls.search_var
        self.var_ordem = search_controls.order_var
        self.var_status = search_controls.status_var
        self.status_filter = search_controls.status_combobox
        self.status_menu: Optional[tk.Menu] = None
        self._status_menu_cliente: Optional[int] = None
        self._status_menu_row: Optional[str] = None

        # --- Divisória entre filtros e a faixa de controles de colunas
        self._cols_separator = ttk.Separator(self, orient="horizontal")
        self._cols_separator.pack(side="top", fill="x", padx=10, pady=(6, 4))

        # --- Faixa alinhada às colunas (fora do Treeview, mas sincronizada)
        HEADER_CTRL_H = 26  # altura da faixa dos controles
        self.columns_align_bar = tk.Frame(self, height=HEADER_CTRL_H)
        self.columns_align_bar.pack(side="top", fill="x", padx=10)

        # IDs/ordem exatos das colunas
        self._col_order = (
            "ID",
            "Razao Social",
            "CNPJ",
            "Nome",
            "WhatsApp",
            "Observacoes",
            "Status",
            "Ultima Alteracao",
        )

        # Estado por usuário (mantemos persistência)
        def _user_key():
            return getattr(self, "current_user_email", None) or getattr(self, "status_user_email", None) or "default"

        self._user_key = _user_key()
        _saved = load_columns_visibility(self._user_key)
        self._col_content_visible = {c: tk.BooleanVar(value=_saved.get(c, True)) for c in self._col_order}

        # Lista atual de clientes (para refresh)
        self._all_clientes: list[Any] = []
        self._current_clientes = []

        # Funções auxiliares (nested functions)
        def _persist_visibility():
            save_columns_visibility(
                self._user_key,
                {k: v.get() for k, v in self._col_content_visible.items()},
            )

        def _on_toggle(col: str):
            # Garante pelo menos uma visível
            if not any(v.get() for v in self._col_content_visible.values()):
                self._col_content_visible[col].set(True)
            self._refresh_rows()
            _persist_visibility()

        self.client_list = create_clients_treeview(
            self,
            on_double_click=lambda _event: self._invoke_safe(self.on_edit),
            on_select=self._update_main_buttons_state,
            on_delete=lambda _event: self._invoke_safe(self.on_delete),
            on_click=self._on_click,
        )
        self.client_list.pack(expand=True, fill="both", padx=10, pady=5)
        self.tree = self.client_list
        self.client_list.bind("<Button-3>", self._on_status_menu, add="+")

        # Configura headings sem sobrescrever os textos vindos do componente
        self.client_list.configure(displaycolumns=self._col_order)
        for col in self._col_order:
            try:
                # mantém o texto atual (com acento) se já veio do componente
                cur = self.client_list.heading(col, option="text")
                if not cur:
                    # fallback para IDs internos sem acento
                    friendly = {
                        "Razao Social": "Razão Social",
                        "Observacoes": "Observações",
                        "Ultima Alteracao": "Última Alteração",
                    }.get(col, col)
                    self.client_list.heading(col, text=friendly, anchor="center")
                else:
                    self.client_list.heading(col, text=cur, anchor="center")
            except Exception as e:
                log.debug("Erro ao configurar heading %s: %s", col, e)

        # Larguras originais (para não mexer quando ocultar)
        self._col_widths = {}
        for c in self._col_order:
            try:
                self._col_widths[c] = self.client_list.column(c, option="width")
            except Exception:
                self._col_widths[c] = 120

        # Função auxiliar para texto dinâmico do rótulo
        def _label_for(col: str) -> str:
            return "Ocultar" if self._col_content_visible[col].get() else "Mostrar"

        # Função para atualizar textos dos rótulos
        def _update_toggle_labels():
            for col, parts in self._col_ctrls.items():
                parts["label"].config(text=_label_for(col))

        # Atualiza _on_toggle para incluir atualização de labels
        _original_on_toggle = _on_toggle

        def _on_toggle_with_labels(col: str):
            _original_on_toggle(col)
            _update_toggle_labels()

        # Cria os controles alinhados (um grupo por coluna)
        self._col_ctrls = {}  # col -> {"frame":..., "label":..., "check":...}

        for col in self._col_order:
            grp = tk.Frame(self.columns_align_bar, bd=0, highlightthickness=0)

            chk = tk.Checkbutton(
                grp,
                variable=self._col_content_visible[col],
                command=lambda c=col: _on_toggle_with_labels(c),
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=0,  # <- sem padding
                cursor="hand2",
                anchor="w",
            )
            chk.pack(side="left")

            lbl = ttk.Label(grp, text=_label_for(col))
            lbl.pack(side="left", padx=(0, 0))  # <- sem padding, totalmente colado

            grp.place(x=0, y=2, width=120, height=HEADER_CTRL_H - 4)
            self._col_ctrls[col] = {"frame": grp, "label": lbl, "check": chk}

        # Inicializa textos dos rótulos
        _update_toggle_labels()

        # Função de sincronização: alinha grupos com as colunas (usa bbox para precisão)
        def _sync_col_controls():
            try:
                self.columns_align_bar.update_idletasks()
                self.client_list.update_idletasks()

                # base X do Treeview em relação à barra (corrige deslocamento de janela)
                base_left = self.client_list.winfo_rootx() - self.columns_align_bar.winfo_rootx()

                # pegue o primeiro item visível para medir as colunas com bbox
                items = self.client_list.get_children()
                first_item = items[0] if items else None

                # Se não houver items, calcula posição acumulada manualmente
                cumulative_x = 0

                for col in self._col_order:
                    # largura e posição reais da coluna via bbox
                    bx = None  # inicializa explicitamente
                    if first_item:
                        bx = self.client_list.bbox(first_item, col)
                        if not bx:
                            # se bbox vier vazio, usa fallback acumulado
                            col_w = int(self.client_list.column(col, option="width"))  # pyright: ignore[reportArgumentType]
                            bx = (cumulative_x, 0, col_w, 0)
                            cumulative_x += col_w
                    else:
                        # fallback: calcula posição acumulada das colunas
                        col_w = int(self.client_list.column(col, option="width"))  # pyright: ignore[reportArgumentType]
                        bx = (cumulative_x, 0, col_w, 0)
                        cumulative_x += col_w

                    if not bx:
                        # se ainda assim vier vazio, pula
                        continue

                    col_x_rel, _, col_w, _ = bx
                    col_left = base_left + col_x_rel
                    col_right = col_left + col_w

                    # largura necessária do bloquinho = label + check + margens
                    parts = self._col_ctrls[col]
                    req_w = parts["label"].winfo_reqwidth() + 12 + 4  # label + checkbox (~12px) + margem (4px)
                    # limite por coluna
                    min_w, max_w = 70, 160
                    gw = max(min_w, min(max_w, min(req_w, col_w - 8)))

                    # centraliza dentro da coluna
                    gx = col_left + (col_w - gw) // 2
                    # não deixa vazar a borda
                    if gx < col_left + 2:
                        gx = col_left + 2
                    if gx + gw > col_right - 2:
                        gx = max(col_left + 2, col_right - gw - 2)

                    parts["frame"].place_configure(x=gx, y=2, width=gw, height=HEADER_CTRL_H - 4)

            except Exception:
                pass

            # mantém alinhado mesmo com resize/scroll
            self.after(120, _sync_col_controls)

        # Eventos que disparam a sync
        self.client_list.bind("<Configure>", lambda e: _sync_col_controls())

        # Se houver scrollbar horizontal dedicado, sincronize
        try:
            old_cmd = self.client_list.cget("xscrollcommand")

            def _xscroll_proxy(*args):
                if old_cmd:
                    try:
                        func = self.nametowidget(old_cmd.split()[0])
                        func.set(*args)
                    except Exception:
                        pass
                _sync_col_controls()

            self.client_list.configure(xscrollcommand=_xscroll_proxy)
        except Exception:
            pass

        # primeira sincronização
        _sync_col_controls()

        footer = create_footer(
            self,
            on_novo=lambda: self._invoke_safe(self.on_new),
            on_editar=lambda: self._invoke_safe(self.on_edit),
            on_subpastas=lambda: self._invoke_safe(self.on_open_subpastas),
            on_enviar=lambda: self._invoke_safe(self.on_upload),
            on_enviar_pasta=lambda: self._invoke_safe(self.on_upload_folder),
            on_lixeira=lambda: self._invoke_safe(self.on_open_lixeira),
        )
        footer.frame.pack(fill="x", padx=10, pady=10)
        self.btn_novo = footer.novo
        self.btn_editar = footer.editar
        self.btn_subpastas = footer.subpastas
        self.btn_enviar = footer.enviar
        self.menu_enviar = footer.enviar_menu
        self.btn_lixeira = footer.lixeira
        self._uploading_busy = False
        self._send_button_prev_text: Optional[str] = None
        self.btn_enviar.state(["disabled"])
        try:
            last_index = self.menu_enviar.index("end")
            if last_index is not None:
                for idx in range(last_index + 1):
                    self.menu_enviar.entryconfigure(idx, state="disabled")
        except Exception:
            pass

        def _refresh_send_state() -> None:
            has_sel = bool(self.tree.selection())
            if has_sel:
                self.btn_enviar.state(["!disabled"])
                self.menu_enviar.entryconfig(0, state="normal")
                self.menu_enviar.entryconfig(1, state="normal")
            else:
                self.btn_enviar.state(["disabled"])
                self.menu_enviar.entryconfig(0, state="disabled")
                self.menu_enviar.entryconfig(1, state="disabled")
            self._update_main_buttons_state()

        _refresh_send_state()
        self.tree.bind("<<TreeviewSelect>>", lambda _event: _refresh_send_state(), add="+")

        # UI do modo de seleção (oculto inicialmente)
        self._pick_banner_frame = tb.Frame(self, bootstyle="info")
        self._pick_label = tb.Label(
            self._pick_banner_frame,
            text="🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter",
            font=("", 10, "bold"),  # pyright: ignore[reportArgumentType]
            bootstyle="info-inverse",
        )
        self._pick_label.pack(side="left", padx=10, pady=5)

        btn_cancel_pick = tb.Button(
            self._pick_banner_frame,
            text="✕ Cancelar",
            bootstyle="danger-outline",
            command=self._cancel_pick,
        )
        btn_cancel_pick.pack(side="right", padx=10, pady=5)

        self.btn_select = tb.Button(
            self._pick_banner_frame,
            text="✓ Selecionar",
            command=self._confirm_pick,
            state="disabled",
            bootstyle="success",
        )
        self.btn_select.pack(side="right", padx=10, pady=5)

        # StatusBar removido - agora é global no main_window
        # Usar referências da App
        if self.app is not None:
            self.clients_count_var = getattr(self.app, "clients_count_var", None)
            self.status_var_dot = getattr(self.app, "status_var_dot", None)
            self.status_var_text = getattr(self.app, "status_var_text", None)
            self.status_dot = getattr(self.app, "status_dot", None)
            self.status_lbl = getattr(self.app, "status_lbl", None)
            setattr(self.app, "_main_frame_ref", self)

        self._update_main_buttons_state()

        # Inicia verificação periódica de conectividade
        self._start_connectivity_monitor()

    def set_uploading(self, busy: bool) -> None:
        """Disable upload actions while an upload job is running."""
        busy = bool(busy)
        if busy == self._uploading_busy:
            return

        self._uploading_busy = busy

        if busy:
            try:
                if hasattr(self, "btn_enviar") and self.btn_enviar:
                    self._send_button_prev_text = self.btn_enviar.cget("text")
                    self.btn_enviar.configure(text="Enviando…")
            except Exception:
                pass
        else:
            try:
                if hasattr(self, "btn_enviar") and self.btn_enviar and self._send_button_prev_text is not None:
                    self.btn_enviar.configure(text=self._send_button_prev_text)
            except Exception:
                pass
            self._send_button_prev_text = None

        self._update_main_buttons_state()

    def _start_connectivity_monitor(self) -> None:
        """
        Inicia monitoramento periódico da conectividade com Supabase.

        Sistema de 3 Estados:
        - ONLINE (🟢): Conectado e estável → Botões habilitados
        - INSTÁVEL (🟡): Conexão intermitente → Botões de envio bloqueados
        - OFFLINE (🔴): Sem conexão → Botões de envio bloqueados

        Atualiza o estado dos botões e o texto visual baseado no status.
        """

        def _check_and_update():
            try:
                # Obtém estado detalhado (online/unstable/offline)
                state, description = get_supabase_state()
                text, style, tooltip = get_cloud_status_for_ui()

                # Atualiza atributo interno para uso em outras partes
                if self.app is not None:
                    setattr(self.app, "_net_is_online", state == "online")
                    setattr(self.app, "_net_state", state)  # online/unstable/offline
                    setattr(self.app, "_net_description", description)

                # Atualiza estado dos botões
                self._update_main_buttons_state()

                # Atualiza texto do botão enviar baseado no status
                if hasattr(self, "btn_enviar") and not self._uploading_busy:
                    if state == "online":
                        self.btn_enviar.configure(text="Enviar Para SupaBase")
                    elif state == "unstable":
                        self.btn_enviar.configure(text="Envio suspenso – Conexão instável")
                    else:  # offline
                        self.btn_enviar.configure(text="Envio suspenso – Offline")

                # Atualiza indicador visual na UI (se existir)
                if hasattr(self.app, "status_var_text") and self.app.status_var_text:
                    try:
                        current_text = self.app.status_var_text.get()
                        # Atualiza apenas a parte da nuvem, preservando info do usuário
                        if "Nuvem:" in current_text:
                            parts = current_text.split("|")
                            parts[0] = f"Nuvem: {text}"
                            self.app.status_var_text.set(" | ".join(parts))
                        else:
                            # Se não tem info ainda, adiciona
                            self.app.status_var_text.set(f"Nuvem: {text}")
                    except Exception:
                        pass

                # Log apenas em mudanças de estado
                if not hasattr(self, "_last_cloud_state") or self._last_cloud_state != state:
                    log.info(
                        "Status da nuvem mudou: %s → %s (%s)",
                        getattr(self, "_last_cloud_state", "unknown"),
                        state.upper(),
                        description,
                    )
                    self._last_cloud_state = state

            except Exception as e:
                log.debug("Erro ao verificar conectividade: %s", e)

            # Reagenda para próxima verificação (a cada 5 segundos)
            try:
                self.after(5000, _check_and_update)
            except Exception:
                pass  # Widget foi destruído

        # Primeira verificação após 2 segundos (para dar tempo ao health checker iniciar)
        try:
            self.after(2000, _check_and_update)
        except Exception:
            pass

    def _row_dict_from_cliente(self, cliente: Any) -> dict:
        """Converte objeto cliente em dicionário de valores por coluna."""
        # Normaliza WhatsApp
        wa = normalize_br_whatsapp(str(getattr(cliente, "whatsapp", "") or getattr(cliente, "numero", "") or getattr(cliente, "telefone", "")))

        # Formata CNPJ
        cnpj_raw = str(getattr(cliente, "cnpj", "") or "")
        try:
            from src.utils.text_utils import format_cnpj

            cnpj_fmt = format_cnpj(cnpj_raw) or cnpj_raw
        except Exception:
            cnpj_fmt = cnpj_raw

        # Formata data
        updated_at = getattr(cliente, "ultima_alteracao", "") or getattr(cliente, "updated_at", "") or ""
        if updated_at:
            try:
                from src.app_utils import fmt_data

                updated_fmt = fmt_data(updated_at)
            except Exception:
                updated_fmt = str(updated_at)
        else:
            updated_fmt = ""

        by = (getattr(cliente, "ultima_por", "") or "").strip()
        initial = ""
        if by:
            aliases_raw = os.getenv("RC_INITIALS_MAP", "")
            alias = ""
            try:
                try:
                    mapping = json.loads(aliases_raw) if aliases_raw else {}
                except Exception:
                    mapping = {}
                if isinstance(mapping, dict):
                    alias = str(mapping.get(by, "") or "")
                if alias:
                    initial = (alias[:1] or "").upper()
                else:
                    from src.ui.hub.authors import _author_display_name as _author_name

                    display = _author_name(self, by)
                    initial = (display[:1] or by[:1] or "").upper()
            except Exception:
                initial = (by[:1] or "").upper()
        if updated_fmt and initial:
            updated_fmt = f"{updated_fmt} ({initial})"

        # Separa Status das Observações
        _obs_raw = str(getattr(cliente, "observacoes", "") or getattr(cliente, "obs", ""))
        _m = STATUS_PREFIX_RE.match(_obs_raw)
        _status = _m.group("st") if _m else ""
        _obs_body = STATUS_PREFIX_RE.sub("", _obs_raw, count=1).strip()

        row = {
            "ID": str(getattr(cliente, "id", "") or getattr(cliente, "pk", "") or getattr(cliente, "client_id", "")),
            "Razao Social": str(getattr(cliente, "razao_social", "") or getattr(cliente, "razao", "")),
            "CNPJ": cnpj_fmt,
            "Nome": str(getattr(cliente, "nome", "") or getattr(cliente, "contato", "")),
            "WhatsApp": wa["display"],
            "Observacoes": _obs_body,
            "Status": _status,
            "Ultima Alteracao": updated_fmt,
        }
        self._ensure_row_search_norm(row)
        return row

    def _row_values_masked(self, row_dict: dict) -> tuple:
        """Retorna tupla de valores aplicando máscara de visibilidade."""
        vals = []
        for col in self._col_order:
            v = row_dict.get(col, "")
            if not self._col_content_visible[col].get():
                v = ""  # esconde apenas conteúdo da célula
            vals.append(v)
        return tuple(vals)

    def _refresh_rows(self) -> None:
        """Re-renderiza linhas mantendo ordem e aplicando máscara de visibilidade."""
        items = self.client_list.get_children()
        if len(items) != len(self._current_clientes):
            # Se contagem não bate, reconstrói do zero
            self.client_list.delete(*items)
            for cli in self._current_clientes:
                row = self._row_dict_from_cliente(cli)
                self.client_list.insert("", "end", values=self._row_values_masked(row))
            return
        # Atualização in-place preservando posição
        for item_id, cli in zip(items, self._current_clientes):
            row = self._row_dict_from_cliente(cli)
            self.client_list.item(item_id, values=self._row_values_masked(row))

    def carregar(self) -> None:
        """Preenche a tabela de clientes."""
        order_label = self.var_ordem.get()
        search_term = self.var_busca.get().strip()
        column, reverse_after = self._resolve_order_preferences()
        log.info("Atualizando lista (busca='%s', ordem='%s')", search_term, order_label)

        # Busca os dados ANTES de limpar a lista (evita tela branca)
        try:
            clientes = search_clientes(search_term, column)
            if reverse_after:
                clientes = list(reversed(clientes))
        except Exception as exc:
            # Se falhar, mantém lista atual e apenas notifica
            log.warning("Falha ao carregar lista: %s", exc)
            messagebox.showerror("Erro", f"Falha ao carregar lista: {exc}", parent=self)
            return

        # Guarda lista completa e prepara filtros dinâmicos
        self._all_clientes = list(clientes)
        self._search_norm_cache.clear()

        try:
            self._populate_status_filter_options(self._all_clientes)
        except KeyError as exc:
            log.error("campo status ausente no dataset da lista: %s", exc)
            messagebox.showerror(
                "Erro",
                "Campo status ausente no dataset da lista.",
                parent=self,
            )
            return
        except Exception as exc:
            log.error("Falha ao preparar opções de status: %s", exc)

        self.apply_filters()

    def _sort_by(self, column: str) -> None:
        current = self.var_ordem.get()
        if column == "updated_at":
            new_value = "Ultima Alteracao (mais antiga)" if current == "Ultima Alteracao (mais recente)" else "Ultima Alteracao (mais recente)"
            self.var_ordem.set(new_value)
        elif column in ("razao_social", "cnpj", "nome"):
            mapping = {
                "razao_social": "Razao Social (A->Z)",
                "cnpj": "CNPJ (A->Z)",
                "nome": "Nome (A->Z)",
            }
            self.var_ordem.set(mapping[column])
        elif column == "id":
            new_value = "ID (9→1)" if current == "ID (1→9)" else "ID (1→9)"
            self.var_ordem.set(new_value)
        else:
            return
        self.carregar()

    def _get_selected_values(self) -> Optional[Sequence[Any]]:
        try:
            selection = self.client_list.selection()
        except Exception:
            return None
        if not selection:
            return None
        item_id = selection[0]
        try:
            return self.client_list.item(item_id, "values")
        except Exception:
            return None

    def _buscar(self, _event: Any | None = None) -> None:
        try:
            if self._buscar_after:
                self.after_cancel(self._buscar_after)
        except Exception:
            pass
        self._buscar_after = self.after(200, self.carregar)

    def _limpar_busca(self) -> None:
        self.var_busca.set("")
        self.var_status.set("Todos")
        self.carregar()

    def apply_filters(self, *_: Any) -> None:
        base = getattr(self, "_all_clientes", None) or []

        status_sel = (self.var_status.get() or "").strip().lower()
        raw_query = self.var_busca.get() if hasattr(self, "var_busca") else ""
        query_norm = normalize_search(raw_query)

        filtered: list[Any] = []
        try:
            for cli in base:
                row = self._row_dict_from_cliente(cli)
                if "Status" not in row:
                    raise KeyError("status")
                status_value = str(row.get("Status", "") or "").strip().lower()
                if status_sel and status_sel != "todos" and status_value != status_sel:
                    continue
                if query_norm:
                    norm_value = self._ensure_row_search_norm(row)
                    if query_norm not in norm_value:
                        continue
                filtered.append(cli)
        except KeyError:
            log.error("campo status ausente no dataset da lista durante filtragem")
            return

        filtered = self._sort_clientes(filtered)

        self._current_clientes = filtered
        self._render_clientes(filtered)

    def _ensure_row_search_norm(self, row: dict) -> str:
        norm = row.get("_search_norm", "")
        cache_key = str(row.get("ID", "") or "").strip()
        if not norm:
            norm = join_and_normalize(
                row.get("ID"),
                row.get("Razao Social"),
                row.get("CNPJ"),
                row.get("Nome"),
                row.get("WhatsApp"),
                row.get("Observacoes"),
                row.get("Status"),
            )
            row["_search_norm"] = norm
        if cache_key:
            self._search_norm_cache[cache_key] = norm
        return norm

    def _populate_status_filter_options(self, clientes: Sequence[Any]) -> None:
        if not clientes:
            try:
                self.status_filter.configure(values=["Todos"])
            except Exception:
                pass
            self.var_status.set("Todos")
            return

        sample_row = self._row_dict_from_cliente(clientes[0])
        if "Status" not in sample_row:
            raise KeyError("status")

        seen: dict[str, str] = {}
        for cli in clientes:
            row = self._row_dict_from_cliente(cli)
            status_raw = str(row.get("Status", "") or "").strip()
            if not status_raw:
                continue
            key = status_raw.lower()
            if key not in seen:
                seen[key] = status_raw

        choices = ["Todos"] + sorted(seen.values(), key=lambda s: s.lower())
        try:
            self.status_filter.configure(values=choices)
        except Exception:
            pass

        current = (self.var_status.get() or "").strip()
        normalized_current = current.lower()
        available_map = {choice.lower(): choice for choice in choices}
        if normalized_current in available_map:
            resolved = available_map[normalized_current]
            if resolved != current:
                self.var_status.set(resolved)
        else:
            self.var_status.set("Todos")

    @staticmethod
    def _key_nulls_last(value: object, transform: Callable[[str], Any] = str) -> tuple[bool, Any]:
        s = "" if value is None else str(value).strip()
        return (s == "", transform(s))

    @staticmethod
    def _only_digits(s: str) -> str:
        return "".join(ch for ch in str(s) if ch.isdigit())

    @classmethod
    def _key_name(cls, cliente: Any) -> tuple[bool, Any]:
        value = getattr(cliente, "razao_social", None) or getattr(cliente, "razao", None)
        return cls._key_nulls_last(value, lambda text: text.casefold())

    @classmethod
    def _key_nome(cls, cliente: Any) -> tuple[bool, Any]:
        value = getattr(cliente, "nome", None) or getattr(cliente, "contato", None)
        return cls._key_nulls_last(value, lambda text: text.casefold())

    @classmethod
    def _key_cnpj(cls, cliente: Any) -> tuple[bool, str]:
        raw = getattr(cliente, "cnpj", None)
        digits = "" if raw is None else cls._only_digits(raw)
        return (digits == "", digits)

    @staticmethod
    def _key_id(cliente: Any) -> tuple[bool, int]:
        raw = getattr(cliente, "id", None) or getattr(cliente, "pk", None) or getattr(cliente, "client_id", None)
        try:
            value = int(str(raw).strip())
            return (False, value)
        except (TypeError, ValueError):
            return (True, 0)

    def _sort_clientes(self, clientes: list[Any]) -> list[Any]:
        if not clientes:
            return []

        column, reverse_after = self._resolve_order_preferences()
        ordered = list(clientes)
        if not column:
            return ordered

        try:
            if column == "razao_social":
                non_empty: list[tuple[Any, Any]] = []
                empties: list[Any] = []
                for cli in ordered:
                    is_empty, key = self._key_name(cli)
                    if is_empty:
                        empties.append(cli)
                    else:
                        non_empty.append((key, cli))
                non_empty.sort(key=lambda item: item[0], reverse=reverse_after)
                ordered = [cli for _, cli in non_empty]
                ordered.extend(empties)
                return ordered
            if column == "nome":
                non_empty: list[tuple[Any, Any]] = []
                empties: list[Any] = []
                for cli in ordered:
                    is_empty, key = self._key_nome(cli)
                    if is_empty:
                        empties.append(cli)
                    else:
                        non_empty.append((key, cli))
                non_empty.sort(key=lambda item: item[0], reverse=reverse_after)
                ordered = [cli for _, cli in non_empty]
                ordered.extend(empties)
                return ordered
            if column == "cnpj":
                non_empty: list[tuple[Any, Any]] = []
                empties: list[Any] = []
                for cli in ordered:
                    is_empty, key = self._key_cnpj(cli)
                    if is_empty:
                        empties.append(cli)
                    else:
                        non_empty.append((key, cli))
                non_empty.sort(key=lambda item: item[0], reverse=reverse_after)
                ordered = [cli for _, cli in non_empty]
                ordered.extend(empties)
                return ordered
            if column == "id":
                numeric: list[tuple[int, Any]] = []
                invalid: list[Any] = []
                for cli in ordered:
                    is_invalid, value = self._key_id(cli)
                    if is_invalid:
                        invalid.append(cli)
                    else:
                        numeric.append((value, cli))
                numeric.sort(key=lambda item: item[0], reverse=reverse_after)
                ordered = [cli for _, cli in numeric]
                ordered.extend(invalid)
                return ordered
        except Exception as exc:
            log.debug("Falha ao ordenar clientes durante filtros: %s", exc)
            return list(clientes)

        return ordered

    def _render_clientes(self, clientes: Sequence[Any]) -> None:
        try:
            self.client_list.delete(*self.client_list.get_children())
        except Exception:
            pass

        for cli in clientes:
            row = self._row_dict_from_cliente(cli)
            obs_txt = row.get("Observacoes", "").strip()
            tags = ("has_obs",) if obs_txt else ()
            self.client_list.insert("", "end", values=self._row_values_masked(row), tags=tags)

        count = len(clientes) if isinstance(clientes, (list, tuple)) else len(self.client_list.get_children())
        self._set_count_text(count)
        self._update_main_buttons_state()

        try:
            self.after(50, lambda: None)
        except Exception:
            pass

    def _ensure_status_menu(self) -> tk.Menu:
        menu = self.status_menu
        if menu is None:
            menu = tk.Menu(self, tearoff=0)
            self.status_menu = menu
        menu.configure(postcommand=lambda: _build_status_menu(menu, self._on_status_pick))
        return menu

    def _show_status_menu(self, row_id: str, cliente_id: int, event: Any) -> None:
        menu = self._ensure_status_menu()
        self.client_list.selection_set(row_id)
        self.client_list.focus(row_id)
        self._status_menu_row = row_id
        self._status_menu_cliente = cliente_id
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            if self._status_menu_row == row_id:
                self._status_menu_row = None
            if self._status_menu_cliente == cliente_id:
                self._status_menu_cliente = None

    def _on_status_menu(self, event: Any) -> None:
        tv = getattr(self, "tree", self.client_list)
        row_id = tv.identify_row(event.y)
        if not row_id:
            return
        tv.selection_set(row_id)
        tv.focus(row_id)
        try:
            values = tv.item(row_id, "values")
            idx = self._col_order.index("ID") if "ID" in self._col_order else 0
            cliente_id = int(values[idx])
        except Exception:
            return
        self._show_status_menu(row_id, cliente_id, event)

    def _on_status_pick(self, label: str) -> None:
        self._set_status(label)

    def _set_status(self, label: str) -> None:
        target_id = self._status_menu_cliente
        if target_id is None:
            try:
                selection = self.client_list.selection()
                if not selection:
                    self._status_menu_cliente = None
                    self._status_menu_row = None
                    return
                values = self.client_list.item(selection[0], "values")
                idx = self._col_order.index("ID") if "ID" in self._col_order else 0
                target_id = int(values[idx])
            except Exception:
                self._status_menu_cliente = None
                self._status_menu_row = None
                return
        try:
            self._apply_status_for(int(target_id), label)
        finally:
            self._status_menu_cliente = None
            self._status_menu_row = None

    def _on_click(self, event: Any) -> None:
        """Abre WhatsApp na col #5 e menu de Status na col #7."""
        item = self.client_list.identify_row(event.y)
        col = self.client_list.identify_column(event.x)
        if not item:
            return

        # Menu de Status ao clicar na coluna #7
        if col == "#7":
            try:
                vals = self.client_list.item(item, "values")
                id_index = self._col_order.index("ID") if "ID" in self._col_order else 0
                cliente_id = int(vals[id_index])
            except Exception:
                return

            self._show_status_menu(item, cliente_id, event)
            return

        # WhatsApp permanece na coluna #5
        if col != "#5":
            return
        try:
            cell = self.client_list.item(item, "values")[4] or ""  # índice 4 = 5ª coluna (WhatsApp)
        except Exception:
            cell = ""

        # Usa normalize_br_whatsapp para obter formato e164
        wa = normalize_br_whatsapp(str(cell))
        if not wa["e164"]:
            return

        msg = "Olá, tudo bem?"
        webbrowser.open_new_tab(f"https://wa.me/{wa['e164']}?text={urllib.parse.quote(msg)}")

    def _apply_status_for(self, cliente_id: int, chosen: str) -> None:
        """Atualiza o [STATUS] no campo Observações e recarrega a grade."""
        try:
            cli = get_cliente_by_id(cliente_id)
            if not cli:
                return
            old_obs = (getattr(cli, "obs", None) or getattr(cli, "observacoes", None) or "").strip()
            body = STATUS_PREFIX_RE.sub("", old_obs, count=1).strip()
            new_obs = f"[{chosen}] {body}".strip() if chosen else body
            update_status_only(cliente_id=cliente_id, obs=new_obs)
            self.carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar status: {e}", parent=self)

    def _update_main_buttons_state(self, *_: Any) -> None:
        """
        Atualiza o estado dos botões principais baseado em:
        - Seleção de cliente
        - Status de conectividade com Supabase (Online/Instável/Offline)

        Comportamento:
        - ONLINE: Todos os botões funcionam normalmente
        - INSTÁVEL ou OFFLINE: Botões de envio ficam desabilitados
        - Operações locais (visualizar, buscar) continuam disponíveis
        """
        try:
            has_sel = bool(self.client_list.selection())
        except Exception:
            has_sel = False

        # Obtém estado detalhado da nuvem
        state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]
        online = state == "online"  # Somente "online" permite envio

        allow_send = has_sel and online and not self._uploading_busy
        try:
            # Botões que dependem de conexão E seleção
            self.btn_editar.configure(state=("normal" if (has_sel and online) else "disabled"))
            self.btn_subpastas.configure(state=("normal" if (has_sel and online) else "disabled"))
            if allow_send:
                self.btn_enviar.state(["!disabled"])
            else:
                self.btn_enviar.state(["disabled"])
            if hasattr(self, "menu_enviar") and self.menu_enviar is not None:
                try:
                    last_index = self.menu_enviar.index("end")
                    if last_index is not None:
                        entry_state = "normal" if allow_send else "disabled"
                        for idx in range(last_index + 1):
                            self.menu_enviar.entryconfigure(idx, state=entry_state)
                except Exception:
                    pass

            # Botões que dependem apenas de conexão
            self.btn_novo.configure(state=("normal" if online else "disabled"))
            self.btn_lixeira.configure(state=("normal" if online else "disabled"))

            # Botão de seleção (modo pick) - não depende de conexão
            if self._pick_mode and hasattr(self, "btn_select"):
                self.btn_select.configure(state=("normal" if has_sel else "disabled"))
        except Exception as e:
            log.debug("Erro ao atualizar estado dos botões: %s", e)

    def _resolve_order_preferences(self) -> Tuple[Optional[str], bool]:
        label = self.var_ordem.get()
        return self._order_choices.get(label, (None, False))

    def _set_count_text(self, count: int) -> None:
        try:
            text = "1 cliente" if count == 1 else f"{count} clientes"
            self.clients_count_var.set(text)
        except Exception:
            pass

    # =========================================================================
    # Modo de seleção para integração com Senhas
    # =========================================================================

    def start_pick(self, on_pick, return_to=None):
        """
        Coloca a tela de Clientes em modo seleção.

        Args:
            on_pick: callback(dict com cliente) chamado ao confirmar
            return_to: callable opcional que navega de volta
        """
        self._pick_mode = True
        self._on_pick = on_pick
        self._return_to = return_to
        # Mostrar banner/barra e configurar UI
        self._ensure_pick_ui(True)
        # Recarregar lista (já lista os clientes da ORG)
        self.carregar()

    def _ensure_pick_ui(self, enable: bool):
        """Exibe ou oculta UI do modo seleção."""
        if enable:
            # Exibir banner
            if hasattr(self, "_pick_banner_frame"):
                self._pick_banner_frame.pack(fill="x", padx=10, pady=(0, 10), before=self.client_list)

            # Ocultar botões CRUD
            crud_buttons = [
                self.btn_novo,
                self.btn_editar,
                self.btn_subpastas,
                self.btn_enviar,
                self.btn_lixeira,
            ]

            for btn in crud_buttons:
                if btn and btn.winfo_ismapped():
                    # Salvar estado do geometry manager
                    info = btn.pack_info() if btn.winfo_manager() == "pack" else None
                    self._saved_toolbar_state[btn] = info
                    btn.pack_forget()

            # Adicionar bindings de teclado para modo seleção
            # Remover bindings anteriores de duplo-clique para evitar conflito
            self.client_list.unbind("<Double-1>")
            self.client_list.bind("<Double-1>", self._confirm_pick)
            self.client_list.bind("<Return>", self._confirm_pick)
            self.bind_all("<Escape>", self._cancel_pick)
        else:
            # Ocultar banner
            if hasattr(self, "_pick_banner_frame"):
                self._pick_banner_frame.pack_forget()

            # Restaurar botões CRUD
            for btn, pack_info in self._saved_toolbar_state.items():
                if pack_info:
                    btn.pack(**pack_info)
            self._saved_toolbar_state.clear()

            # Remover bindings de modo seleção e restaurar bindings normais
            self.client_list.unbind("<Double-1>")
            self.client_list.unbind("<Return>")
            self.unbind_all("<Escape>")
            # Restaurar binding normal de edição via duplo-clique
            self.client_list.bind("<Double-1>", lambda _event: self._invoke_safe(self.on_edit))

    def _get_selected_client_dict(self) -> dict | None:
        """Retorna dict com dados do cliente selecionado."""
        sel = self.client_list.selection()
        if not sel:
            return None

        item_id = sel[0]
        values = self.client_list.item(item_id, "values")
        if not values or len(values) < 3:
            return None

        # Colunas: ID, Razao Social, CNPJ, Nome, WhatsApp, Observacoes, Ultima Alteracao
        try:
            return {
                "id": values[0],
                "razao_social": values[1],
                "cnpj": values[2],
            }
        except Exception as e:
            log.warning(f"Erro ao obter dados do cliente: {e}")
            return None

    def _cancel_pick(self, *_):
        """Cancela modo de seleção sem escolher cliente."""
        if not self._pick_mode:
            return

        # Sair do modo seleção
        self._pick_mode = False
        self._on_pick = None
        self._ensure_pick_ui(False)

        # Voltar para tela anterior
        if callable(self._return_to):
            self._return_to()

    def _confirm_pick(self, *_):
        """Confirma seleção e volta para tela de Senhas."""
        if not self._pick_mode:
            return

        info = self._get_selected_client_dict()
        if not info:
            messagebox.showwarning("Atenção", "Selecione um cliente primeiro.", parent=self)
            return

        # Normalizar CNPJ com máscara
        cnpj_raw = info.get("cnpj", "")
        info["cnpj"] = self._format_cnpj_for_pick(cnpj_raw)

        try:
            if callable(self._on_pick):
                self._on_pick(info)
        finally:
            # Sair do modo seleção
            self._pick_mode = False
            self._on_pick = None
            self._ensure_pick_ui(False)
            # Voltar para tela de Senhas
            if callable(self._return_to):
                self._return_to()

    @staticmethod
    def _format_cnpj_for_pick(cnpj: str) -> str:
        """Formata CNPJ para exibição (##.###.###/####-##)."""
        digits = re.sub(r"\D", "", cnpj or "")
        if len(digits) != 14:
            return cnpj or ""
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"

    @staticmethod
    def _invoke(callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            callback()

    def _invoke_safe(self, callback: Optional[Callable[[], None]]) -> None:
        """Invoca callback apenas se NÃO estiver em modo seleção."""
        if getattr(self, "_pick_mode", False):
            return
        if callable(callback):
            callback()
