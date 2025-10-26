# -*- coding: utf-8 -*-
"""Main screen frame extracted from app_gui (clients list)."""

from __future__ import annotations

import logging
import re
import urllib.parse
import webbrowser
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import ttkbootstrap as tb
except Exception:
    tb = ttk  # fallback


from src.core.search import search_clientes
from src.utils.phone_utils import normalize_br_whatsapp
from src.utils.prefs import load_columns_visibility, save_columns_visibility
from src.ui.components import (
    create_clients_treeview,
    create_footer_buttons as create_footer,
    create_search_controls,
)
from infra.supabase_client import get_supabase_state, get_cloud_status_for_ui
from src.core.db_manager import get_cliente_by_id, update_cliente

log = logging.getLogger("app_gui")

DEFAULT_ORDER_LABEL = "Razão Social (A->Z)"
ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = {
    "Razão Social (A->Z)": ("razao_social", False),
    "CNPJ (A->Z)": ("cnpj", False),
    "Nome (A->Z)": ("nome", False),
    "Última Alteração (mais recente)": ("ultima_alteracao", False),
    "Última Alteração (mais antiga)": ("ultima_alteracao", True),
}

STATUS_CHOICES = [
    "Novo lead",
    "Sem resposta",
    "Aguardando documento",
    "Aguardando pagamento",
    "Em cadastro",
    "Finalizado",
    "Follow-up hoje",
    "Follow-up amanhã",
]
STATUS_PREFIX_RE = re.compile(r'^\s*\[(?P<st>[^\]]+)\]\s*')

