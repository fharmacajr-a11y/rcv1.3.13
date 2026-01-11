# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false, reportUntypedBaseClass=false, reportPrivateUsage=false

"""Main screen dataflow - Carregamento, filtros e dataflow.

Responsável por carregamento, filtros, dataflow e integração com o controller.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Sequence

from src.infra.supabase_client import get_supabase_state
from src.modules.clientes.controllers.connectivity_state_manager import (
    ConnectivityRawInput,
)
from src.modules.clientes.controllers.rendering_adapter import (
    build_rendering_context_from_ui,
    build_row_tags,
    build_row_values,
)
from src.modules.clientes.service import (
    fetch_cliente_by_id,
    update_cliente_status_and_observacoes,
)
from src.modules.clientes.viewmodel import ClienteRow, ClientesViewModelError
from src.modules.clientes.views.main_screen_controller import (
    compute_button_states,
    compute_count_summary,
    compute_filtered_and_ordered,
    decide_status_change,
    FilterOrderInput,
    MainScreenComputedLike,
)
from src.modules.clientes.views.main_screen_helpers import (
    ORDER_LABEL_CNPJ,
    ORDER_LABEL_ID_ASC,
    ORDER_LABEL_ID_DESC,
    ORDER_LABEL_NOME,
    ORDER_LABEL_RAZAO,
    ORDER_LABEL_UPDATED_OLD,
    ORDER_LABEL_UPDATED_RECENT,
    build_filter_choices_with_all_option,
    normalize_order_label,
    resolve_filter_choice_from_options,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger("app_gui")

__all__ = ["MainScreenDataflowMixin"]


class MainScreenDataflowMixin:
    """Mixin para carregamento, filtros e dataflow da main screen."""

    # Thread pool compartilhado para carregamento assíncrono (1 worker apenas)
    _load_executor: ThreadPoolExecutor | None = None
    _load_seq: int = 0
    _load_inflight: bool = False

    def carregar(self) -> None:
        """Preenche a tabela de clientes (versão síncrona - legado).

        NOTA: Preferir carregar_async() para evitar travamento da UI.
        """
        t0 = time.perf_counter()

        order_label_raw = (
            self.var_ordem.get()
        )  # pyright: ignore[reportAttributeAccessIssue]
        order_label = normalize_order_label(order_label_raw)
        if order_label != order_label_raw:
            self.var_ordem.set(
                order_label
            )  # pyright: ignore[reportAttributeAccessIssue]

        search_term = (
            self.var_busca.get().strip()
        )  # pyright: ignore[reportAttributeAccessIssue]

        log.info("Atualizando lista (busca='%s', ordem='%s')", search_term, order_label)

        # ViewModel apenas carrega dados brutos do backend
        t_fetch = time.perf_counter()
        try:
            self._vm.refresh_from_service()  # pyright: ignore[reportAttributeAccessIssue]
        except ClientesViewModelError as exc:
            log.warning("Falha ao carregar lista: %s", exc)
            messagebox.showerror(
                "Erro", f"Falha ao carregar lista: {exc}", parent=self
            )  # pyright: ignore[reportArgumentType]
            return
        fetch_time = time.perf_counter() - t_fetch

        # Atualizar opções de filtro de status (dinâmico baseado nos dados)
        self._populate_status_filter_options()

        # Usar controller para aplicar filtros/ordenação
        t_render = time.perf_counter()
        self._refresh_with_controller()
        render_time = time.perf_counter() - t_render

        total_time = time.perf_counter() - t0
        raw_count = len(
            self._vm._clientes_raw
        )  # pyright: ignore[reportPrivateUsage,reportAttributeAccessIssue]
        rows_count = len(
            self._current_rows
        )  # pyright: ignore[reportAttributeAccessIssue]

        log.info(
            "Clientes: perf fetch=%.3fs render=%.3fs total=%.3fs raw=%d rows=%d",
            fetch_time,
            render_time,
            total_time,
            raw_count,
            rows_count,
        )

    def carregar_async(self, force: bool = False) -> None:
        """Carrega lista de clientes de forma assíncrona (sem travar UI).

        Args:
            force: Se True, força recarga mesmo se já houver uma em andamento
        """
        # Prevenir múltiplas cargas simultâneas
        if (
            self._load_inflight and not force
        ):  # pyright: ignore[reportAttributeAccessIssue]
            log.debug("Carregar_async: carga já em andamento, ignorando")
            return

        # Incrementar sequência para invalidar cargas anteriores
        self._load_seq += 1  # pyright: ignore[reportAttributeAccessIssue]
        current_seq = self._load_seq  # pyright: ignore[reportAttributeAccessIssue]
        self._load_inflight = True  # pyright: ignore[reportAttributeAccessIssue]

        # Capturar parâmetros de UI no main thread
        order_label_raw = (
            self.var_ordem.get()
        )  # pyright: ignore[reportAttributeAccessIssue]
        order_label = normalize_order_label(order_label_raw)
        if order_label != order_label_raw:
            self.var_ordem.set(
                order_label
            )  # pyright: ignore[reportAttributeAccessIssue]

        search_term = (
            self.var_busca.get().strip()
        )  # pyright: ignore[reportAttributeAccessIssue]

        log.info(
            "Iniciando carga assíncrona (seq=%d, busca='%s', ordem='%s')",
            current_seq,
            search_term,
            order_label,
        )

        # Opcional: Desabilitar botões durante carga
        self._set_loading_state(True)

        # Criar executor se não existir
        if MainScreenDataflowMixin._load_executor is None:
            MainScreenDataflowMixin._load_executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="clientes_load"
            )

        # Função que roda em background (NÃO toca em Tk)
        def _fetch_data() -> tuple[list[Any], float] | tuple[None, float]:
            """Busca dados em background - SEM tocar em widgets Tk."""
            t0 = time.perf_counter()
            try:
                # Importar service aqui para evitar circular imports
                from src.core.search import search_clientes

                # Buscar dados do serviço (materialize list para não depender de cursor)
                clientes_raw = list(search_clientes("", None))
                fetch_time = time.perf_counter() - t0
                return clientes_raw, fetch_time
            except Exception:
                log.exception(
                    "Erro ao buscar clientes em background (seq=%d)", current_seq
                )
                fetch_time = time.perf_counter() - t0
                return None, fetch_time

        # Função que roda no main thread após o fetch
        def _apply_loaded(
            clientes_result: tuple[list[Any], float] | tuple[None, float]
        ) -> None:
            """Aplica dados carregados na UI (main thread)."""
            clientes_raw, fetch_time = clientes_result

            # Verificar se ainda é válido
            if not self.winfo_exists():  # pyright: ignore[reportAttributeAccessIssue]
                log.debug(
                    "Frame destruído, ignorando resultado de carga (seq=%d)",
                    current_seq,
                )
                self._load_inflight = (
                    False  # pyright: ignore[reportAttributeAccessIssue]
                )
                return

            if (
                current_seq != self._load_seq
            ):  # pyright: ignore[reportAttributeAccessIssue]
                log.debug(
                    "Carga obsoleta (seq=%d != atual %d), ignorando",
                    current_seq,
                    self._load_seq,
                )  # pyright: ignore[reportAttributeAccessIssue]
                self._load_inflight = (
                    False  # pyright: ignore[reportAttributeAccessIssue]
                )
                return

            t_render = time.perf_counter()

            # Erro no fetch
            if clientes_raw is None:
                self._load_inflight = (
                    False  # pyright: ignore[reportAttributeAccessIssue]
                )
                self._set_loading_state(False)
                messagebox.showerror(
                    "Erro", "Falha ao carregar lista de clientes", parent=self
                )  # pyright: ignore[reportArgumentType]
                return

            # Aplicar dados no ViewModel (sem buscar rede)
            try:
                self._vm.load_from_iterable(
                    clientes_raw
                )  # pyright: ignore[reportAttributeAccessIssue]
            except Exception as exc:
                log.exception("Erro ao aplicar dados no ViewModel")
                self._load_inflight = (
                    False  # pyright: ignore[reportAttributeAccessIssue]
                )
                self._set_loading_state(False)
                messagebox.showerror(
                    "Erro", f"Erro ao processar clientes: {exc}", parent=self
                )  # pyright: ignore[reportArgumentType]
                return

            # Atualizar filtros de status
            try:
                self._populate_status_filter_options()
            except Exception as exc:
                log.warning("Erro ao popular opções de status: %s", exc)

            # Aplicar filtros/ordenação via controller
            try:
                self._refresh_with_controller()
            except Exception:
                log.exception("Erro ao aplicar filtros/ordenação")

            render_time = time.perf_counter() - t_render
            total_time = fetch_time + render_time
            raw_count = len(clientes_raw)
            rows_count = len(
                self._current_rows
            )  # pyright: ignore[reportAttributeAccessIssue]

            log.info(
                "Clientes: carregar_async (seq=%d) perf fetch=%.3fs render=%.3fs total=%.3fs raw=%d rows=%d",
                current_seq,
                fetch_time,
                render_time,
                total_time,
                raw_count,
                rows_count,
            )

            self._load_inflight = False  # pyright: ignore[reportAttributeAccessIssue]
            self._set_loading_state(False)

        # Submeter ao executor e agendar callback no main thread
        future = MainScreenDataflowMixin._load_executor.submit(_fetch_data)

        def _on_done() -> None:
            try:
                result = future.result(timeout=0.001)  # Non-blocking check
                self.after(
                    0, lambda: _apply_loaded(result)
                )  # pyright: ignore[reportAttributeAccessIssue]
            except Exception:
                # Future ainda não completou, reagendar
                self.after(10, _on_done)  # pyright: ignore[reportAttributeAccessIssue]

        self.after(10, _on_done)  # pyright: ignore[reportAttributeAccessIssue]

    def _set_loading_state(self, loading: bool) -> None:
        """Define estado de carregamento (opcional: desabilitar botões, mostrar status)."""
        try:
            # Opcional: desabilitar botões principais durante carga
            # Por enquanto apenas log
            if loading:
                log.debug("UI em modo carregamento")
            else:
                log.debug("UI saiu do modo carregamento")
        except Exception as exc:
            log.debug("Erro ao setar loading state: %s", exc)

    def _sort_by(self, column: str) -> None:
        current = normalize_order_label(
            self.var_ordem.get()
        )  # pyright: ignore[reportAttributeAccessIssue]

        if column == "updated_at":
            new_value = (
                ORDER_LABEL_UPDATED_OLD
                if current == ORDER_LABEL_UPDATED_RECENT
                else ORDER_LABEL_UPDATED_RECENT
            )
            self.var_ordem.set(new_value)  # pyright: ignore[reportAttributeAccessIssue]
        elif column in ("razao_social", "cnpj", "nome"):
            mapping = {
                "razao_social": ORDER_LABEL_RAZAO,
                "cnpj": ORDER_LABEL_CNPJ,
                "nome": ORDER_LABEL_NOME,
            }
            self.var_ordem.set(
                mapping[column]
            )  # pyright: ignore[reportAttributeAccessIssue]
        elif column == "id":
            new_value = (
                ORDER_LABEL_ID_DESC
                if current == ORDER_LABEL_ID_ASC
                else ORDER_LABEL_ID_ASC
            )
            self.var_ordem.set(new_value)  # pyright: ignore[reportAttributeAccessIssue]
        else:
            return

        self.carregar()

    def _buscar(self, _event: Any | None = None) -> None:
        try:
            if self._buscar_after:  # pyright: ignore[reportAttributeAccessIssue]
                self.after_cancel(
                    self._buscar_after
                )  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao cancelar debounce de busca: %s", exc)

        self._buscar_after = self.after(
            200, self.carregar
        )  # pyright: ignore[reportAttributeAccessIssue]

    def _limpar_busca(self) -> None:
        self.var_busca.set("")  # pyright: ignore[reportAttributeAccessIssue]

        self.var_status.set("Todos")  # pyright: ignore[reportAttributeAccessIssue]

        self.carregar()

    def apply_filters(self, *_: Any) -> None:
        """Aplica filtros de status e texto de busca via controller headless."""
        self._refresh_with_controller()

    def _populate_status_filter_options(self) -> None:
        statuses = (
            self._vm.get_status_choices()
        )  # pyright: ignore[reportAttributeAccessIssue]

        choices = build_filter_choices_with_all_option(statuses)

        try:
            self.status_filter.configure(
                values=choices
            )  # pyright: ignore[reportAttributeAccessIssue]

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar filtro de status: %s", exc)

        current = (
            self.var_status.get() or ""
        ).strip()  # pyright: ignore[reportAttributeAccessIssue]

        resolved = resolve_filter_choice_from_options(current, choices)

        if resolved != current:
            self.var_status.set(resolved)  # pyright: ignore[reportAttributeAccessIssue]

    def _row_values_masked(self, row: ClienteRow) -> tuple[Any, ...]:
        """Converte ClienteRow para tupla de exibição com visibilidade de colunas aplicada."""
        ctx = build_rendering_context_from_ui(
            column_order=self._col_order,  # pyright: ignore[reportAttributeAccessIssue]
            visible_vars=self._col_content_visible,  # pyright: ignore[reportAttributeAccessIssue]
        )
        return build_row_values(row, ctx)

    def _refresh_rows(self) -> None:
        rows = self._current_rows  # pyright: ignore[reportAttributeAccessIssue]

        items = (
            self.client_list.get_children()
        )  # pyright: ignore[reportAttributeAccessIssue]

        if len(items) != len(rows):
            self.client_list.delete(
                *items
            )  # pyright: ignore[reportAttributeAccessIssue]

            for row in rows:
                self.client_list.insert(
                    "", "end", values=self._row_values_masked(row)
                )  # pyright: ignore[reportAttributeAccessIssue]

            return

        for item_id, row in zip(items, rows):
            self.client_list.item(
                item_id, values=self._row_values_masked(row)
            )  # pyright: ignore[reportAttributeAccessIssue]

    def _render_clientes(self, rows: Sequence[ClienteRow]) -> None:
        try:
            self.client_list.delete(
                *self.client_list.get_children()
            )  # pyright: ignore[reportAttributeAccessIssue]

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao limpar treeview de clientes: %s", exc)

        for row_index, row in enumerate(rows):
            tags = build_row_tags(row, row_index=row_index)

            self.client_list.insert(
                "", "end", values=self._row_values_masked(row), tags=tags
            )  # pyright: ignore[reportAttributeAccessIssue]

        raw_clientes = [
            row.raw.get("cliente") for row in rows if row.raw.get("cliente") is not None
        ]

        count = (
            len(rows)
            if isinstance(rows, (list, tuple))
            else len(self.client_list.get_children())
        )  # pyright: ignore[reportAttributeAccessIssue]

        self._set_count_text(count, raw_clientes)

        self._update_main_buttons_state()  # pyright: ignore[reportAttributeAccessIssue]

        try:
            self.after(50, lambda: None)  # pyright: ignore[reportAttributeAccessIssue]

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao agendar refresh assíncrono: %s", exc)

    def _get_clients_for_controller(self) -> Sequence[ClienteRow]:
        """Obtém lista completa de clientes para passar ao controller.

        Retorna a lista antes de filtros/ordenação, pois o controller
        é responsável por aplicar essas transformações.
        """
        # Reconstruir rows a partir dos dados brutos sem aplicar filtros
        raw_clientes = (
            self._vm._clientes_raw
        )  # pyright: ignore[reportPrivateUsage,reportAttributeAccessIssue]

        # Converter cada cliente raw para ClienteRow usando o método do VM
        rows: list[ClienteRow] = []
        for cliente in raw_clientes:
            row = self._vm._build_row_from_cliente(
                cliente
            )  # pyright: ignore[reportPrivateUsage,reportAttributeAccessIssue]
            rows.append(row)

        return rows

    def _update_ui_from_computed(self, computed: MainScreenComputedLike) -> None:
        """Atualiza a UI usando os dados computados pelo controller.

        Função central que aplica os resultados do controller na interface Tkinter.
        """
        # Atualizar lista visível na Treeview
        self._current_rows = list(
            computed.visible_clients
        )  # pyright: ignore[reportAttributeAccessIssue]
        self._render_clientes(
            self._current_rows
        )  # pyright: ignore[reportAttributeAccessIssue]

        # Atualizar SelectionManager com novos clientes
        self._selection_manager.update_all_clients(
            self._current_rows
        )  # pyright: ignore[reportAttributeAccessIssue]

        # Atualizar botões de batch operations e principais
        self._update_batch_buttons_from_computed(computed)
        self._update_main_buttons_state()  # pyright: ignore[reportAttributeAccessIssue]

    def _update_batch_buttons_from_computed(
        self, computed: MainScreenComputedLike
    ) -> None:
        """Atualiza botões de batch operations usando dados do controller."""
        try:
            if getattr(self, "btn_batch_delete", None) is not None:
                self.btn_batch_delete.configure(
                    state="normal" if computed.can_batch_delete else "disabled"
                )  # pyright: ignore[reportAttributeAccessIssue]

            if getattr(self, "btn_batch_restore", None) is not None:
                self.btn_batch_restore.configure(
                    state="normal" if computed.can_batch_restore else "disabled"
                )  # pyright: ignore[reportAttributeAccessIssue]

            if getattr(self, "btn_batch_export", None) is not None:
                self.btn_batch_export.configure(
                    state="normal" if computed.can_batch_export else "disabled"
                )  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as e:
            log.debug("Erro ao atualizar botões de batch: %s", e)

    def _refresh_with_controller(self) -> None:
        """Função central que usa o controller para recomputar filtro/ordem/busca (MS-34)."""
        # Obter estado de conectividade
        state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]
        online = state == "online"

        # Construir input para controller
        inp = FilterOrderInput(
            raw_clients=self._get_clients_for_controller(),
            order_label=self.var_ordem.get(),  # pyright: ignore[reportAttributeAccessIssue]
            filter_label=self.var_status.get(),  # pyright: ignore[reportAttributeAccessIssue]
            search_text=self.var_busca.get(),  # pyright: ignore[reportAttributeAccessIssue]
            selected_ids=self._get_selected_ids(),  # pyright: ignore[reportAttributeAccessIssue]
            is_trash_screen=False,
            is_online=online,
        )

        # Computar via controller headless (MS-34)
        computed = compute_filtered_and_ordered(inp)

        # Atualizar UI com resultado
        self._update_ui_from_computed(computed)

    def _update_batch_buttons_on_selection_change(self) -> None:
        """Atualiza apenas botões de batch quando seleção muda (sem recarregar lista).

        MS-34: Usa controller direto em vez de FilterSortManager.
        """
        # Obter estado de conectividade
        state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]
        online = state == "online"

        # MS-34: Usar controller direto (reutiliza lista já filtrada/ordenada)
        inp = FilterOrderInput(
            raw_clients=self._current_rows,  # pyright: ignore[reportAttributeAccessIssue]
            order_label=self.var_ordem.get(),  # pyright: ignore[reportAttributeAccessIssue]
            filter_label=self.var_status.get(),  # pyright: ignore[reportAttributeAccessIssue]
            search_text=self.var_busca.get(),  # pyright: ignore[reportAttributeAccessIssue]
            selected_ids=self._get_selected_ids(),  # pyright: ignore[reportAttributeAccessIssue]
            is_trash_screen=False,
            is_online=online,
        )

        # Computar apenas para obter flags de batch
        computed = compute_filtered_and_ordered(inp)

        # Atualizar apenas botões de batch
        self._update_batch_buttons_from_computed(computed)

    def _apply_status_for(self, cliente_id: int, chosen: str) -> None:
        """Atualiza o [STATUS] no campo Observações e recarrega a grade (MS-35: via controller)."""
        # MS-35: Delegar decisão ao controller headless
        decision = decide_status_change(
            cliente_id=cliente_id if cliente_id else None,
            chosen_status=chosen,
        )

        # Interpretar decisão
        if decision.kind == "noop":
            return

        if decision.kind == "error":
            if decision.message:
                messagebox.showerror(
                    "Erro", decision.message, parent=self
                )  # pyright: ignore[reportArgumentType]
            return

        if decision.kind == "execute":
            # Executar mudança de status via serviço
            try:
                cli = fetch_cliente_by_id(decision.target_id or cliente_id)

                if not cli:
                    return

                old_obs = (
                    getattr(cli, "obs", None) or getattr(cli, "observacoes", None) or ""
                ).strip()

                _ = self._vm.extract_status_and_observacoes(
                    old_obs
                )  # pyright: ignore[reportAttributeAccessIssue]

                update_cliente_status_and_observacoes(
                    cliente=decision.target_id or cliente_id,
                    novo_status=decision.new_status or chosen,
                )

                self.carregar()

            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Falha ao atualizar status: {e}", parent=self
                )  # pyright: ignore[reportArgumentType]

    def _apply_connectivity_state(
        self, state: str, description: str, text: str, _style: str, _tooltip: str
    ) -> None:
        """Aplica efeitos de conectividade (enable/disable, textos, status bar)."""
        # Construir input bruto para o ConnectivityStateManager
        raw = ConnectivityRawInput(
            state=state,  # pyright: ignore[reportArgumentType]
            description=description,
            text=text,
            last_known_state=(
                self._last_cloud_state
                if hasattr(self, "_last_cloud_state")
                else "unknown"
            ),  # pyright: ignore[reportArgumentType,reportAttributeAccessIssue]
        )

        # Computar snapshot de conectividade
        snapshot = self._connectivity_state_manager.compute_snapshot(
            raw
        )  # pyright: ignore[reportAttributeAccessIssue]

        # Aplicar atributos globais da app
        try:
            if self.app is not None:  # pyright: ignore[reportAttributeAccessIssue]
                setattr(
                    self.app, "_net_is_online", snapshot.is_online
                )  # pyright: ignore[reportAttributeAccessIssue]
                setattr(
                    self.app, "_net_state", snapshot.state
                )  # pyright: ignore[reportAttributeAccessIssue]
                setattr(
                    self.app, "_net_description", snapshot.description
                )  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar atributos globais de conectividade: %s", exc)

        # Atualiza estado dos botões e textos
        try:
            self._update_main_buttons_state()  # pyright: ignore[reportAttributeAccessIssue]

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar UI de conectividade: %s", exc)

        # Atualiza indicador visual na UI (status bar global)
        status_var = (
            getattr(self.app, "status_var_text", None) if self.app is not None else None
        )  # pyright: ignore[reportAttributeAccessIssue]
        if status_var is not None:
            try:
                current_text = status_var.get()
                updated_text = self._connectivity_state_manager.update_status_bar_text(  # pyright: ignore[reportAttributeAccessIssue]
                    current_text=current_text,
                    new_cloud_text=snapshot.text_for_status_bar,
                )
                status_var.set(updated_text)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao atualizar texto de status global: %s", exc)

        # Log de transição de estado
        if snapshot.should_log_transition:
            log.info(
                "Status da nuvem mudou: %s – %s (%s)",
                (snapshot.old_state or "unknown").upper(),
                (snapshot.state or "unknown").upper(),
                snapshot.description,
            )
            self._last_cloud_state = (
                snapshot.state
            )  # pyright: ignore[reportAttributeAccessIssue]

    def _update_main_buttons_state(self, *_: Any) -> None:
        """Atualiza o estado dos botões principais (MS-32: via controller headless).

        Baseado em: seleção de cliente e status de conectividade.
        Comportamento: ONLINE → todos funcionam; INSTÁVEL/OFFLINE → botões de envio desabilitados.
        """
        # Obter snapshot de seleção via SelectionManager
        selection_snapshot = (
            self._build_selection_snapshot()
        )  # pyright: ignore[reportAttributeAccessIssue]

        # Obtém estado detalhado da nuvem
        state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]
        online = state == "online"

        # MS-32: Computar estados via controller headless
        button_states = compute_button_states(
            has_selection=selection_snapshot.has_selection,
            is_online=online,
            is_uploading=self._uploading_busy,  # pyright: ignore[reportAttributeAccessIssue]
            is_pick_mode=self._pick_mode,  # pyright: ignore[reportAttributeAccessIssue]
            connectivity_state=state,  # pyright: ignore[reportArgumentType]
        )

        try:
            # Botões que dependem de conexão E seleção
            self.btn_editar.configure(
                state=("normal" if button_states.editar else "disabled")
            )  # pyright: ignore[reportAttributeAccessIssue]
            self.btn_subpastas.configure(
                state=("normal" if button_states.subpastas else "disabled")
            )  # pyright: ignore[reportAttributeAccessIssue]

            # Botões que dependem apenas de conexão
            self.btn_novo.configure(
                state=("normal" if button_states.novo else "disabled")
            )  # pyright: ignore[reportAttributeAccessIssue]

            # FIX-CLIENTES-007: Não mexer no estado da Lixeira quando saindo do pick mode
            pick_snapshot = (
                self._pick_mode_manager.get_snapshot()
            )  # pyright: ignore[reportAttributeAccessIssue]
            if not pick_snapshot.is_pick_mode_active:
                self.btn_lixeira.configure(
                    state=("normal" if button_states.lixeira else "disabled")
                )  # pyright: ignore[reportAttributeAccessIssue]

            # Botão de seleção (modo pick) - não depende de conexão
            if pick_snapshot.is_pick_mode_active and hasattr(self, "btn_select"):
                self.btn_select.configure(
                    state=("normal" if button_states.select else "disabled")
                )  # pyright: ignore[reportAttributeAccessIssue]

            btn_excluir = getattr(self, "btn_excluir", None)
            if btn_excluir is not None:
                btn_excluir.configure(
                    state=("normal" if button_states.editar else "disabled")
                )

        except Exception as e:
            log.debug("Erro ao atualizar estado dos botões: %s", e)

        # Atualizar botões de batch via controller
        self._update_batch_buttons_on_selection_change()

    def _set_count_text(
        self, count: int, clientes: Sequence[Any] | None = None
    ) -> None:
        """Atualiza o StatusFooter global com estatísticas de clientes (MS-35: via controller)."""
        try:
            # MS-35: Delegar cálculo ao controller headless
            summary = compute_count_summary(
                visible_clients=(
                    self._current_rows if hasattr(self, "_current_rows") else []
                ),  # pyright: ignore[reportAttributeAccessIssue]
                raw_clients_for_stats=clientes,
            )

            # Atualizar o StatusFooter global
            if (
                self.app and self.app.status_footer
            ):  # pyright: ignore[reportAttributeAccessIssue]
                self.app.status_footer.set_clients_summary(  # pyright: ignore[reportAttributeAccessIssue]
                    summary.total,
                    summary.new_today,
                    summary.new_this_month,
                )

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar resumo de clientes: %s", exc)