__all__ = ["MainScreenFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]


class MainScreenFrame(tb.Frame):
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
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self.app = app
        self.on_new = on_new
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_upload = on_upload
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

        search_controls = create_search_controls(
            self,
            order_choices=list(self._order_choices.keys()),
            default_order=self._default_order_label,
            on_search=self._buscar,
            on_clear=self._limpar_busca,
            on_order_change=self.carregar,
        )
        search_controls.frame.pack(fill="x", padx=10, pady=10)
        self.var_busca = search_controls.search_var
        self.var_ordem = search_controls.order_var
        
        # --- Divisória entre filtros e a faixa de controles de colunas
        self._cols_separator = ttk.Separator(self, orient="horizontal")
        self._cols_separator.pack(side="top", fill="x", padx=10, pady=(6, 4))
        
        # --- Faixa alinhada às colunas (fora do Treeview, mas sincronizada)
        HEADER_CTRL_H = 26   # altura da faixa dos controles
        self.columns_align_bar = tk.Frame(self, height=HEADER_CTRL_H)
        self.columns_align_bar.pack(side="top", fill="x", padx=10)
        
        # IDs/ordem exatos das colunas
        self._col_order = ("ID", "Razao Social", "CNPJ", "Nome",
                           "WhatsApp", "Observacoes", "Status", "Ultima Alteracao")
        
        # Estado por usuário (mantemos persistência)
        def _user_key():
            return getattr(self, "current_user_email", None) or getattr(self, "status_user_email", None) or "default"
        self._user_key = _user_key()
        _saved = load_columns_visibility(self._user_key)
        self._col_content_visible = {c: tk.BooleanVar(value=_saved.get(c, True)) for c in self._col_order}
        
        # Lista atual de clientes (para refresh)
        self._current_clientes = []
        
        # Funções auxiliares (nested functions)
        def _persist_visibility():
            save_columns_visibility(self._user_key, {k: v.get() for k, v in self._col_content_visible.items()})
        
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
        
        # Configura headings sem sobrescrever os textos vindos do componente
        self.client_list.configure(displaycolumns=self._col_order)
        for col in self._col_order:
            try:
                # mantém o texto atual (com acento) se já veio do componente
                cur = self.client_list.heading(col, "text")
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
                self._col_widths[c] = self.client_list.column(c, "width")
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
        def _on_toggle(col: str):
            _original_on_toggle(col)
            _update_toggle_labels()
        
        # Cria os controles alinhados (um grupo por coluna)
        self._col_ctrls = {}  # col -> {"frame":..., "label":..., "check":...}
        
        for col in self._col_order:
            grp = tk.Frame(self.columns_align_bar, bd=0, highlightthickness=0)
            
            chk = tk.Checkbutton(
                grp,
                variable=self._col_content_visible[col],
                command=lambda c=col: _on_toggle(c),
                bd=0, highlightthickness=0, padx=0, pady=0,  # <- sem padding
                cursor="hand2", anchor="w"
            )
            chk.pack(side="left")
            
            lbl = ttk.Label(grp, text=_label_for(col))
            lbl.pack(side="left", padx=(0, 0))  # <- sem padding, totalmente colado
            
            grp.place(x=0, y=2, width=120, height=HEADER_CTRL_H-4)
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
                    if first_item:
                        bx = self.client_list.bbox(first_item, col)
                        if not bx:
                            # se bbox vier vazio, usa fallback acumulado
                            col_w = int(self.client_list.column(col, "width"))
                            bx = (cumulative_x, 0, col_w, 0)
                            cumulative_x += col_w
                    else:
                        # fallback: calcula posição acumulada das colunas
                        col_w = int(self.client_list.column(col, "width"))
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
            on_lixeira=lambda: self._invoke_safe(self.on_open_lixeira),
        )
        footer.frame.pack(fill="x", padx=10, pady=10)
        self.btn_novo = footer.novo
        self.btn_editar = footer.editar
        self.btn_subpastas = footer.subpastas
        self.btn_enviar = footer.enviar
        self.btn_lixeira = footer.lixeira
        
        # UI do modo de seleção (oculto inicialmente)
        self._pick_banner_frame = tb.Frame(self, bootstyle="info")
        self._pick_label = tb.Label(
            self._pick_banner_frame,
            text="🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter",
            font=("", 10, "bold"),
            bootstyle="info-inverse"
        )
        self._pick_label.pack(side="left", padx=10, pady=5)
        
        btn_cancel_pick = tb.Button(
            self._pick_banner_frame,
            text="✕ Cancelar",
            bootstyle="danger-outline",
            command=self._cancel_pick
        )
        btn_cancel_pick.pack(side="right", padx=10, pady=5)
        
        self.btn_select = tb.Button(
            self._pick_banner_frame,
            text="✓ Selecionar",
            command=self._confirm_pick,
            state="disabled",
            bootstyle="success"
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
                if hasattr(self, "btn_enviar"):
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
                    log.info("Status da nuvem mudou: %s → %s (%s)", 
                            getattr(self, "_last_cloud_state", "unknown"), 
                            state.upper(), 
                            description)
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
        wa = normalize_br_whatsapp(
            str(
                getattr(cliente, "whatsapp", "") 
                or getattr(cliente, "numero", "") 
                or getattr(cliente, "telefone", "")
            )
        )
        
        # Formata CNPJ
        cnpj_raw = str(getattr(cliente, "cnpj", "") or "")
        try:
            from src.utils.text_utils import format_cnpj
            cnpj_fmt = format_cnpj(cnpj_raw) or cnpj_raw
        except Exception:
            cnpj_fmt = cnpj_raw
        
        # Formata data
        updated_at = getattr(cliente, "updated_at", "") or getattr(cliente, "ultima_alteracao", "")
        if updated_at:
            try:
                from src.app_utils import fmt_data
                updated_fmt = fmt_data(updated_at)
            except Exception:
                updated_fmt = str(updated_at)
        else:
            updated_fmt = ""
        
        # Separa Status das Observações
        _obs_raw = str(getattr(cliente, "observacoes", "") or getattr(cliente, "obs", ""))
        _m = STATUS_PREFIX_RE.match(_obs_raw)
        _status = _m.group("st") if _m else ""
        _obs_body = STATUS_PREFIX_RE.sub("", _obs_raw, count=1).strip()
        
        return {
            "ID": str(getattr(cliente, "id", "") or getattr(cliente, "pk", "") or getattr(cliente, "client_id", "")),
            "Razao Social": str(getattr(cliente, "razao_social", "") or getattr(cliente, "razao", "")),
            "CNPJ": cnpj_fmt,
            "Nome": str(getattr(cliente, "nome", "") or getattr(cliente, "contato", "")),
            "WhatsApp": wa["display"],
            "Observacoes": _obs_body,
            "Status": _status,
            "Ultima Alteracao": updated_fmt,
        }
    
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

        # Guarda lista atual de clientes
        self._current_clientes = clientes
        
        # Agora que temos os dados, limpa e repopula rapidamente
        try:
            self.client_list.delete(*self.client_list.get_children())
        except Exception:
            pass

        # Popula usando os novos métodos
        for cli in clientes:
            row = self._row_dict_from_cliente(cli)
            obs_txt = row.get("Observacoes", "").strip()
            tags = ("has_obs",) if obs_txt else ()
            self.client_list.insert("", "end", values=self._row_values_masked(row), tags=tags)

        count = (
            len(clientes)
            if isinstance(clientes, (list, tuple))
            else len(self.client_list.get_children())
        )
        self._set_count_text(count)
        self._update_main_buttons_state()
        
        # Força sincronização dos controles após carregar
        self.after(50, lambda: None)  # Dummy para garantir que _sync_col_controls já está agendado

    def _sort_by(self, column: str) -> None:
        current = self.var_ordem.get()
        if column == "updated_at":
            new_value = (
                "Ultima Alteracao (mais antiga)"
                if current == "Ultima Alteracao (mais recente)"
                else "Ultima Alteracao (mais recente)"
            )
            self.var_ordem.set(new_value)
        elif column in ("razao_social", "cnpj", "nome"):
            mapping = {
                "razao_social": "Razao Social (A->Z)",
                "cnpj": "CNPJ (A->Z)",
                "nome": "Nome (A->Z)",
            }
            self.var_ordem.set(mapping[column])
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
        self.carregar()

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

            menu = tk.Menu(self, tearoff=0)
            for s in STATUS_CHOICES:
                menu.add_command(label=s, command=lambda _s=s: self._apply_status_for(cliente_id, _s))
            menu.add_separator()
            menu.add_command(label="Limpar", command=lambda: self._apply_status_for(cliente_id, ""))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
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
        webbrowser.open_new_tab(
            f"https://wa.me/{wa['e164']}?text={urllib.parse.quote(msg)}"
        )

    def _apply_status_for(self, cliente_id: int, chosen: str) -> None:
        """Atualiza o [STATUS] no campo Observações e recarrega a grade."""
        try:
            cli = get_cliente_by_id(cliente_id)
            if not cli:
                return
            old_obs = (getattr(cli, "obs", None) or getattr(cli, "observacoes", None) or "").strip()
            body = STATUS_PREFIX_RE.sub("", old_obs, count=1).strip()
            new_obs = (f"[{chosen}] {body}".strip() if chosen else body)
            update_cliente(
                cliente_id=cliente_id,
                numero=str(getattr(cli, "numero", "") or getattr(cli, "whatsapp", "") or getattr(cli, "telefone", "") or ""),
                nome=str(getattr(cli, "nome", "") or ""),
                razao_social=str(getattr(cli, "razao_social", "") or getattr(cli, "razao", "") or ""),
                cnpj=str(getattr(cli, "cnpj", "") or ""),
                obs=new_obs,
            )
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
        state, _ = get_supabase_state()
        online = (state == "online")  # Somente "online" permite envio
        
        try:
            # Botões que dependem de conexão E seleção
            self.btn_editar.configure(
                state=("normal" if (has_sel and online) else "disabled")
            )
            self.btn_subpastas.configure(
                state=("normal" if (has_sel and online) else "disabled")
            )
            self.btn_enviar.configure(
                state=("normal" if (has_sel and online) else "disabled")
            )
            
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
                self.btn_lixeira
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
